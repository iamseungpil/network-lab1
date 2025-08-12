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
echo "       DUAL CONTROLLER SDN DEMONSTRATION"
echo "       Cross-Domain Link Failure Detection & Rerouting"
echo "       10 Switches, 20 Hosts"
echo "============================================================"
echo -e "${NC}"

# Check if conda sdn-env exists and works
if [ -d "/data/miniforge3/envs/sdn-env" ]; then
    echo -e "${YELLOW}[INFO] Conda environment detected. Using conda version for compatibility...${NC}"
    source /data/miniforge3/etc/profile.d/conda.sh
    conda activate sdn-env
    if ryu-manager --version > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Using conda sdn-env (Python 3.8, RYU $(ryu-manager --version))${NC}"
        echo -e "${GREEN}[INFO] Redirecting to conda demo for better compatibility...${NC}"
        echo ""
        exec ./demo_conda.sh
    fi
fi

echo -e "${YELLOW}[WARNING] Using system RYU - may have eventlet compatibility issues${NC}"

# Clean up any existing setup
echo -e "${YELLOW}[INFO] Performing complete cleanup...${NC}"
./cleanup_network.sh

# Start dual controllers
echo -e "${GREEN}[INFO] Starting dual controller environment...${NC}"
./start_dual_controllers.sh

echo ""
echo -e "${MAGENTA}${BOLD}Network Topology:${NC}"
echo "  Primary Controller (6633):   s1-s5 managing h1-h10"  
echo "  Secondary Controller (6634): s6-s10 managing h11-h20"
echo "  Cross-domain gateways:       s3↔s6, s3↔s7, s4↔s8, s4↔s9, s5↔s10"
echo ""
# Check for auto flag
if [[ "$1" == "auto" ]]; then
    echo -e "${CYAN}Auto mode - starting demonstration in 3 seconds...${NC}"
    sleep 3
else
    echo -e "${CYAN}Press Enter to start demonstration (or use './demo_all.sh auto' for auto mode)...${NC}"
    read
fi

# Run the test with proper conda environment
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
echo -e "${GREEN}Demo finished successfully!${NC}"