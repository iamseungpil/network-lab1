#!/bin/bash

# Visual Demo with Split Panes - See everything at once!
# Shows Primary Controller, Secondary Controller, and Test Output in split view

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo "       VISUAL DUAL CONTROLLER SDN DEMONSTRATION"
echo "       Split-Pane View for Real-time Monitoring"
echo "============================================================"
echo -e "${NC}"

# Check conda environment
if [ -d "/data/miniforge3/envs/sdn-env" ]; then
    echo -e "${YELLOW}[INFO] Activating conda sdn-env...${NC}"
    source /data/miniforge3/etc/profile.d/conda.sh
    conda activate sdn-env
    if ryu-manager --version > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Using conda sdn-env (Python 3.8, RYU $(ryu-manager --version))${NC}"
    else
        echo -e "${RED}ERROR: RYU not available in conda environment${NC}"
        exit 1
    fi
fi

# Clean up
echo -e "${YELLOW}[INFO] Cleaning up previous setup...${NC}"
./cleanup_network.sh

# Create tmux session with split panes
SESSION_NAME="sdn_visual"
tmux kill-session -t $SESSION_NAME 2>/dev/null

echo -e "${GREEN}[INFO] Creating split-pane tmux layout...${NC}"

# Create new session with primary controller
tmux new-session -d -s $SESSION_NAME -n "SDN-Demo"

# Split window into 3 panes
# Layout:
# +------------------+------------------+
# |                  |                  |
# | Primary          | Secondary        |
# | Controller       | Controller       |
# | (top-left)       | (top-right)      |
# |                  |                  |
# +------------------+------------------+
# |                                     |
# |         Test Output                 |
# |         (bottom)                    |
# |                                     |
# +-------------------------------------+

# Split horizontally first (creates top and bottom)
tmux split-window -v -t $SESSION_NAME:0 -p 40

# Split the top pane vertically (creates left and right controllers)
tmux split-window -h -t $SESSION_NAME:0.0 -p 50

# Now we have:
# Pane 0: Primary Controller (top-left)
# Pane 1: Secondary Controller (top-right)  
# Pane 2: Test Output (bottom)

# Start Primary Controller in pane 0
echo -e "${YELLOW}[INFO] Starting Primary Controller (top-left pane)...${NC}"
tmux send-keys -t $SESSION_NAME:0.0 "echo '=== PRIMARY CONTROLLER (s1-s5) ===' && echo 'Port: 6633' && echo '=================================='" Enter
tmux send-keys -t $SESSION_NAME:0.0 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_controller.py 2>&1 | grep -E 'DIJKSTRA|PATH|LINK|TOPOLOGY|ERROR' --color=always" Enter

# Start Secondary Controller in pane 1
echo -e "${YELLOW}[INFO] Starting Secondary Controller (top-right pane)...${NC}"
tmux send-keys -t $SESSION_NAME:0.1 "echo '=== SECONDARY CONTROLLER (s6-s10) ===' && echo 'Port: 6634' && echo '===================================='" Enter
tmux send-keys -t $SESSION_NAME:0.1 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_controller.py 2>&1 | grep -E 'DIJKSTRA|PATH|LINK|TOPOLOGY|ERROR' --color=always" Enter

# Wait for controllers to initialize
echo -e "${YELLOW}[INFO] Waiting for controllers to initialize...${NC}"
sleep 8

# Check if controllers are running
if netstat -ln | grep ":6633 " > /dev/null; then
    echo -e "${GREEN}✓ Primary Controller running${NC}"
else
    echo -e "${RED}✗ Primary Controller failed${NC}"
fi

if netstat -ln | grep ":6634 " > /dev/null; then
    echo -e "${GREEN}✓ Secondary Controller running${NC}"
else
    echo -e "${RED}✗ Secondary Controller failed${NC}"
fi

# Prepare test script
cat > /tmp/visual_test.sh << 'EOF'
#!/bin/bash
source /data/miniforge3/etc/profile.d/conda.sh
conda activate sdn-env
cd /home/ubuntu/network-lab1

echo "==================================="
echo "    LINK FAILURE TEST OUTPUT"
echo "==================================="
echo ""
echo "Starting test in 3 seconds..."
sleep 3

python3 link_failure_test.py
EOF

chmod +x /tmp/visual_test.sh

# Run test in bottom pane
echo -e "${YELLOW}[INFO] Starting tests in bottom pane...${NC}"
tmux send-keys -t $SESSION_NAME:0.2 "sudo -E /tmp/visual_test.sh" Enter

echo ""
echo -e "${GREEN}${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}    VISUAL DEMO STARTED!${NC}"
echo -e "${GREEN}${BOLD}============================================${NC}"
echo ""

echo -e "${CYAN}Pane Layout:${NC}"
echo "┌─────────────────┬─────────────────┐"
echo "│ Primary Ctrl    │ Secondary Ctrl  │"
echo "│ (s1-s5)         │ (s6-s10)        │"
echo "│ Port: 6633      │ Port: 6634      │"
echo "├─────────────────┴─────────────────┤"
echo "│         Test Output                │"
echo "│         (8 scenarios)              │"
echo "└────────────────────────────────────┘"
echo ""

echo -e "${YELLOW}Commands:${NC}"
echo "  Attach to session:  tmux attach -t sdn_visual"
echo "  Navigate panes:     Ctrl+b then arrow keys"
echo "  Zoom pane:          Ctrl+b then z"
echo "  Kill session:       tmux kill-session -t sdn_visual"
echo ""

if [[ "$1" == "attach" ]]; then
    echo -e "${CYAN}Attaching to tmux session...${NC}"
    tmux attach -t sdn_visual
else
    echo -e "${CYAN}Session running in background. To view:${NC}"
    echo -e "${GREEN}  tmux attach -t sdn_visual${NC}"
fi

# Clean up temp file after a delay
(sleep 60 && rm -f /tmp/visual_test.sh) &