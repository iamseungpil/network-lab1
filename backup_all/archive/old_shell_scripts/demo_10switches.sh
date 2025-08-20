#!/bin/bash
# 10-Switch Topology Demo with Real-time Monitoring

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}     10-SWITCH DIJKSTRA SDN DEMO WITH MONITORING${NC}"
echo -e "${CYAN}============================================================${NC}"

# Function to clean up
cleanup() {
    echo -e "\n${BLUE}[CLEANUP]${NC} Stopping all sessions..."
    tmux kill-session -t controller 2>/dev/null || true
    tmux kill-session -t monitor 2>/dev/null || true
    sudo mn -c 2>/dev/null || true
    pkill -9 ryu-manager 2>/dev/null || true
}

# Clean up first
cleanup

# Check if conda environment exists
if command -v conda &> /dev/null; then
    echo -e "${BLUE}[SETUP]${NC} Activating SDN environment..."
    source /data/miniforge3/etc/profile.d/conda.sh
    conda activate sdn-lab 2>/dev/null || true
fi

# Start controller in tmux with logging
echo -e "${BLUE}[CONTROLLER]${NC} Starting 10-switch Dijkstra controller..."
tmux new-session -d -s controller -n "Controller"
tmux send-keys -t controller "ryu-manager --ofp-tcp-listen-port 6633 --verbose ryu-controller/dijkstra_controller_10sw.py" Enter

# Create monitoring session
echo -e "${BLUE}[MONITOR]${NC} Creating monitoring session..."
tmux new-session -d -s monitor -n "Logs"

# Split monitor window into panes
tmux split-window -t monitor -v -p 30  # Bottom pane for commands
tmux select-pane -t monitor:0.0

# Start log monitoring in top pane
tmux send-keys -t monitor:0.0 "echo 'Controller Logs - Watching for events...'" Enter
tmux send-keys -t monitor:0.0 "sleep 3 && tmux capture-pane -t controller -p -S - | tail -30" Enter

sleep 5

# Run the test
echo -e "\n${GREEN}[NETWORK]${NC} Starting 10-switch test network..."
echo -e "${YELLOW}[INFO]${NC} Controller running in: tmux attach -t controller"
echo -e "${YELLOW}[INFO]${NC} Monitoring in: tmux attach -t monitor"
echo ""

# Create a Python script that will run in the monitor session
cat > /tmp/demo_10sw_interactive.py << 'EOF'
#!/usr/bin/env python3
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def demo():
    print("\n🔨 Building 10-switch topology...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Create switches and hosts
    switches = {}
    hosts = {}
    for i in range(1, 11):
        switches[i] = net.addSwitch(f's{i}', protocols='OpenFlow13', dpid=str(i))
        hosts[i] = net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
        net.addLink(hosts[i], switches[i], port1=0, port2=1)
    
    # Create all links (avoiding port conflicts)
    links = [
        # Row 1
        (1, 2, 2, 2), (2, 3, 3, 3),
        # Row 2  
        (4, 5, 2, 2), (5, 6, 3, 2),
        # Row 3
        (7, 8, 2, 2), (8, 9, 3, 2),
        # Vertical
        (1, 4, 3, 3), (2, 5, 4, 4), (3, 6, 4, 3),
        (4, 7, 4, 3), (5, 8, 5, 4), (6, 9, 4, 3),
        # Diagonal
        (1, 5, 4, 6), (2, 4, 5, 5), (2, 6, 6, 5), (3, 5, 5, 7),
        (4, 8, 6, 5), (5, 7, 8, 4), (5, 9, 9, 4), (6, 8, 6, 6),
        # s10
        (8, 10, 10, 2)
    ]
    
    for s1, s2, p1, p2 in links:
        try:
            net.addLink(switches[s1], switches[s2], port1=p1, port2=p2)
        except Exception as e:
            print(f"Warning: Could not add link s{s1}-s{s2}: {e}")
    
    print("✅ Starting network...")
    net.start()
    time.sleep(5)
    
    print("\n" + "="*70)
    print(" INTERACTIVE DEMO - 10 SWITCH TOPOLOGY")
    print("="*70)
    print("\n📊 TOPOLOGY:")
    print("     s1 --- s2 --- s3")
    print("     |  X   |  X   |")
    print("     s4 --- s5 --- s6") 
    print("     |  X   |  X   |")
    print("     s7 --- s8 --- s9")
    print("            |")
    print("           s10")
    print("\n💡 DEMO COMMANDS:")
    print("  TEST CONNECTIVITY:")
    print("    h1 ping -c 3 h9        # Test corner to corner")
    print("    h1 ping -c 3 h10       # Test to isolated switch")
    print("")
    print("  SIMULATE FAILURES:")
    print("    link s1 s2 down        # Break horizontal link")
    print("    link s5 s8 down        # Break central vertical")
    print("    link s1 s5 down        # Break diagonal")
    print("")
    print("  MONITORING:")
    print("    links                  # Show all links")
    print("    sh ovs-ofctl dump-flows s1  # Show switch flows")
    print("")
    print("  RESTORATION:")
    print("    link s1 s2 up          # Restore link")
    print("")
    print("🔍 Watch the controller window for Dijkstra calculations!")
    print("="*70 + "\n")
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('warning')
    demo()
EOF

# Run the interactive demo
sudo python3 /tmp/demo_10sw_interactive.py

# Cleanup on exit
cleanup
echo -e "${GREEN}✅ Demo completed${NC}"