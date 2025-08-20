#!/bin/bash

# Clear Dijkstra routing test

# Cleanup
tmux kill-session -t test_dijkstra 2>/dev/null
sudo mn -c 2>/dev/null
pkill -f ryu-manager 2>/dev/null
sleep 2

# Start controller with grep filter for Dijkstra
echo "Starting controller with Dijkstra filter..."
tmux new-session -d -s test_dijkstra
tmux send-keys -t test_dijkstra:0 "ryu-manager --observe-links ryu-controller/main_controller.py 2>&1 | tee /tmp/controller.log | grep --line-buffered -E '(DIJKSTRA|PATH|Computing|shortest|Next hop|Path length|HOST.*Learned)'" Enter

sleep 5

# Start topology
echo "Starting ring topology..."
sudo python3 mininet/ring_topology.py &
TOPO_PID=$!

sleep 8

# Test h1 to h6 (opposite sides of ring)
echo -e "\n=== Testing h1 -> h6 (opposite sides) ==="
echo "Expected: 5 hops shortest path"
sudo ip netns exec h1 ping -c 1 10.0.0.6

sleep 2

# Check controller output
echo -e "\n=== Dijkstra Routing Logs ==="
tmux capture-pane -t test_dijkstra:0 -p | tail -20

# Show full log
echo -e "\n=== Full Controller Log (filtered) ==="
cat /tmp/controller.log | grep -E "(DIJKSTRA|PATH|shortest|Next hop)"

# Cleanup
kill $TOPO_PID 2>/dev/null
tmux kill-session -t test_dijkstra 2>/dev/null