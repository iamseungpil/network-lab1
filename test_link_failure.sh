#!/bin/bash

echo "====================================="
echo "🔧 SDN Link Failure Test Script"
echo "====================================="
echo ""
echo "This script demonstrates link failure and recovery"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run command in mininet
run_mininet_cmd() {
    tmux send-keys -t sdn_demo:0.1 "$1" Enter
    sleep $2
}

echo -e "${GREEN}1. Testing normal state (s1-s2 link UP)${NC}"
run_mininet_cmd "h1 ping -c 3 h2" 4
echo "   Expected: Low latency (~3-5ms)"
echo ""

echo -e "${RED}2. Breaking s1-s2 link${NC}"
echo "   Command: sh ovs-ofctl mod-port s1 s1-eth2 down"
run_mininet_cmd "sh ovs-ofctl mod-port s1 s1-eth2 down" 2
echo ""

echo -e "${YELLOW}3. Testing with link DOWN${NC}"
run_mininet_cmd "h1 ping -c 3 h2" 4
echo "   Expected: Higher latency on first packet (~40-50ms)"
echo ""

echo -e "${GREEN}4. Restoring s1-s2 link${NC}"
echo "   Command: sh ovs-ofctl mod-port s1 s1-eth2 up"
run_mininet_cmd "sh ovs-ofctl mod-port s1 s1-eth2 up" 2
echo ""

echo -e "${GREEN}5. Testing after recovery${NC}"
run_mininet_cmd "h1 ping -c 3 h2" 4
echo "   Expected: Back to low latency (~3-5ms)"
echo ""

echo "====================================="
echo "✅ Test completed!"
echo "====================================="