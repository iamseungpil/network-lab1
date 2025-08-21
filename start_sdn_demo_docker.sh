#!/bin/bash

# SDN Dijkstra Demo Script for Docker Container
# Simplified version without conda for Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 SDN DIJKSTRA ROUTING DEMO (Docker Version)${NC}"
echo -e "${BLUE}================================================${NC}"

# Get topology argument
TOPOLOGY=${1:-ring}

# Verify Python packages
echo -e "${YELLOW}🔍 Verifying Python packages...${NC}"
if python3 -c "import ryu, networkx" 2>/dev/null; then
    echo -e "${GREEN}✅ All packages ready${NC}"
else
    echo -e "${YELLOW}📦 Installing packages...${NC}"
    pip3 install ryu networkx
fi

# Kill existing processes
echo -e "${YELLOW}🧹 Cleaning up...${NC}"
tmux kill-session -t sdn_demo 2>/dev/null || true
pkill -f ryu-manager 2>/dev/null || true
mn -c 2>/dev/null || true

# Ensure OVS is running
if ! pgrep ovsdb-server > /dev/null || ! pgrep ovs-vswitchd > /dev/null; then
    echo -e "${YELLOW}Starting OVS...${NC}"
    /usr/local/bin/start-ovs.sh
    sleep 2
fi

# Check port
CONTROLLER_PORT="6653"
if ss -tulpn 2>/dev/null | grep -q :6653; then
    echo -e "${YELLOW}Port 6653 in use, using 6633${NC}"
    CONTROLLER_PORT="6633"
fi

# Choose topology
case "$TOPOLOGY" in
    ring)
        TOPOLOGY_FILE="mininet/ring_topology.py"
        TOPO_NAME="10-Switch Ring"
        ;;
    graph)
        TOPOLOGY_FILE="mininet/graph_topology.py"
        TOPO_NAME="Graph"
        ;;
    *)
        TOPOLOGY_FILE="mininet/diamond_topology.py"
        TOPO_NAME="Diamond"
        ;;
esac

echo -e "${GREEN}🌐 Using $TOPO_NAME topology${NC}"

# Create tmux session
echo -e "${YELLOW}📺 Creating tmux session...${NC}"
tmux new-session -d -s sdn_demo
tmux split-window -v -t sdn_demo

# Start controller
tmux select-pane -t sdn_demo:0.0
tmux send-keys -t sdn_demo:0.0 "echo '=== CONTROLLER (상단) ==='" Enter
tmux send-keys -t sdn_demo:0.0 "cd /opt/sdn-lab" Enter
tmux send-keys -t sdn_demo:0.0 "python3 ryu-controller/main_controller_stp.py" Enter

# Start topology
tmux select-pane -t sdn_demo:0.1
tmux send-keys -t sdn_demo:0.1 "echo '=== MININET (하단) ==='" Enter
tmux send-keys -t sdn_demo:0.1 "echo 'Waiting for controller...'" Enter
tmux send-keys -t sdn_demo:0.1 "sleep 5" Enter
tmux send-keys -t sdn_demo:0.1 "cd /opt/sdn-lab" Enter
tmux send-keys -t sdn_demo:0.1 "python3 $TOPOLOGY_FILE" Enter

# Attach to session
echo -e "${GREEN}✅ Ready! Attaching to tmux...${NC}"
sleep 1
tmux attach-session -t sdn_demo
