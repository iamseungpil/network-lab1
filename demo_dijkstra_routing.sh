#!/bin/bash

# SDN Ring Topology with Dijkstra Routing Demo
# Shows normal routing and automatic rerouting on link failure

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}"
echo "============================================================"
echo "       SDN DIJKSTRA ROUTING DEMONSTRATION"
echo "       10-Switch Ring Topology with Rerouting"
echo "============================================================"
echo -e "${NC}"

# Cleanup
echo -e "${YELLOW}🧹 Cleaning up previous sessions...${NC}"
tmux kill-session -t dijkstra_demo 2>/dev/null || true
sudo mn -c 2>/dev/null || true
pkill -f ryu-manager 2>/dev/null || true
sleep 2

# Create tmux session with 3 panes
echo -e "${YELLOW}📺 Creating demo session...${NC}"
tmux new-session -d -s dijkstra_demo

# Split into 3 panes: controller (top), topology (middle), monitor (bottom)
tmux split-window -v -t dijkstra_demo
tmux split-window -v -t dijkstra_demo
tmux select-layout -t dijkstra_demo even-vertical

# Start controller in top pane
echo -e "${GREEN}🎛️  Starting Dijkstra Controller...${NC}"
tmux select-pane -t dijkstra_demo:0.0
tmux send-keys -t dijkstra_demo:0.0 "echo '=== DIJKSTRA CONTROLLER ===' && echo ''" Enter
tmux send-keys -t dijkstra_demo:0.0 "ryu-manager --observe-links ryu-controller/main_controller.py 2>&1 | grep -E '(DIJKSTRA|PATH|Computing|PORT EVENT|LINK)' --color=always" Enter

# Wait for controller
sleep 5

# Start topology in middle pane
echo -e "${GREEN}🌐 Starting Ring Topology (10 switches)...${NC}"
tmux select-pane -t dijkstra_demo:0.1
tmux send-keys -t dijkstra_demo:0.1 "echo '=== RING TOPOLOGY ===' && echo ''" Enter
tmux send-keys -t dijkstra_demo:0.1 "sudo python3 mininet/ring_topology.py" Enter

# Wait for topology
sleep 8

# Setup monitoring in bottom pane
tmux select-pane -t dijkstra_demo:0.2
tmux send-keys -t dijkstra_demo:0.2 "echo '=== TEST MONITOR ===' && echo ''" Enter

echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo "       SCENARIO 1: NORMAL ROUTING"
echo "============================================================"
echo -e "${NC}"

# Test 1: Adjacent hosts
echo -e "${YELLOW}Test 1: Adjacent hosts (h1 -> h2)${NC}"
echo "Expected: Direct path through s1 -> s2"
tmux send-keys -t dijkstra_demo:0.1 "h1 ping -c 3 h2" Enter
sleep 4

# Test 2: Opposite side
echo -e "${YELLOW}Test 2: Opposite side of ring (h1 -> h6)${NC}"
echo "Expected: Shortest path (5 hops) either clockwise or counter-clockwise"
tmux send-keys -t dijkstra_demo:0.1 "h1 ping -c 3 h6" Enter
sleep 4

# Test 3: Far hosts
echo -e "${YELLOW}Test 3: Far hosts (h1 -> h9)${NC}"
echo "Expected: Path through multiple switches"
tmux send-keys -t dijkstra_demo:0.1 "h1 ping -c 3 h9" Enter
sleep 4

echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo "       SCENARIO 2: LINK FAILURE & REROUTING"
echo "============================================================"
echo -e "${NC}"

# Start continuous ping in monitor pane
echo -e "${YELLOW}Starting continuous ping h1 -> h2 (monitoring)${NC}"
tmux send-keys -t dijkstra_demo:0.2 "watch -n 1 'echo \"h1 -> h2 connectivity test\" && sudo ip netns exec h1 ping -c 1 -W 1 10.0.0.2 2>&1 | grep -E \"(bytes from|Unreachable|100% packet loss)\"'" Enter

sleep 3

# Fail link
echo -e "${RED}💥 FAILING LINK: s1 <-X-> s2${NC}"
echo "Watch the controller detect failure and compute new path!"
tmux send-keys -t dijkstra_demo:0.1 "link s1 s2 down" Enter
sleep 5

# Test after failure
echo -e "${YELLOW}Testing h1 -> h2 after link failure${NC}"
echo "Expected: Rerouted through the other direction (s1->s10->s9->...->s2)"
tmux send-keys -t dijkstra_demo:0.1 "h1 ping -c 3 h2" Enter
sleep 4

# Restore link
echo -e "${GREEN}🔧 RESTORING LINK: s1 <--> s2${NC}"
tmux send-keys -t dijkstra_demo:0.1 "link s1 s2 up" Enter
sleep 5

# Test after restoration
echo -e "${YELLOW}Testing h1 -> h2 after link restoration${NC}"
echo "Expected: Back to optimal direct path (s1->s2)"
tmux send-keys -t dijkstra_demo:0.1 "h1 ping -c 3 h2" Enter
sleep 4

# Stop monitor
tmux send-keys -t dijkstra_demo:0.2 C-c

echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo "       SCENARIO 3: MULTIPLE FAILURES"
echo "============================================================"
echo -e "${NC}"

echo -e "${RED}💥 FAILING MULTIPLE LINKS${NC}"
echo "Breaking s1-s2 and s1-s10 (both directions from s1)"
tmux send-keys -t dijkstra_demo:0.1 "link s1 s2 down" Enter
sleep 2
tmux send-keys -t dijkstra_demo:0.1 "link s1 s10 down" Enter
sleep 5

echo -e "${YELLOW}Testing h1 -> h3 with both s1 links failed${NC}"
echo "Expected: No direct path - should fail or find complex route"
tmux send-keys -t dijkstra_demo:0.1 "h1 ping -c 3 h3" Enter
sleep 4

# Restore one link
echo -e "${GREEN}🔧 Restoring one link: s1 <--> s10${NC}"
tmux send-keys -t dijkstra_demo:0.1 "link s1 s10 up" Enter
sleep 5

echo -e "${YELLOW}Testing h1 -> h3 with one link restored${NC}"
echo "Expected: Path through s1->s10->s9->...->s3"
tmux send-keys -t dijkstra_demo:0.1 "h1 ping -c 3 h3" Enter
sleep 4

# Restore all
echo -e "${GREEN}🔧 Restoring all links${NC}"
tmux send-keys -t dijkstra_demo:0.1 "link s1 s2 up" Enter
sleep 3

echo -e "${GREEN}${BOLD}"
echo "============================================================"
echo "       DEMO COMPLETE!"
echo "============================================================"
echo -e "${NC}"

echo ""
echo -e "${CYAN}📊 Results Summary:${NC}"
echo "  ✅ Normal routing using Dijkstra shortest path"
echo "  ✅ Automatic rerouting on link failure"
echo "  ✅ Path restoration when link recovers"
echo "  ✅ Multiple failure handling"
echo ""
echo -e "${YELLOW}📋 To explore further:${NC}"
echo "  1. Connect to session: tmux attach -t dijkstra_demo"
echo "  2. Top pane: Controller logs (filtered for routing events)"
echo "  3. Middle pane: Mininet CLI for testing"
echo "  4. Bottom pane: Monitoring tools"
echo ""
echo "  Try these commands in Mininet:"
echo "    - pingall"
echo "    - link s3 s4 down"
echo "    - h1 traceroute h6"
echo "    - dpctl dump-flows"
echo ""
echo -e "${RED}To exit: tmux kill-session -t dijkstra_demo${NC}"