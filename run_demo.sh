#!/bin/bash

# SDN Ring Topology Complete Demo
# Shows normal routing and link failure recovery with clear logs

set -e

# Fix terminal database issue
export TERM=xterm-256color
export TERMINFO=/lib/terminfo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m'

# Configuration
CONDA_PATH="/data/miniforge3"
CONDA_ENV="sdn-lab"
SESSION_NAME="sdn_demo"

print_banner() {
    clear
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     SDN RING TOPOLOGY - COMPLETE DEMONSTRATION             ║${NC}"
    echo -e "${BLUE}║     STP + Dijkstra Routing + Link Failure Recovery         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up environment...${NC}"
    tmux kill-session -t $SESSION_NAME 2>/dev/null || true
    sudo pkill -f ryu-manager 2>/dev/null || true
    sudo pkill -f mininet 2>/dev/null || true
    sudo mn -c 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✓ Environment cleaned${NC}"
}

check_requirements() {
    echo -e "${CYAN}🔍 Checking requirements...${NC}"
    
    # Check tmux
    if ! command -v tmux &> /dev/null; then
        echo -e "${RED}✗ tmux is required but not installed${NC}"
        echo -e "${YELLOW}  Install with: sudo apt install tmux${NC}"
        exit 1
    fi
    
    # Check conda environment
    if [ ! -d "$CONDA_PATH/envs/$CONDA_ENV" ]; then
        echo -e "${RED}✗ Conda environment '$CONDA_ENV' not found${NC}"
        echo -e "${YELLOW}  Create with: conda create -n $CONDA_ENV python=3.9${NC}"
        exit 1
    fi
    
    # Check controller file
    if [ ! -f "ryu-controller/enhanced_controller.py" ]; then
        echo -e "${RED}✗ Enhanced controller not found${NC}"
        exit 1
    fi
    
    # Check topology file
    if [ ! -f "mininet/ring_topology.py" ]; then
        echo -e "${RED}✗ Ring topology not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All requirements satisfied${NC}"
}

start_demo() {
    echo ""
    echo -e "${CYAN}📺 Creating tmux session with 3 panes...${NC}"
    
    # Create tmux session with initial window
    tmux new-session -d -s $SESSION_NAME
    
    # Split horizontally (top 60% for controller, bottom 40% for mininet)
    tmux split-window -v -t $SESSION_NAME -p 40
    
    # Split bottom pane vertically (for monitoring)
    tmux split-window -h -t $SESSION_NAME:0.1
    
    # Pane 0: Controller (top)
    echo -e "${CYAN}🎛️  Starting Enhanced Controller (Pane 0 - Top)...${NC}"
    tmux send-keys -t $SESSION_NAME:0.0 \
        "source $CONDA_PATH/etc/profile.d/conda.sh && conda activate $CONDA_ENV" Enter
    tmux send-keys -t $SESSION_NAME:0.0 "clear" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${WHITE}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${WHITE}          ENHANCED SDN CONTROLLER                   ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${WHITE}     Watch for: STP, DIJKSTRA, LINK FAILURE         ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${WHITE}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 "echo ''" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "ryu-manager --observe-links ryu-controller/fixed_controller.py" Enter
    
    # Wait for controller initialization
    echo -e "${YELLOW}⏳ Waiting for controller startup (5 seconds)...${NC}"
    sleep 5
    
    # Pane 1: Mininet (bottom-left)
    echo -e "${CYAN}🌐 Starting Ring Topology (Pane 1 - Bottom Left)...${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "clear" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}         MININET RING TOPOLOGY (10 switches)        ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 "echo ''" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "sudo python3 mininet/ring_topology.py" Enter
    
    # Pane 2: Monitor (bottom-right)
    echo -e "${CYAN}📊 Setting up Monitor (Pane 2 - Bottom Right)...${NC}"
    tmux send-keys -t $SESSION_NAME:0.2 "clear" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${MAGENTA}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${MAGENTA}              TEST SCENARIO MONITOR                  ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${MAGENTA}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 "echo ''" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo 'Ready for monitoring. Scenario will start in 10 seconds...'" Enter
    
    echo -e "${YELLOW}⏳ Waiting for topology discovery (10 seconds)...${NC}"
    sleep 10
}

run_scenario() {
    echo ""
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║              STARTING DEMO SCENARIO                         ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Update monitor
    tmux send-keys -t $SESSION_NAME:0.2 "clear" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${YELLOW}═══════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${YELLOW}SCENARIO 1: Normal Routing${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${YELLOW}═══════════════════════════════════════════════${NC}'" Enter
    
    # Test 1: Adjacent hosts
    echo -e "${CYAN}[Test 1] Adjacent hosts (h1 → h2)${NC}"
    echo -e "         Expected: Direct path, 1 hop"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 2 h2" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo '[Test 1] h1 ping h2 - Direct path (1 hop)'" Enter
    sleep 4
    
    # Test 2: Opposite side
    echo -e "${CYAN}[Test 2] Opposite side (h1 → h6)${NC}"
    echo -e "         Expected: 5 hops through STP path"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 2 h6" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo '[Test 2] h1 ping h6 - Opposite side (5 hops)'" Enter
    sleep 4
    
    # Show current state
    echo -e "${CYAN}[Info] Checking current topology state${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "links" Enter
    sleep 2
    
    # Update monitor for failure scenario
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo ''" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${YELLOW}═══════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${YELLOW}SCENARIO 2: Link Failure & Recovery${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${YELLOW}═══════════════════════════════════════════════${NC}'" Enter
    
    # Test 3: Link failure
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║           SIMULATING LINK FAILURE: s1-s2                    ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    
    tmux send-keys -t $SESSION_NAME:0.1 "link s1 s2 down" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${RED}[FAILURE] Link s1-s2 DOWN${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo 'Watch controller logs for:'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo '  - LINK FAILURE DETECTED'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo '  - STP recalculation'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo '  - DIJKSTRA path recomputation'" Enter
    
    echo -e "${YELLOW}⏳ Waiting for convergence (5 seconds)...${NC}"
    sleep 5
    
    # Test 4: Verify rerouting
    echo -e "${CYAN}[Test 3] Testing rerouting (h1 → h2 after failure)${NC}"
    echo -e "         Expected: Long path around ring (9 hops)"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h2" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo '[Test 3] h1 ping h2 - Rerouted path (9 hops)'" Enter
    sleep 5
    
    # Test 5: Link recovery
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              RECOVERING LINK: s1-s2                         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    
    tmux send-keys -t $SESSION_NAME:0.1 "link s1 s2 up" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo -e '${GREEN}[RECOVERY] Link s1-s2 UP${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo 'STP will recalculate spanning tree'" Enter
    
    echo -e "${YELLOW}⏳ Waiting for reconvergence (5 seconds)...${NC}"
    sleep 5
    
    # Test 6: Verify recovery
    echo -e "${CYAN}[Test 4] Testing after recovery (h1 → h2)${NC}"
    echo -e "         Expected: Direct path restored (1 hop)"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 2 h2" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo '[Test 4] h1 ping h2 - Path restored (1 hop)'" Enter
    sleep 4
    
    # Final test
    echo -e "${CYAN}[Test 5] Full connectivity test${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "pingall" Enter
    tmux send-keys -t $SESSION_NAME:0.2 \
        "echo '[Test 5] Running pingall - testing all 90 paths'" Enter
    
    echo ""
    echo -e "${GREEN}✅ Demo scenario completed!${NC}"
}

print_instructions() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    HOW TO USE                               ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}TMux Controls:${NC}"
    echo -e "  ${GREEN}tmux attach -t $SESSION_NAME${NC}  - Connect to session"
    echo -e "  ${GREEN}Ctrl+b + 0/1/2${NC}              - Switch to pane 0/1/2"
    echo -e "  ${GREEN}Ctrl+b + arrows${NC}             - Navigate between panes"
    echo -e "  ${GREEN}Ctrl+b + d${NC}                  - Detach from session"
    echo -e "  ${GREEN}Ctrl+b + [${NC}                  - Scroll mode (q to exit)"
    echo ""
    echo -e "${YELLOW}What to observe in Controller logs (Top pane):${NC}"
    echo -e "  ${CYAN}[STP]${NC}      - Spanning tree blocking ports to prevent loops"
    echo -e "  ${CYAN}[DIJKSTRA]${NC} - Path calculation showing selected route"
    echo -e "  ${CYAN}[LINK]${NC}     - Link discovery and failure detection"
    echo -e "  ${CYAN}[HOST]${NC}     - Host location learning"
    echo -e "  ${CYAN}[FLOOD]${NC}    - Controlled flooding (STP-safe)"
    echo ""
    echo -e "${YELLOW}Key Events to Watch:${NC}"
    echo -e "  1. ${WHITE}Initial STP Computation${NC} - One port blocked in ring"
    echo -e "  2. ${WHITE}Path Calculation${NC} - Shows all hops in selected path"
    echo -e "  3. ${WHITE}Link Failure${NC} - Immediate detection and rerouting"
    echo -e "  4. ${WHITE}STP Recalculation${NC} - Unblocks alternative path"
    echo ""
    echo -e "${YELLOW}Manual Testing Commands (in Mininet):${NC}"
    echo -e "  ${GREEN}h1 ping h6${NC}         - Test long path"
    echo -e "  ${GREEN}link s3 s4 down${NC}    - Simulate another failure"
    echo -e "  ${GREEN}links${NC}              - Show all links status"
    echo -e "  ${GREEN}nodes${NC}              - List all nodes"
}

# Main execution
main() {
    print_banner
    
    # Parse arguments
    case "${1:-}" in
        --clean)
            cleanup
            echo -e "${GREEN}✅ Cleanup completed${NC}"
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  (none)     Run complete demo"
            echo "  --clean    Clean up environment"
            echo "  --help     Show this help"
            exit 0
            ;;
    esac
    
    # Run demo
    check_requirements
    cleanup
    start_demo
    run_scenario
    print_instructions
    
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🎯 Demo is running! Connect with:${NC} ${WHITE}tmux attach -t $SESSION_NAME${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    
    # Option to auto-attach
    if [ -t 0 ]; then
        echo ""
        echo -e "${YELLOW}Press Enter to attach to tmux session, or Ctrl+C to keep running in background...${NC}"
        read -r
        tmux attach -t $SESSION_NAME
    fi
}

# Run main function
main "$@"