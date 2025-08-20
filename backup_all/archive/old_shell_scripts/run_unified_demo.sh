#!/bin/bash
# Unified demo runner with perfect topology matching

set -e

# Colors
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BLUE='\033[94m'
CYAN='\033[96m'
NC='\033[0m'

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}   UNIFIED 10-SWITCH DIJKSTRA SDN DEMO${NC}"
echo -e "${CYAN}============================================================${NC}"

# Function to cleanup
cleanup() {
    echo -e "\n${BLUE}[CLEANUP]${NC} Cleaning up..."
    sudo mn -c 2>/dev/null || true
    pkill -9 ryu-manager 2>/dev/null || true
    tmux kill-session -t unified_demo 2>/dev/null || true
}

# Clean first
cleanup

# Check for tmux
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} tmux is required. Install with: sudo apt install tmux"
    exit 1
fi

# Create tmux session with split panes
echo -e "${BLUE}[SETUP]${NC} Creating tmux session with split view..."
tmux new-session -d -s unified_demo -n "SDN-Demo"
tmux split-window -t unified_demo -h -p 50

# Start controller in left pane
echo -e "${BLUE}[CONTROLLER]${NC} Starting final controller (left pane)..."
tmux send-keys -t unified_demo:0.0 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-lab" Enter
tmux send-keys -t unified_demo:0.0 "echo -e '${GREEN}===== FINAL DIJKSTRA CONTROLLER =====${NC}'" Enter
tmux send-keys -t unified_demo:0.0 "echo ''" Enter
tmux send-keys -t unified_demo:0.0 "ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/final_controller.py" Enter

# Wait for controller to start
echo -e "${YELLOW}[WAIT]${NC} Waiting for controller to initialize..."
sleep 5

# Run test in right pane
echo -e "${BLUE}[TEST]${NC} Starting network test (right pane)..."
tmux send-keys -t unified_demo:0.1 "echo -e '${YELLOW}===== NETWORK TEST =====${NC}'" Enter
tmux send-keys -t unified_demo:0.1 "echo ''" Enter
tmux send-keys -t unified_demo:0.1 "sudo python3 final_demo.py" Enter

# Instructions
echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}   DEMO READY!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "\n${YELLOW}The demo is running in tmux with split view:${NC}"
echo -e "  • Left pane:  Controller logs (watch for events)"
echo -e "  • Right pane: Network tests and Mininet CLI"
echo -e ""
echo -e "${YELLOW}Tmux commands:${NC}"
echo -e "  • Ctrl+B, ←/→  : Switch between panes"
echo -e "  • Ctrl+B, D    : Detach from session"
echo -e "  • tmux attach  : Reattach to session"
echo -e ""
echo -e "${CYAN}Attaching to tmux session now...${NC}"
echo -e ""

# Attach to session
tmux attach -t unified_demo