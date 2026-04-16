#!/bin/bash
echo "============================================"
echo "  Multi-Switch Flow Table Analyzer - Tests"
echo "============================================"

echo ""
echo "--- Flow Tables ---"
for sw in s1 s2 s3; do
    echo ""
    echo ">>> Switch $sw:"
    sudo ovs-ofctl dump-flows $sw
done

echo ""
echo "--- Port Statistics ---"
for sw in s1 s2 s3; do
    echo ""
    echo ">>> $sw port stats:"
    sudo ovs-ofctl dump-ports $sw
done

echo ""
echo "--- Switch Info ---"
for sw in s1 s2 s3; do
    echo ""
    echo ">>> $sw:"
    sudo ovs-ofctl show $sw
done
