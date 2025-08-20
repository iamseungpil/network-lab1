#!/bin/bash
# Final working demo runner

set -e

# Colors
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BLUE='\033[94m'
CYAN='\033[96m'
NC='\033[0m'

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}   FINAL 10-SWITCH DIJKSTRA SDN DEMO${NC}"
echo -e "${CYAN}============================================================${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${BLUE}[CLEANUP]${NC} Cleaning up..."
    sudo mn -c 2>/dev/null || true
    pkill -9 ryu-manager 2>/dev/null || true
}

# Trap to cleanup on exit
trap cleanup EXIT

# Initial cleanup
cleanup

# Start controller in background
echo -e "${BLUE}[CONTROLLER]${NC} Starting Dijkstra controller..."
source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-lab
ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/final_controller.py &
CONTROLLER_PID=$!

# Wait for controller
echo -e "${YELLOW}[WAIT]${NC} Waiting for controller to start..."
sleep 5

# Check if controller is running
if ! kill -0 $CONTROLLER_PID 2>/dev/null; then
    echo -e "${RED}[ERROR]${NC} Controller failed to start!"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Controller running (PID: $CONTROLLER_PID)"

# Run the demo
echo -e "${BLUE}[NETWORK]${NC} Starting network demo..."
echo ""
sudo python3 final_demo.py

# Controller will be killed by trap on exit
echo -e "\n${GREEN}✅ Demo completed!${NC}"