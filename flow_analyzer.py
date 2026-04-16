# Multi-Switch Flow Table Analyzer - POX Controller
# Handles: MAC learning, flow rule installation, firewall (h2->h5 blocked)

from pox.core import core
from pox.lib.util import dpid_to_str
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ipv4 import ipv4
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr

log = core.getLogger()

# Firewall: block these (src_ip, dst_ip) pairs
BLOCKED_PAIRS = [
    (IPAddr('10.0.0.2'), IPAddr('10.0.0.5')),  # Block h2 -> h5
]

class FlowTableAnalyzer(object):

    def __init__(self, connection, dpid):
        self.connection = connection
        self.dpid = dpid
        self.mac_to_port = {}
        self.packet_in_count = 0
        connection.addListeners(self)
        log.info("Switch %s connected", dpid_to_str(dpid))

    def install_flow(self, match, port=None, priority=10, idle=30):
        """Install a flow rule. If port is None, it's a DROP rule."""
        msg = of.ofp_flow_mod()
        msg.match = match
        msg.priority = priority
        msg.idle_timeout = idle
        msg.hard_timeout = 0
        if port is not None:
            msg.actions.append(of.ofp_action_output(port=port))
        # empty actions = DROP
        self.connection.send(msg)

    def send_packet(self, buffer_id, raw_data, out_port, in_port):
        """Send a packet out a specific port."""
        msg = of.ofp_packet_out()
        msg.in_port = in_port
        msg.buffer_id = buffer_id
        if raw_data is not None:
            msg.data = raw_data
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)

    def _handle_PacketIn(self, event):
        self.packet_in_count += 1
        packet_data = event.parsed
        in_port = event.port

        if not packet_data.parsed:
            log.warning("Ignoring incomplete packet")
            return

        # --- MAC Learning ---
        src_mac = packet_data.src
        dst_mac = packet_data.dst
        self.mac_to_port[src_mac] = in_port

        log.debug("Switch %s: %s -> %s on port %s",
                  dpid_to_str(self.dpid), src_mac, dst_mac, in_port)

        # --- IP Firewall Check ---
        ip_packet = packet_data.find('ipv4')
        if ip_packet:
            src_ip = ip_packet.srcip
            dst_ip = ip_packet.dstip
            if (src_ip, dst_ip) in BLOCKED_PAIRS:
                log.warning("BLOCKED %s -> %s on switch %s",
                            src_ip, dst_ip, dpid_to_str(self.dpid))
                # Install DROP rule
                match = of.ofp_match()
                match.dl_type = ethernet.IP_TYPE
                match.nw_src = src_ip
                match.nw_dst = dst_ip
                self.install_flow(match, port=None, priority=100, idle=30)
                return  # drop this packet, don't forward

        # --- Forwarding ---
        if dst_mac in self.mac_to_port:
            out_port = self.mac_to_port[dst_mac]
            log.info("Switch %s: installing flow %s -> %s out port %s",
                     dpid_to_str(self.dpid), src_mac, dst_mac, out_port)
            # Install flow rule
            match = of.ofp_match.from_packet(packet_data, in_port)
            self.install_flow(match, port=out_port, priority=10, idle=30)
            # Forward this packet
            self.send_packet(event.ofp.buffer_id, event.data, out_port, in_port)
        else:
            # Flood - destination unknown
            log.debug("Switch %s: flooding for %s", dpid_to_str(self.dpid), dst_mac)
            self.send_packet(event.ofp.buffer_id, event.data,
                             of.OFPP_FLOOD, in_port)


class FlowAnalyzerLauncher(object):
    """Launches one FlowTableAnalyzer per switch."""

    def __init__(self):
        self.switches = {}
        core.openflow.addListeners(self)
        log.info("=== Multi-Switch Flow Table Analyzer started ===")
        log.info("Firewall rule: 10.0.1.2 -> 10.0.3.1 is BLOCKED")

    def _handle_ConnectionUp(self, event):
        dpid = event.dpid
        log.info("New switch connected: %s", dpid_to_str(dpid))
        self.switches[dpid] = FlowTableAnalyzer(event.connection, dpid)

    def _handle_ConnectionDown(self, event):
        dpid = event.dpid
        log.info("Switch disconnected: %s", dpid_to_str(dpid))
        if dpid in self.switches:
            sw = self.switches[dpid]
            log.info("Switch %s had %d packet_in events",
                     dpid_to_str(dpid), sw.packet_in_count)
            del self.switches[dpid]


def launch():
    core.registerNew(FlowAnalyzerLauncher)
