#!/bin/bash

# Complete Network Cleanup Script
echo "Performing complete network cleanup..."

# Kill all Mininet-related processes
sudo pkill -9 -f "ryu-manager" 2>/dev/null
sudo pkill -9 -f "mn" 2>/dev/null
sudo pkill -9 -f "mininet" 2>/dev/null
sudo pkill -9 -f "python.*topo" 2>/dev/null
sudo pkill -9 -f "python.*link_failure" 2>/dev/null
sudo killall -9 ovs-vswitchd 2>/dev/null
sudo killall -9 ovsdb-server 2>/dev/null

# Kill tmux sessions first
tmux kill-session -t dual_controllers 2>/dev/null

# Clean Mininet multiple times
sudo mn -c 2>/dev/null
sleep 1
sudo mn -c 2>/dev/null

# Remove all mininet interfaces aggressively
sudo ip link show | grep -E "(h[0-9]+|s[0-9]+)" | cut -d: -f2 | cut -d@ -f1 | while read intf; do
    sudo ip link del $intf 2>/dev/null
done

# Clean up OVS bridges completely
sudo ovs-vsctl --if-exists del-br s1 2>/dev/null
sudo ovs-vsctl --if-exists del-br s2 2>/dev/null
sudo ovs-vsctl --if-exists del-br s3 2>/dev/null
sudo ovs-vsctl --if-exists del-br s4 2>/dev/null
sudo ovs-vsctl --if-exists del-br s5 2>/dev/null
sudo ovs-vsctl --if-exists del-br s6 2>/dev/null
sudo ovs-vsctl --if-exists del-br s7 2>/dev/null
sudo ovs-vsctl --if-exists del-br s8 2>/dev/null
sudo ovs-vsctl --if-exists del-br s9 2>/dev/null
sudo ovs-vsctl --if-exists del-br s10 2>/dev/null

# Restart OVS completely
sudo systemctl stop openvswitch-switch 2>/dev/null
sleep 2
sudo systemctl start openvswitch-switch 2>/dev/null
sleep 2

# Final interface cleanup
sudo ip link show | grep -E "(h[0-9]+|s[0-9]+)" | cut -d: -f2 | cut -d@ -f1 | while read intf; do
    sudo ip link del $intf 2>/dev/null
done

echo "Network cleanup complete!"
sleep 3