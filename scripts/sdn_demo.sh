#!/bin/bash

# SDN Dijkstra Demo Script - Unified Version
# Supports both simple and complex topologies with dynamic routing

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
SESSION_NAME="sdn_demo"

# Functions
print_banner() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          🚀 SDN DIJKSTRA ROUTING DEMO                      ║${NC}"
    echo -e "${BLUE}║          Dynamic Path Computation & Failure Recovery       ║${NC}"
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

start_demo() {
    local topology="$1"
    local test_mode="$2"
    
    # Determine topology file
    local topo_file="simple_topology.py"
    local topo_desc="Diamond (4 switches, 4 hosts)"
    
    if [ "$topology" = "complex" ] || [ "$topology" = "10sw" ]; then
        topo_file="graph_topology_10sw_20h.py"
        topo_desc="Complex Graph (10 switches, 20 hosts)"
    fi
    
    echo -e "${GREEN}📐 Selected Topology: $topo_desc${NC}"
    
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
        "echo -e '${BLUE}         DIJKSTRA SDN CONTROLLER                    ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${BLUE}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "ryu-manager --observe-links ryu-controller/main_controller.py" Enter
    
    # Wait for controller to initialize
    echo -e "${YELLOW}⏳ Waiting for controller initialization...${NC}"
    sleep 5
    
    # Start topology in bottom pane
    echo -e "${CYAN}🌐 Starting Mininet Topology...${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}         MININET TOPOLOGY: $topo_desc              ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "sudo python3 $topo_file" Enter
    
    # Run automated tests if requested
    if [ "$test_mode" = "test" ]; then
        echo -e "${YELLOW}🤖 Running automated tests in 10 seconds...${NC}"
        sleep 10
        run_automated_tests
    fi
}

run_automated_tests() {
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║                 AUTOMATED TEST SEQUENCE                     ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
    
    # Test 1: Basic connectivity
    echo -e "${CYAN}[Test 1] Basic Connectivity Test${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h4" Enter
    sleep 5
    
    # Test 2: Cross connectivity
    echo -e "${CYAN}[Test 2] Cross Connectivity Test${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "h2 ping -c 3 h3" Enter
    sleep 5
    
    # Test 3: Link failure
    echo -e "${CYAN}[Test 3] Link Failure Simulation${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "link s1 s2 down" Enter
    sleep 3
    
    # Test 4: Rerouting verification
    echo -e "${CYAN}[Test 4] Dynamic Rerouting Test${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h4" Enter
    sleep 5
    
    # Test 5: Link recovery
    echo -e "${CYAN}[Test 5] Link Recovery Test${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "link s1 s2 up" Enter
    sleep 3
    
    # Test 6: Full connectivity
    echo -e "${CYAN}[Test 6] Full Network Connectivity${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "pingall" Enter
    sleep 10
    
    echo -e "${GREEN}✅ Automated tests completed!${NC}"
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
    echo -e "${YELLOW}Mininet CLI Commands:${NC}"
    echo -e "  ${GREEN}h1 ping h4${NC}       Test connectivity"
    echo -e "  ${GREEN}h1 ping -c 5 h3${NC}  Ping with count"
    echo -e "  ${GREEN}link s1 s2 down${NC}  Simulate link failure"
    echo -e "  ${GREEN}link s1 s2 up${NC}    Restore link"
    echo -e "  ${GREEN}pingall${NC}          Test all connections"
    echo -e "  ${GREEN}nodes${NC}            List all nodes"
    echo -e "  ${GREEN}links${NC}            Show all links"
    echo -e "  ${GREEN}exit${NC}             Exit Mininet"
    echo ""
    echo -e "${YELLOW}Controller Logs Show:${NC}"
    echo -e "  • 🔌 Switch connections"
    echo -e "  • 🔗 Topology discovery"
    echo -e "  • 📦 Packet processing"
    echo -e "  • 🛤️  Path calculations"
    echo -e "  • 💥 Failure detection"
    echo -e "  • ✅ Dynamic rerouting"
}

# Main script
main() {
    print_banner
    
    # Parse arguments
    local topology="simple"
    local action="start"
    local test_mode=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --complex|--10sw)
                topology="complex"
                shift
                ;;
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
                echo "  --complex, --10sw  Use complex 10-switch topology"
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
    start_demo "$topology" "$test_mode"
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ SDN Demo Started Successfully!${NC}"
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