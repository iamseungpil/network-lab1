#!/bin/bash

# Dual Controller Startup Script

echo "Starting Dual Controller SDN Environment..."

# Clean up any existing setup
echo "Cleaning up previous setup..."
sudo mn -c 2>/dev/null
pkill -f "ryu-manager" 2>/dev/null
sleep 2

# Create tmux session
SESSION_NAME="dual_controllers"

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create new session with 3 windows
echo "Creating tmux session: $SESSION_NAME"
tmux new-session -d -s $SESSION_NAME -n "primary"
tmux new-window -t $SESSION_NAME -n "secondary" 
tmux new-window -t $SESSION_NAME -n "mininet"

# Start Primary Controller (window 0)
echo "Starting Primary Controller on port 6633..."
tmux send-keys -t $SESSION_NAME:0 "ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_controller.py" Enter

# Start Secondary Controller (window 1)  
echo "Starting Secondary Controller on port 6634..."
tmux send-keys -t $SESSION_NAME:1 "ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_controller.py" Enter

# Wait for controllers to start
echo "Waiting for controllers to start..."
sleep 5

# Start Mininet with dual controller topology (window 2)
echo "Starting Mininet with dual controller topology..."
tmux send-keys -t $SESSION_NAME:2 "sudo python3 mininet/dijkstra_graph_topo.py" Enter

echo ""
echo "======================================================================"
echo "  Dual Controller SDN Environment Started Successfully!"
echo "======================================================================"
echo ""
echo "Controllers:"
echo "  Primary Controller:   Port 6633 (s1-s5, h1-h10)"
echo "  Secondary Controller: Port 6634 (s6-s10, h11-h20)"
echo ""
echo "View logs:"
echo "  tmux attach -t dual_controllers:0  # Primary controller"
echo "  tmux attach -t dual_controllers:1  # Secondary controller"  
echo "  tmux attach -t dual_controllers:2  # Mininet CLI"
echo ""
echo "Topology:"
echo "  10 switches (s1-s10), 20 hosts (h1-h20)"
echo "  Cross-domain links: s3↔s6, s3↔s7, s4↔s8, s4↔s9, s5↔s10"
echo ""
echo "Test cross-domain communication:"
echo "  h1 arp -s 10.0.0.11 00:00:00:00:00:0b"
echo "  h11 arp -s 10.0.0.1 00:00:00:00:00:01"
echo "  h1 ping h11"
echo ""