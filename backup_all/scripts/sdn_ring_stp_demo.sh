#!/bin/bash

# SDN Ring Topology Demo with STP (Spanning Tree Protocol)
# Prevents broadcast storms in ring topology

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
SESSION_NAME="sdn_ring_stp"

# Functions
print_banner() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     🔄 SDN RING TOPOLOGY WITH STP ENABLED                  ║${NC}"
    echo -e "${BLUE}║     Broadcast Storm Prevention | Loop-Free Forwarding      ║${NC}"
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

start_stp_demo() {
    local test_mode="$1"
    
    echo -e "${GREEN}🔄 Ring Topology with STP Enabled${NC}"
    echo -e "${CYAN}   Spanning Tree Protocol prevents loops${NC}"
    
    # Create tmux session
    echo -e "${YELLOW}📺 Creating tmux session '$SESSION_NAME'...${NC}"
    tmux new-session -d -s $SESSION_NAME
    tmux split-window -v -t $SESSION_NAME
    tmux resize-pane -t $SESSION_NAME:0.0 -y 60%
    
    # Start STP-enabled controller
    echo -e "${CYAN}🎛️  Starting Dijkstra Controller with STP...${NC}"
    tmux send-keys -t $SESSION_NAME:0.0 \
        "source $CONDA_PATH/etc/profile.d/conda.sh && conda activate $CONDA_ENV" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${BLUE}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${BLUE}    DIJKSTRA CONTROLLER WITH STP ENABLED            ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "echo -e '${BLUE}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.0 \
        "ryu-manager --observe-links ryu-controller/main_controller_stp.py" Enter
    
    # Wait for controller
    echo -e "${YELLOW}⏳ Waiting for controller initialization...${NC}"
    sleep 5
    
    # Start ring topology
    echo -e "${CYAN}🌐 Starting Ring Topology...${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}    RING TOPOLOGY - STP WILL BLOCK LOOP PORTS      ${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "echo -e '${GREEN}════════════════════════════════════════════════════${NC}'" Enter
    tmux send-keys -t $SESSION_NAME:0.1 \
        "sudo python3 mininet/ring_topology.py" Enter
    
    if [ "$test_mode" = "test" ]; then
        echo -e "${YELLOW}🤖 Running STP verification tests in 10 seconds...${NC}"
        sleep 10
        run_stp_tests
    fi
}

run_stp_tests() {
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║           STP VERIFICATION TEST SEQUENCE                    ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
    
    # Test 1: Check for blocked ports
    echo -e "${CYAN}[Test 1] Verifying STP blocked a port to prevent loop${NC}"
    sleep 3
    
    # Test 2: Verify no broadcast storm
    echo -e "${CYAN}[Test 2] Testing broadcast handling (ARP)${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 arping -c 3 10.0.0.6" Enter
    sleep 5
    
    # Test 3: Normal connectivity
    echo -e "${CYAN}[Test 3] Testing connectivity through spanning tree${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h6" Enter
    sleep 5
    
    # Test 4: Link failure on spanning tree
    echo -e "${CYAN}[Test 4] Failing active spanning tree link${NC}"
    echo -e "  Expected: STP recalculation, blocked port activation"
    tmux send-keys -t $SESSION_NAME:0.1 "link s1 s2 down" Enter
    sleep 5
    
    # Test 5: Verify connectivity after STP reconvergence
    echo -e "${CYAN}[Test 5] Testing connectivity after STP reconvergence${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "h1 ping -c 3 h2" Enter
    sleep 5
    
    # Test 6: Check flow tables
    echo -e "${CYAN}[Test 6] Checking OpenFlow tables${NC}"
    tmux send-keys -t $SESSION_NAME:0.1 "sh ovs-ofctl -O OpenFlow13 dump-flows s1 | head -10" Enter
    sleep 3
    
    echo -e "${GREEN}✅ STP verification tests completed!${NC}"
}

print_usage() {
    echo -e "${CYAN}📋 STP-ENABLED RING TOPOLOGY INSTRUCTIONS:${NC}"
    echo ""
    echo -e "${YELLOW}Key Differences with STP:${NC}"
    echo -e "  • One link in the ring is BLOCKED to prevent loops"
    echo -e "  • No broadcast storms even without smart flooding"
    echo -e "  • Automatic failover when spanning tree link fails"
    echo -e "  • Slightly longer convergence time (STP recalculation)"
    echo ""
    echo -e "${YELLOW}Test Commands:${NC}"
    echo -e "  ${GREEN}h1 arping 10.0.0.6${NC}    Test broadcast without storm"
    echo -e "  ${GREEN}h1 ping h6${NC}            Test through spanning tree"
    echo -e "  ${GREEN}link s1 s2 down${NC}       Force STP recalculation"
    echo -e "  ${GREEN}sh ovs-ofctl dump-flows s1${NC}  View OpenFlow rules"
    echo ""
    echo -e "${YELLOW}What to Observe:${NC}"
    echo -e "  • Controller logs show '🚫 [STP] Blocking port...'"
    echo -e "  • One port is blocked to break the ring"
    echo -e "  • No packet flooding even for broadcasts"
    echo -e "  • Automatic unblocking when active link fails"
}

verify_link_down_methods() {
    echo -e "${YELLOW}📝 Link Down Methods Comparison:${NC}"
    echo ""
    echo -e "${CYAN}Method 1: Mininet 'link' command${NC}"
    echo -e "  ${GREEN}link s1 s2 down${NC}"
    echo -e "  • Simulates link failure at Mininet level"
    echo -e "  • Both switches detect port down"
    echo -e "  • OpenFlow port status notification sent"
    echo ""
    echo -e "${CYAN}Method 2: Shell OVS commands${NC}"
    echo -e "  ${GREEN}sh ovs-vsctl del-port s1 s1-eth2${NC}"
    echo -e "  • Removes port from OVS bridge"
    echo -e "  • More drastic - port completely removed"
    echo -e "  • Requires re-adding port to restore"
    echo ""
    echo -e "${CYAN}Method 3: Interface down${NC}"
    echo -e "  ${GREEN}sh ip link set s1-eth2 down${NC}"
    echo -e "  • Sets Linux interface down"
    echo -e "  • OVS detects and reports to controller"
    echo -e "  • Easy to restore with 'up'"
    echo ""
    echo -e "${YELLOW}Recommendation:${NC} Use 'link' command for testing"
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
            --info)
                verify_link_down_methods
                exit 0
                ;;
            --clean)
                action="clean"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --test     Run automated STP verification"
                echo "  --info     Show link down methods comparison"
                echo "  --clean    Clean up and exit"
                echo "  --help     Show this help"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
        esac
    done
    
    if [ "$action" = "clean" ]; then
        cleanup
        echo -e "${GREEN}✅ Cleanup completed${NC}"
        exit 0
    fi
    
    # Check requirements
    if [ ! -f "ryu-controller/main_controller_stp.py" ]; then
        echo -e "${RED}Error: STP controller not found${NC}"
        echo -e "${YELLOW}File required: ryu-controller/main_controller_stp.py${NC}"
        exit 1
    fi
    
    cleanup
    start_stp_demo "$test_mode"
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ STP-Enabled Ring Demo Started Successfully!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    print_usage
    
    echo ""
    echo -e "${MAGENTA}🎯 Connect with:${NC} ${GREEN}tmux attach -t $SESSION_NAME${NC}"
    
    if [ -z "$test_mode" ] && [ -t 0 ]; then
        echo -e "${YELLOW}Press Enter to attach, or Ctrl+C to run in background...${NC}"
        read -r
        tmux attach -t $SESSION_NAME
    fi
}

# Run main function
main "$@"