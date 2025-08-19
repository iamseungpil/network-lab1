#!/bin/bash
# Simple demo with real-time monitoring

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}    SIMPLE DIJKSTRA DEMO WITH MONITORING${NC}"
echo -e "${CYAN}============================================================${NC}"

# Clean up
echo -e "${BLUE}[CLEANUP]${NC} Cleaning environment..."
sudo mn -c 2>/dev/null || true
pkill -9 ryu-manager 2>/dev/null || true
tmux kill-session -t sdn_demo 2>/dev/null || true

# Create tmux session with 2 panes
echo -e "${BLUE}[SETUP]${NC} Creating monitoring session..."
tmux new-session -d -s sdn_demo
tmux split-window -t sdn_demo -h

# Start controller in left pane
echo -e "${BLUE}[CONTROLLER]${NC} Starting controller in left pane..."
tmux send-keys -t sdn_demo:0.0 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-lab" Enter
tmux send-keys -t sdn_demo:0.0 "echo -e '${GREEN}===== CONTROLLER LOGS =====${NC}'" Enter
tmux send-keys -t sdn_demo:0.0 "ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/dijkstra_controller_10sw.py 2>&1 | grep --line-buffered -E 'DIJKSTRA|PATH|PORT|REROUTING|FLOW'" Enter

sleep 5

# Create test network script
cat > /tmp/simple_test.py << 'EOF'
#!/usr/bin/env python3
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def simple_demo():
    print("\n🔨 Building simple 4-switch diamond topology...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Diamond topology
    #     s1
    #    /  \
    #   s2  s3
    #    \  /
    #     s4
    
    s1 = net.addSwitch('s1', protocols='OpenFlow13', dpid='1')
    s2 = net.addSwitch('s2', protocols='OpenFlow13', dpid='2')
    s3 = net.addSwitch('s3', protocols='OpenFlow13', dpid='3')
    s4 = net.addSwitch('s4', protocols='OpenFlow13', dpid='4')
    
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    
    # Connect hosts
    net.addLink(h1, s1)
    net.addLink(h4, s4)
    
    # Diamond links
    net.addLink(s1, s2)
    net.addLink(s1, s3)
    net.addLink(s2, s4)
    net.addLink(s3, s4)
    
    print("✅ Starting network...")
    net.start()
    time.sleep(3)
    
    print("\n" + "="*60)
    print(" DEMO COMMANDS")
    print("="*60)
    print(" TEST:")
    print("   h1 ping h4           # Test connectivity")
    print("")
    print(" SIMULATE FAILURE:")
    print("   link s1 s2 down      # Break left path")
    print("   h1 ping h4           # Should reroute via s3")
    print("   link s1 s2 up        # Restore path")
    print("")
    print(" Watch left pane for controller events!")
    print("="*60 + "\n")
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('warning')
    simple_demo()
EOF

# Run test in right pane
echo -e "${BLUE}[NETWORK]${NC} Starting test network in right pane..."
tmux send-keys -t sdn_demo:0.1 "echo -e '${YELLOW}===== NETWORK TEST =====${NC}'" Enter
tmux send-keys -t sdn_demo:0.1 "sleep 2 && sudo python3 /tmp/simple_test.py" Enter

echo -e "\n${GREEN}✅ Demo ready!${NC}"
echo -e "${YELLOW}Attaching to tmux session...${NC}"
echo -e "${YELLOW}Use Ctrl+B then D to detach${NC}\n"

# Attach to session
tmux attach -t sdn_demo