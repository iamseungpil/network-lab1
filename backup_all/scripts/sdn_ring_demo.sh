#!/bin/bash

# SDN Ring Topology Demo Script
# 10 switches in a ring structure with Dijkstra routing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
CONDA_PATH="/data/miniforge3"
CONDA_ENV="sdn-lab"
SESSION_NAME="sdn_ring"

# Functions
print_banner() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       🔄 SDN RING TOPOLOGY - DIJKSTRA ROUTING              ║${NC}"
    echo -e "${BLUE}║       10 Switches | Ring Structure | Dynamic Routing       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
}

cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up existing sessions...${NC}"
    tmux kill-session -t $SESSION_NAME 2>/dev/null || true
    sudo pkill -f ryu-manager 2>/dev/null || true
    sudo pkill -f mininet 2>/dev/null || true
    sudo mn -c 2>/dev/null || true
    sleep 2
}

check_requirements() {
    echo -e "${CYAN}🔍 Checking requirements...${NC}"
    
    # Check tmux
    if ! command -v tmux &> /dev/null; then
        echo -e "${RED}✗ tmux is required but not installed${NC}"
        exit 1
    fi
    
    # Check conda environment
    if [ ! -d "$CONDA_PATH/envs/$CONDA_ENV" ]; then
        echo -e "${RED}✗ Conda environment '$CONDA_ENV' not found${NC}"
        echo -e "${YELLOW}  Please create it with: conda create -n $CONDA_ENV python=3.9${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All requirements satisfied${NC}"
}

start_ring_demo() {
    local test_mode="$1"
    
    echo -e "${GREEN}🔄 Selected Topology: Ring (10 switches, 10 hosts)${NC}"
    echo -e "${CYAN}   Each switch has 1 host, switches form a ring${NC}"
    
    # Create tmux session with proper layout
    echo -e "${YELLOW}📺 Creating tmux session '$SESSION_NAME'...${NC}"
    tmux new-session -d -s $SESSION_NAME
    
    # Split window horizontally (top: controller, bottom: mininet)
    tmux split-window -v -t $SESSION_NAME
    
    # Make top pane slightly larger (60%)
    tmux resize-pane -t $SESSION_NAME:0.0 -y 60%
    
    # Start controller in top pane
    echo -e "${CYAN}🎛️  Starting Dijkstra Controller...${NC}"
    tmux send-keys -t $SESSION_NAME:0.0 \
        "source $CONDA_PATH/etc/profile.d/conda.sh && conda activate $CONDA_ENV" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${BLUE}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${BLUE}      DIJKSTRA SDN CONTROLLER - RING TOPOLOGY       ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${BLUE}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo 'Waiting for topology discovery...'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "ryu-manager --observe-links ryu-controller/main_controller.py" Enter
    
    # Wait for controller to initialize
    echo -e "${YELLOW}⏳ Waiting for controller initialization...${NC}"
    sleep 5
    
    # Start topology in bottom pane
    echo -e "${CYAN}🌐 Starting Ring Topology...${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}         MININET RING TOPOLOGY                      ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}    s1---s2---s3---s4---s5                         ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}    |                    |                         ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}   s10                   s6                        ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}    |                    |                         ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}    s9---s8---s7---------                         ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "sudo python3 mininet/ring_topology.py" Enter
    
    # Run automated tests if requested
    if [ "$test_mode" = "test" ]; then
        echo -e "${YELLOW}🤖 Running automated tests in 10 seconds...${NC}"
        sleep 10
        run_ring_tests
    fi
}

run_ring_tests() {
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║             RING TOPOLOGY TEST SEQUENCE                     ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
    
    # Test 1: Adjacent hosts (short path)
    echo -e "${CYAN}[Test 1] Adjacent Hosts (h1 -> h2)${NC}"
    echo -e "  Expected: Direct path through s1-s2"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h2" Enter
    sleep 5
    
    # Test 2: Opposite side of ring (equal paths)
    echo -e "${CYAN}[Test 2] Opposite Side (h1 -> h6)${NC}"
    echo -e "  Expected: Two equal-cost paths (5 hops each)"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h6" Enter
    sleep 5
    
    # Test 3: Cross-ring communication
    echo -e "${CYAN}[Test 3] Cross-Ring (h3 -> h8)${NC}"
    echo -e "  Expected: Shortest path selection"
    tmux send-keys -t $SESSION_NAME:0.1 "h3 ping -c 3 h8" Enter
    sleep 5
    
    # Test 4: Link failure in ring
    echo -e "${CYAN}[Test 4] Link Failure (s1-s2 down)${NC}"
    echo -e "  Expected: Reroute via opposite direction"
    tmux send-keys -t $SESSION_NAME:0.1 "link s1 s2 down" Enter
    sleep 3
    
    # Test 5: Verify rerouting
    echo -e "${CYAN}[Test 5] Rerouting Test (h1 -> h2 after failure)${NC}"
    echo -e "  Expected: Long path around the ring (9 hops)"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h2" Enter
    sleep 5
    
    # Test 6: Second link failure (test ring break)
    echo -e "${CYAN}[Test 6] Second Link Failure (s5-s6 down)${NC}"
    echo -e "  Expected: Ring is broken, some hosts unreachable"
    tmux send-keys -t $SESSION_NAME:0.1 "link s5 s6 down" Enter
    sleep 3
    
    # Test 7: Connectivity after ring break
    echo -e "${CYAN}[Test 7] Testing Connectivity with Broken Ring${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h7" Enter
    sleep 5
    
    # Test 8: Restore links
    echo -e "${CYAN}[Test 8] Link Recovery${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "link s1 s2 up" Enter
    sleep 2
    tmux send-keys -t $SESSION_NAME:0.1 "link s5 s6 up" Enter
    sleep 3
    
    # Test 9: Full connectivity test
    echo -e "${CYAN}[Test 9] Full Ring Connectivity Test${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "pingall" Enter
    sleep 15
    
    echo -e "${GREEN}✅ Ring topology tests completed!${NC}"
}

print_usage() {
    echo -e "${CYAN}📋 USAGE INSTRUCTIONS:${NC}"
    echo ""
    echo -e "${YELLOW}To connect to the session:${NC}"
    echo -e "  ${GREEN}tmux attach -t $SESSION_NAME${NC}"
    echo ""
    echo -e "${YELLOW}Navigation:${NC}"
    echo -e "  ${GREEN}Ctrl+b + ↑/↓${NC}     Switch between panes"
    echo -e "  ${GREEN}Ctrl+b + d${NC}       Detach from session"
    echo -e "  ${GREEN}Ctrl+b + [${NC}       Scroll mode (q to exit)"
    echo ""
    echo -e "${YELLOW}Ring Topology Test Commands:${NC}"
    echo -e "  ${GREEN}h1 ping h2${NC}       Test adjacent hosts (1 hop)"
    echo -e "  ${GREEN}h1 ping h6${NC}       Test opposite side (5 hops)"
    echo -e "  ${GREEN}h1 ping h10${NC}      Test around ring (1 or 9 hops)"
    echo -e "  ${GREEN}link s1 s2 down${NC}  Break ring at s1-s2"
    echo -e "  ${GREEN}link s1 s2 up${NC}    Restore ring at s1-s2"
    echo -e "  ${GREEN}pingall${NC}          Test all 90 host pairs"
    echo -e "  ${GREEN}nodes${NC}            List all nodes"
    echo -e "  ${GREEN}links${NC}            Show ring links"
    echo -e "  ${GREEN}exit${NC}             Exit Mininet"
    echo ""
    echo -e "${YELLOW}Expected Routing Behavior:${NC}"
    echo -e "  • Ring provides 2 paths between any nodes"
    echo -e "  • Controller selects shortest path"
    echo -e "  • Link failure forces opposite direction"
    echo -e "  • Two failures can break connectivity"
    echo ""
    echo -e "${YELLOW}Controller Logs Show:${NC}"
    echo -e "  • 🔌 10 switches connecting"
    echo -e "  • 🔗 20 links discovered (bidirectional)"
    echo -e "  • 📦 Packet processing details"
    echo -e "  • 🛤️  Dijkstra path calculations"
    echo -e "  • 💥 Link failure detection"
    echo -e "  • ✅ Rerouting decisions"
}

# Main script
main() {
    print_banner
    
    # Parse arguments
    local action="start"
    local test_mode=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --test)
                test_mode="test"
                shift
                ;;
            --clean)
                action="clean"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --test            Run automated test sequence"
                echo "  --clean           Clean up and exit"
                echo "  --help, -h        Show this help"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
        esac
    done
    
    # Execute action
    if [ "$action" = "clean" ]; then
        cleanup
        echo -e "${GREEN}✅ Cleanup completed${NC}"
        exit 0
    fi
    
    # Normal startup
    check_requirements
    cleanup
    start_ring_demo "$test_mode"
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Ring Topology Demo Started Successfully!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    print_usage
    
    echo ""
    echo -e "${MAGENTA}🎯 Ready! Connect with:${NC} ${GREEN}tmux attach -t $SESSION_NAME${NC}"
    
    # Auto-attach if in interactive mode and test mode not enabled
    if [ -z "$test_mode" ] && [ -t 0 ]; then
        echo -e "${YELLOW}Press Enter to attach to session, or Ctrl+C to run in background...${NC}"
        read -r
        tmux attach -t $SESSION_NAME
    fi
}

# Run main function
main "$@"