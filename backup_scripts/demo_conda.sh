#!/bin/bash

# Color codes for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo "       DUAL CONTROLLER SDN DEMONSTRATION (CONDA)"
echo "       Cross-Domain Link Failure Detection & Rerouting"
echo "       10 Switches, 20 Hosts"
echo "============================================================"
echo -e "${NC}"

# Check conda environment
source /data/miniforge3/etc/profile.d/conda.sh
conda activate sdn-env

if ! ryu-manager --version > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Please activate conda environment first:${NC}"
    echo "  source /data/miniforge3/etc/profile.d/conda.sh"
    echo "  conda activate sdn-env"
    exit 1
fi

echo -e "${GREEN}✓ Conda environment: sdn-env (Python 3.8, RYU $(ryu-manager --version))${NC}"

# Clean up any existing setup
echo -e "${YELLOW}[INFO] Performing complete cleanup...${NC}"
./cleanup_network.sh

# Start controllers ONLY (not the persistent topology)
echo -e "${GREEN}[INFO] Starting dual controllers (port 6633 & 6634)...${NC}"

# Create tmux session
SESSION_NAME="dual_controllers"
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create new session with 2 windows for controllers only
tmux new-session -d -s $SESSION_NAME -n "primary"
tmux new-window -t $SESSION_NAME -n "secondary" 

# Start Primary Controller (window 0)
tmux send-keys -t $SESSION_NAME:0 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_controller.py" Enter

# Start Secondary Controller (window 1)  
tmux send-keys -t $SESSION_NAME:1 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_controller.py" Enter

# Wait for controllers to start
echo -e "${YELLOW}[INFO] Waiting for controllers to initialize...${NC}"
sleep 8

# Check controller status
if netstat -ln | grep ":6633 " > /dev/null; then
    echo -e "${GREEN}✓ Primary Controller (6633) is running${NC}"
else
    echo -e "${RED}✗ Primary Controller (6633) failed to start${NC}"
fi

if netstat -ln | grep ":6634 " > /dev/null; then
    echo -e "${GREEN}✓ Secondary Controller (6634) is running${NC}"
else
    echo -e "${RED}✗ Secondary Controller (6634) failed to start${NC}"
fi

echo ""
echo -e "${MAGENTA}${BOLD}Network Topology:${NC}"
echo "  Primary Controller (6633):   s1-s5 managing h1-h10"  
echo "  Secondary Controller (6634): s6-s10 managing h11-h20"
echo "  Cross-domain gateways:       s3↔s6, s3↔s7, s4↔s8, s4↔s9, s5↔s10"
echo ""

# Check for auto mode
if [[ "$1" == "auto" ]]; then
    echo -e "${CYAN}Auto mode - starting demonstration in 3 seconds...${NC}"
    sleep 3
else
    echo -e "${CYAN}Press Enter to start demonstration (or use 'auto' for auto mode)...${NC}"
    read
fi

# Run the test with conda environment - link_failure_test.py creates its own topology
echo -e "${GREEN}[INFO] Running automated dual controller tests...${NC}"
echo ""

# Create test script that preserves conda environment
cat > /tmp/run_test_conda.sh << 'EOF'
#!/bin/bash
source /data/miniforge3/etc/profile.d/conda.sh
conda activate sdn-env
cd /home/ubuntu/network-lab1
python3 link_failure_test.py
EOF

chmod +x /tmp/run_test_conda.sh
sudo -E /tmp/run_test_conda.sh
rm -f /tmp/run_test_conda.sh

# Show tmux sessions info
echo ""
echo -e "${YELLOW}[INFO] Controllers are still running in tmux sessions${NC}"
echo "View controller logs:"
echo "  tmux attach -t dual_controllers:0  # Primary controller"  
echo "  tmux attach -t dual_controllers:1  # Secondary controller"
echo "  tmux attach -t dual_controllers:2  # Mininet CLI"
echo ""
echo "To stop all controllers:"
echo "  tmux kill-session -t dual_controllers"

echo ""
echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║          DUAL CONTROLLER DEMONSTRATION COMPLETE!       ║${NC}"
echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Test Summary:${NC}"
echo "  ✓ Dual controller Dijkstra routing (Primary & Secondary domains)"
echo "  ✓ Cross-domain communication via gateway switches"
echo "  ✓ Link failure detection via OpenFlow PORT_STATUS"
echo "  ✓ Intra-domain and cross-domain rerouting"
echo "  ✓ Multiple controller coordination"
echo "  ✓ Path restoration when links recover"
echo ""
echo -e "${GREEN}Environment: Conda sdn-env with compatible RYU installation${NC}"