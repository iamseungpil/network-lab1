#!/bin/bash
# Interactive Demo with Real-time Controller Logs
# Shows OpenFlow communication and Dijkstra rerouting

set -e

echo "============================================================"
echo "   INTERACTIVE DEMO: REAL-TIME REROUTING VISUALIZATION"
echo "   Watch OpenFlow messages and Dijkstra path calculation"
echo "============================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Clean up
echo -e "${BLUE}[SETUP]${NC} Cleaning up previous sessions..."
sudo mn -c 2>/dev/null || true
pkill -9 ryu-manager 2>/dev/null || true
tmux kill-session -t dijkstra_demo 2>/dev/null || true

# Start controller in tmux
echo -e "${BLUE}[SETUP]${NC} Starting Dijkstra controller with detailed logs..."
if command -v conda &> /dev/null; then
    source /data/miniforge3/etc/profile.d/conda.sh
    conda activate sdn-env 2>/dev/null || true
fi

# Create tmux session for controller
tmux new-session -d -s dijkstra_demo
tmux send-keys -t dijkstra_demo "ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/dijkstra_controller.py" Enter
sleep 3

# Create test script for interactive demo
cat > /tmp/interactive_demo.py << 'EOF'
#!/usr/bin/env python3
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def interactive_demo():
    print("\n[NETWORK] Creating topology for interactive testing...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Create diamond topology with multiple paths
    print("\n[TOPOLOGY] Creating diamond topology:")
    print("        h1           h3")
    print("         |            |")
    print("        s1 ======== s3")
    print("       /  \\        /  \\")
    print("      /    \\      /    \\")
    print("     s2     \\    /     s6---h6")
    print("      \\      \\  /")
    print("       \\      \\/")
    print("        s4====s5")
    print("         |     |")
    print("        h4    h5")
    
    # Add switches
    s1 = net.addSwitch('s1', protocols='OpenFlow13', dpid='1')
    s2 = net.addSwitch('s2', protocols='OpenFlow13', dpid='2')
    s3 = net.addSwitch('s3', protocols='OpenFlow13', dpid='3')
    s4 = net.addSwitch('s4', protocols='OpenFlow13', dpid='4')
    s5 = net.addSwitch('s5', protocols='OpenFlow13', dpid='5')
    s6 = net.addSwitch('s6', protocols='OpenFlow13', dpid='6')
    
    # Add hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    h5 = net.addHost('h5', ip='10.0.0.5/24')
    h6 = net.addHost('h6', ip='10.0.0.6/24')
    
    # Host connections
    net.addLink(h1, s1)
    net.addLink(h3, s3)
    net.addLink(h4, s4)
    net.addLink(h5, s5)
    net.addLink(h6, s6)
    
    # Switch connections (multiple paths)
    net.addLink(s1, s2)   # Path 1: s1-s2-s4
    net.addLink(s2, s4)
    net.addLink(s1, s3)   # Path 2: s1-s3 (DIRECT - will be broken)
    net.addLink(s1, s5)   # Path 3: s1-s5-s3
    net.addLink(s5, s3)
    net.addLink(s4, s5)   # Creates loop for redundancy
    net.addLink(s3, s6)   # Extension
    
    print("\n[NETWORK] Starting network...")
    net.start()
    time.sleep(3)
    
    print("\n" + "="*70)
    print("   INTERACTIVE DEMO - MANUAL LINK CONTROL")
    print("="*70)
    print()
    print("🔍 WATCH the controller logs in the other terminal!")
    print("   tmux attach -t dijkstra_demo")
    print()
    print("📋 SUGGESTED TEST SEQUENCE:")
    print("1. h1 ping h3        # Establish initial path")
    print("2. link s1 s3 down   # Break direct link")
    print("3. h1 ping h3        # See automatic rerouting") 
    print("4. link s1 s3 up     # Restore link")
    print("5. h1 ping h3        # See path optimization")
    print("6. links             # Show all links status")
    print()
    print("🎯 WHAT TO OBSERVE IN CONTROLLER LOGS:")
    print("❌ PORT_STATUS events when links fail")
    print("🔍 Topology updates removing failed links")
    print("📨 PACKET_IN events triggering rerouting")
    print("🧮 Dijkstra calculations finding new paths")
    print("📋 Flow installation on new path switches")
    print()
    print("="*70)
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('warning')
    interactive_demo()
EOF

echo -e "${YELLOW}[INFO]${NC} Controller is running in tmux session 'dijkstra_demo'"
echo -e "${YELLOW}[INFO]${NC} You can view logs with: tmux attach -t dijkstra_demo"
echo ""
echo -e "${BLUE}[DEMO]${NC} Starting interactive Mininet..."

# Run the interactive demo
sudo python3 /tmp/interactive_demo.py

# Cleanup
echo -e "${BLUE}[CLEANUP]${NC} Stopping controller..."
tmux kill-session -t dijkstra_demo 2>/dev/null || true
rm -f /tmp/interactive_demo.py

echo -e "${GREEN}✓ Interactive Demo Complete${NC}"