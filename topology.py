#!/usr/bin/env python3
"""
Multi-Switch Flow Table Analyzer - Mininet Topology
3 switches in a chain, 2 hosts each, POX controller
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

def create_topology():
    setLogLevel('info')

    net = Mininet(controller=RemoteController,
                  switch=OVSSwitch,
                  link=TCLink,
                  autoSetMacs=True)

    info("*** Adding POX controller\n")
    c0 = net.addController('c0',
                            controller=RemoteController,
                            ip='127.0.0.1',
                            port=6633)   # POX uses 6633

    info("*** Adding 3 switches\n")
    s1 = net.addSwitch('s1', dpid='0000000000000001')
    s2 = net.addSwitch('s2', dpid='0000000000000002')
    s3 = net.addSwitch('s3', dpid='0000000000000003')

    info("*** Adding 6 hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:01:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:01:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:02:01')
    h4 = net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:02:02')
    h5 = net.addHost('h5', ip='10.0.0.5/24', mac='00:00:00:00:03:01')
    h6 = net.addHost('h6', ip='10.0.0.6/24', mac='00:00:00:00:03:02')

    info("*** Creating links\n")
    # Hosts to switches
    net.addLink(h1, s1, bw=10)
    net.addLink(h2, s1, bw=10)
    net.addLink(h3, s2, bw=10)
    net.addLink(h4, s2, bw=10)
    net.addLink(h5, s3, bw=10)
    net.addLink(h6, s3, bw=10)

    # Switch chain: s1 -- s2 -- s3
    net.addLink(s1, s2, bw=100)
    net.addLink(s2, s3, bw=100)

    info("*** Starting network\n")
    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])

    info("\n*** Network ready!\n")
    info("*** Test commands:\n")
    info("    pingall                          - test all hosts\n")
    info("    h2 ping -c 4 h5                  - should be BLOCKED\n")
    info("    h1 ping -c 4 h6                  - should work\n")
    info("    h1 iperf -s & h6 iperf -c 10.0.1.1 -t 5  - throughput\n")
    info("    sh ovs-ofctl dump-flows s1       - flow table\n\n")

    CLI(net)
    net.stop()

if __name__ == '__main__':
    create_topology()
