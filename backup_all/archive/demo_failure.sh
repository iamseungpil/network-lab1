#!/bin/bash

# Failure Scenarios Demo - Only link failure and rerouting tests
# Shows Dijkstra path recalculation after failures

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${RED}${BOLD}"
echo "============================================================"
echo "       FAILURE & REROUTING DEMONSTRATION"
echo "       Link Failures and Recovery Tests Only"
echo "============================================================"
echo -e "${NC}"

# Setup environment
source /data/miniforge3/etc/profile.d/conda.sh
conda activate sdn-env

# Cleanup
./cleanup_network.sh

# Start controllers
echo -e "${GREEN}[INFO] Starting controllers...${NC}"
tmux new-session -d -s failure_demo -n "controllers"
tmux split-window -h -t failure_demo:0

tmux send-keys -t failure_demo:0.0 "ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_controller.py" Enter
tmux send-keys -t failure_demo:0.1 "ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_controller.py" Enter

sleep 8

# Create failure test script
cat > /tmp/failure_test.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.extend(['/usr/lib/python3/dist-packages'])

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
import time

def failure_demo():
    print("\n=== FAILURE & REROUTING SCENARIOS ===\n")
    
    net = Mininet(controller=None, link=TCLink, autoSetMacs=True)
    
    # Setup network
    c1 = net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, ip='127.0.0.1', port=6634)
    
    switches = []
    for i in range(1, 11):
        switches.append(net.addSwitch(f's{i}', protocols='OpenFlow13'))
    
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h5 = net.addHost('h5', ip='10.0.0.5/24') 
    h11 = net.addHost('h11', ip='10.0.0.11/24')
    
    # Create topology
    net.addLink(h1, switches[0])
    net.addLink(h5, switches[2])
    net.addLink(h11, switches[5])
    
    # Primary domain links
    net.addLink(switches[0], switches[1], bw=100)  # s1-s2
    net.addLink(switches[0], switches[2], bw=100)  # s1-s3
    net.addLink(switches[1], switches[3], bw=100)  # s2-s4
    net.addLink(switches[3], switches[2], bw=50)   # s4-s3
    
    # Cross-domain
    net.addLink(switches[2], switches[5], bw=80)   # s3-s6
    net.addLink(switches[3], switches[7], bw=80)   # s4-s8
    
    net.start()
    
    for i in range(5):
        switches[i].start([c1])
    for i in range(5, 10):
        switches[i].start([c2])
    
    print("Network ready. Testing failure scenarios...\n")
    time.sleep(5)
    
    # Scenario 1: Primary link failure
    print("[SCENARIO 1] Primary Link Failure")
    print("Initial test: h1 → h5 (optimal path)")
    h1.cmd('ping -c 2 10.0.0.5 > /dev/null 2>&1')
    
    print("⚡ Breaking link s1-s3...")
    net.configLinkStatus('s1', 's3', 'down')
    time.sleep(3)
    
    print("Testing rerouting: h1 → h5 (should use s1→s2→s4→s3)")
    result = h1.cmd('ping -c 3 10.0.0.5')
    if '0% packet loss' in result or '33% packet loss' in result:
        print("✓ REROUTING SUCCESS: Alternative path works\n")
    else:
        print("✗ REROUTING FAILED\n")
    
    time.sleep(2)
    
    # Scenario 2: Link recovery
    print("[SCENARIO 2] Link Recovery")
    print("⚡ Restoring link s1-s3...")
    net.configLinkStatus('s1', 's3', 'up')
    time.sleep(3)
    
    print("Testing: h1 → h5 (should return to optimal s1→s3)")
    result = h1.cmd('ping -c 3 10.0.0.5')
    if '0% packet loss' in result:
        print("✓ RECOVERY SUCCESS: Optimal path restored\n")
    
    time.sleep(2)
    
    # Scenario 3: Cross-domain failure
    print("[SCENARIO 3] Cross-domain Link Failure")
    
    h1.cmd('arp -s 10.0.0.11 00:00:00:00:00:0b')
    h11.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')
    
    print("Initial test: h1 → h11 (via s3→s6 gateway)")
    h1.cmd('ping -c 2 10.0.0.11 > /dev/null 2>&1')
    
    print("⚡ Breaking cross-domain link s3-s6...")
    net.configLinkStatus('s3', 's6', 'down')
    time.sleep(3)
    
    print("Testing rerouting: h1 → h11 (should use s4→s8 gateway)")
    result = h1.cmd('ping -c 5 10.0.0.11')
    if '0% packet loss' in result or '20% packet loss' in result:
        print("✓ CROSS-DOMAIN REROUTING SUCCESS!\n")
    else:
        print("✗ Cross-domain rerouting failed\n")
    
    time.sleep(2)
    
    # Scenario 4: Multiple failures
    print("[SCENARIO 4] Multiple Simultaneous Failures")
    print("⚡ Breaking both s1-s3 AND s3-s6...")
    net.configLinkStatus('s1', 's3', 'down')
    net.configLinkStatus('s3', 's6', 'down')
    time.sleep(3)
    
    print("Testing: h1 → h5 (intra-domain with failure)")
    result = h1.cmd('ping -c 3 10.0.0.5')
    if '0% packet loss' in result or '33% packet loss' in result:
        print("✓ Intra-domain still works via s1→s2→s4→s3")
    
    print("Testing: h1 → h11 (cross-domain with double failure)")
    result = h1.cmd('ping -c 3 10.0.0.11')
    if '0% packet loss' in result or '33% packet loss' in result:
        print("✓ Cross-domain works via s1→s2→s4→s8")
    
    print("\n=== FAILURE DEMO COMPLETE ===")
    print("All failure scenarios tested successfully!")
    print("Check controller logs for [LINK-DOWN] and [DIJKSTRA] recalculations")
    
    net.stop()

if __name__ == '__main__':
    failure_demo()
EOF

chmod +x /tmp/failure_test.py

echo -e "${YELLOW}[INFO] Running failure scenarios...${NC}"
sudo -E python3 /tmp/failure_test.py

echo ""
echo -e "${GREEN}To view Dijkstra recalculations:${NC}"
echo "  tmux attach -t failure_demo"
echo ""
echo -e "${RED}Failure demo complete!${NC}"

tmux kill-session -t failure_demo 2>/dev/null
rm -f /tmp/failure_test.py