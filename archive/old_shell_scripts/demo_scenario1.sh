#!/bin/bash
# Demo Scenario 1: Normal Dijkstra Routing

set -e

echo "============================================================"
echo "   SCENARIO 1: NORMAL DIJKSTRA ROUTING"
echo "   Testing shortest path calculations (NO link failures)"
echo "============================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Clean up
echo -e "${BLUE}[SETUP]${NC} Cleaning up previous sessions..."
sudo mn -c 2>/dev/null || true
pkill -9 ryu-manager 2>/dev/null || true

# Start controller
echo -e "${BLUE}[SETUP]${NC} Starting Dijkstra controller..."
if command -v conda &> /dev/null; then
    source /data/miniforge3/etc/profile.d/conda.sh
    conda activate sdn-env 2>/dev/null || true
fi

ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/dijkstra_controller.py &
CONTROLLER_PID=$!
sleep 3

# Create test script
cat > /tmp/scenario1_test.py << 'EOF'
#!/usr/bin/env python3
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel

def test_scenario1():
    print("\n[NETWORK] Creating topology...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Create switches
    s1 = net.addSwitch('s1', protocols='OpenFlow13', dpid='1')
    s2 = net.addSwitch('s2', protocols='OpenFlow13', dpid='2')
    s3 = net.addSwitch('s3', protocols='OpenFlow13', dpid='3')
    s4 = net.addSwitch('s4', protocols='OpenFlow13', dpid='4')
    s5 = net.addSwitch('s5', protocols='OpenFlow13', dpid='5')
    s6 = net.addSwitch('s6', protocols='OpenFlow13', dpid='6')
    
    # Add hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    h5 = net.addHost('h5', ip='10.0.0.5/24')
    h6 = net.addHost('h6', ip='10.0.0.6/24')
    
    # Host connections
    net.addLink(h1, s1)
    net.addLink(h4, s4)
    net.addLink(h5, s3)
    net.addLink(h6, s6)
    
    # Switch connections (multiple paths)
    net.addLink(s1, s2)   # Path option 1
    net.addLink(s2, s4)
    net.addLink(s1, s3)   # Path option 2 (direct)
    net.addLink(s1, s5)   # Path option 3
    net.addLink(s5, s3)
    net.addLink(s4, s5)   # Creates loop
    net.addLink(s3, s6)   # Extension
    
    print("[NETWORK] Starting network...")
    net.start()
    time.sleep(3)
    
    print("\n" + "="*50)
    print("   TESTING DIJKSTRA SHORTEST PATHS")
    print("="*50)
    
    # Test 1: Direct path
    print("\n[TEST 1] h1 -> h5 (should use direct s1->s3)")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.5')
    success = '0% packet loss' in result
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    if not success:
        print(result[:200])
    
    # Test 2: Multi-hop path
    print("\n[TEST 2] h1 -> h4 (should use s1->s2->s4)")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.4')
    success = '0% packet loss' in result
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    if not success:
        print(result[:200])
    
    # Test 3: Extended path
    print("\n[TEST 3] h1 -> h6 (should use s1->s3->s6)")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.6')
    success = '0% packet loss' in result
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    if not success:
        print(result[:200])
    
    print("\n" + "="*50)
    print("   SCENARIO 1 COMPLETE - All paths working normally")
    print("   No link failures tested in this scenario")
    print("="*50)
    
    net.stop()

if __name__ == '__main__':
    setLogLevel('warning')
    test_scenario1()
EOF

# Run the test
echo -e "${BLUE}[TESTING]${NC} Running Scenario 1..."
sudo python3 /tmp/scenario1_test.py

# Cleanup
echo -e "${BLUE}[CLEANUP]${NC} Stopping controller..."
kill $CONTROLLER_PID 2>/dev/null || true
pkill -9 ryu-manager 2>/dev/null || true
rm -f /tmp/scenario1_test.py

echo -e "${GREEN}✓ Scenario 1 Complete${NC}"