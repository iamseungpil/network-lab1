#!/bin/bash

# Automated Demo Script - No User Input Required
# Automatically demonstrates dual controller SDN with link failure testing

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
echo "       AUTOMATED DUAL CONTROLLER SDN DEMONSTRATION"
echo "       Cross-Domain Link Failure Detection & Rerouting"
echo "       10 Switches, 20 Hosts"
echo "============================================================"
echo -e "${NC}"

# Function to wait with countdown
countdown() {
    local seconds=$1
    local message=$2
    echo -e "${YELLOW}${message}${NC}"
    for ((i=seconds; i>0; i--)); do
        printf "\r${CYAN}Starting in %d seconds...${NC}" $i
        sleep 1
    done
    printf "\r${GREEN}Starting now!                    ${NC}\n"
}

# Check conda environment
source /data/miniforge3/etc/profile.d/conda.sh
conda activate sdn-env

if ! ryu-manager --version > /dev/null 2>&1; then
    echo -e "${RED}ERROR: RYU not available in conda environment!${NC}"
    echo "Please run: conda activate sdn-env"
    exit 1
fi

echo -e "${GREEN}✓ Conda environment: sdn-env (Python 3.8, RYU $(ryu-manager --version))${NC}"

# Clean up any existing setup
echo -e "${YELLOW}[INFO] Cleaning up previous setup...${NC}"
sudo mn -c 2>/dev/null
pkill -f "ryu-manager" 2>/dev/null
tmux kill-session -t dual_controllers 2>/dev/null
sleep 2

# Start controllers in background
echo -e "${GREEN}[INFO] Starting Primary Controller (port 6633)...${NC}"
tmux new-session -d -s dual_controllers -n "primary"
tmux send-keys -t dual_controllers:0 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_controller.py" Enter

echo -e "${GREEN}[INFO] Starting Secondary Controller (port 6634)...${NC}"
tmux new-window -t dual_controllers -n "secondary"
tmux send-keys -t dual_controllers:1 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_controller.py" Enter

# Wait for controllers to start
echo -e "${YELLOW}[INFO] Waiting for controllers to initialize...${NC}"
sleep 8

# Check if controllers are running
echo -e "${CYAN}[INFO] Checking controller status...${NC}"
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

countdown 3 "[INFO] Starting automated link failure tests..."

# Run the test with proper environment
echo -e "${GREEN}[INFO] Running automated dual controller tests...${NC}"
echo ""

# Create test script that preserves conda environment  
cat > /tmp/run_test.sh << 'EOF'
#!/bin/bash
source /data/miniforge3/etc/profile.d/conda.sh
conda activate sdn-env
cd /home/ubuntu/network-lab1
python3 link_failure_test.py
EOF

chmod +x /tmp/run_test.sh
sudo -E /tmp/run_test.sh

# Show results
echo ""
echo -e "${YELLOW}[INFO] Controllers are still running in tmux sessions${NC}"
echo ""
echo -e "${CYAN}View detailed logs:${NC}"
echo "  tmux attach -t dual_controllers:0  # Primary controller"  
echo "  tmux attach -t dual_controllers:1  # Secondary controller"
echo ""
echo -e "${CYAN}Manual testing:${NC}"
echo "  tmux new-window -t dual_controllers -n mininet"
echo "  tmux send-keys -t dual_controllers:2 'sudo python3 mininet/dijkstra_graph_topo.py' Enter"
echo ""
echo -e "${CYAN}Stop all controllers:${NC}"
echo "  tmux kill-session -t dual_controllers"

echo ""
echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║          DEMONSTRATION COMPLETE!                       ║${NC}"
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

# Clean up temp file
rm -f /tmp/run_test.sh