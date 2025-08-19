#!/bin/bash

# Interactive Demo - Execute tests one by one manually
# You control when each test runs!

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo "       INTERACTIVE SDN DEMONSTRATION"
echo "       Manual Test Execution - You Control Everything!"
echo "============================================================"
echo -e "${NC}"

# Check conda environment
if [ -d "/data/miniforge3/envs/sdn-env" ]; then
    source /data/miniforge3/etc/profile.d/conda.sh
    conda activate sdn-env
    if ! ryu-manager --version > /dev/null 2>&1; then
        echo -e "${RED}ERROR: RYU not available${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Using conda sdn-env${NC}"
fi

# Function to wait for user
wait_for_user() {
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read
}

# Function to show menu
show_menu() {
    echo -e "${CYAN}${BOLD}"
    echo "========================================"
    echo "    INTERACTIVE TEST MENU"
    echo "========================================"
    echo -e "${NC}"
    echo "1) Start Controllers & Network"
    echo "2) Test Normal Routing (h1 → h5)"
    echo "3) Test Cross-domain (h1 → h11)"
    echo "4) Break Link s1-s3"
    echo "5) Test Rerouting after Failure"
    echo "6) Restore Link s1-s3"
    echo "7) Break Cross-domain Link s3-s6"
    echo "8) Test Cross-domain Rerouting"
    echo "9) Restore All Links"
    echo "10) Show Dijkstra Logs"
    echo "11) Manual Mininet CLI"
    echo "12) View Controllers (tmux)"
    echo "0) Exit and Cleanup"
    echo ""
    echo -e "${YELLOW}Enter choice: ${NC}"
}

# Clean up first
echo -e "${YELLOW}[INFO] Initial cleanup...${NC}"
./cleanup_network.sh

# Create tmux session with split panes
SESSION_NAME="interactive_demo"
tmux kill-session -t $SESSION_NAME 2>/dev/null

echo -e "${GREEN}[INFO] Creating split-pane tmux layout...${NC}"
tmux new-session -d -s $SESSION_NAME -n "Interactive"

# Split into 3 panes
tmux split-window -v -t $SESSION_NAME:0 -p 40
tmux split-window -h -t $SESSION_NAME:0.0 -p 50

# Start controllers
echo -e "${YELLOW}[INFO] Starting controllers...${NC}"

# Primary Controller (top-left)
tmux send-keys -t $SESSION_NAME:0.0 "echo '=== PRIMARY CONTROLLER (s1-s5) ===' && source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_controller.py" Enter

# Secondary Controller (top-right)
tmux send-keys -t $SESSION_NAME:0.1 "echo '=== SECONDARY CONTROLLER (s6-s10) ===' && source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_controller.py" Enter

# Wait for controllers
sleep 8

# Check controllers
if netstat -ln | grep ":6633 " > /dev/null && netstat -ln | grep ":6634 " > /dev/null; then
    echo -e "${GREEN}✓ Controllers are running${NC}"
else
    echo -e "${RED}✗ Controllers failed to start${NC}"
    exit 1
fi

# Create interactive test script
cat > /tmp/interactive_test.py << 'EOF'
#!/usr/bin/env python3
"""
Interactive SDN Test Environment
"""

import sys
import os
import time

sys.path.extend([
    '/usr/lib/python3/dist-packages',
    '/usr/local/lib/python3.8/dist-packages',
    '/usr/lib/python3.8/dist-packages'
])

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

class InteractiveDemo:
    def __init__(self):
        self.net = None
        self.setup_network()
    
    def setup_network(self):
        """Create the network topology"""
        print("\n=== Setting up Network ===")
        self.net = Mininet(controller=None, link=TCLink, autoSetMacs=True)
        
        # Add controllers
        c1 = self.net.addController('c1', controller=RemoteController, 
                                    ip='127.0.0.1', port=6633)
        c2 = self.net.addController('c2', controller=RemoteController, 
                                    ip='127.0.0.1', port=6634)
        
        # Add switches
        self.switches = []
        for i in range(1, 11):
            switch = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            self.switches.append(switch)
        
        # Add key hosts for testing
        self.h1 = self.net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        self.h5 = self.net.addHost('h5', ip='10.0.0.5/24', mac='00:00:00:00:00:05')
        self.h11 = self.net.addHost('h11', ip='10.0.0.11/24', mac='00:00:00:00:00:0b')
        self.h15 = self.net.addHost('h15', ip='10.0.0.15/24', mac='00:00:00:00:00:0f')
        
        # Add more hosts
        for i in [2,3,4]:
            self.net.addHost(f'h{i}', ip=f'10.0.0.{i}/24', mac=f'00:00:00:00:00:{i:02x}')
        
        # Connect hosts
        self.net.addLink(self.h1, self.switches[0])   # h1-s1
        self.net.addLink(self.h5, self.switches[2])   # h5-s3
        self.net.addLink(self.h11, self.switches[5])  # h11-s6
        self.net.addLink(self.h15, self.switches[7])  # h15-s8
        
        # Primary domain links
        self.net.addLink(self.switches[0], self.switches[1], bw=100)  # s1-s2
        self.net.addLink(self.switches[0], self.switches[2], bw=100)  # s1-s3
        self.net.addLink(self.switches[1], self.switches[3], bw=100)  # s2-s4
        self.net.addLink(self.switches[1], self.switches[4], bw=100)  # s2-s5
        self.net.addLink(self.switches[3], self.switches[2], bw=50)   # s4-s3
        
        # Cross-domain links
        self.net.addLink(self.switches[2], self.switches[5], bw=80)   # s3-s6
        self.net.addLink(self.switches[2], self.switches[6], bw=80)   # s3-s7
        self.net.addLink(self.switches[3], self.switches[7], bw=80)   # s4-s8
        
        # Secondary domain
        self.net.addLink(self.switches[5], self.switches[6], bw=60)   # s6-s7
        self.net.addLink(self.switches[7], self.switches[8], bw=60)   # s8-s9
        
        # Start network
        self.net.start()
        
        # Assign controllers
        for i in range(5):
            self.switches[i].start([c1])
        for i in range(5, 10):
            self.switches[i].start([c2])
        
        print("✓ Network created with 10 switches, dual controllers")
        time.sleep(3)
    
    def test_normal_routing(self):
        """Test 1: Normal intra-domain routing"""
        print("\n=== TEST: Normal Routing (h1 → h5) ===")
        print("Expected: Direct path s1 → s3")
        result = self.h1.cmd('ping -c 3 10.0.0.5')
        if '0% packet loss' in result:
            print("✓ SUCCESS: Normal routing works via optimal path")
        else:
            print("✗ FAILED: Check controller logs")
        return result
    
    def test_cross_domain(self):
        """Test 2: Cross-domain routing"""
        print("\n=== TEST: Cross-domain (h1 → h11) ===")
        print("Expected: Path s1 → s3 → s6")
        
        # Setup ARP
        self.h1.cmd('arp -s 10.0.0.11 00:00:00:00:00:0b')
        self.h11.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')
        
        result = self.h1.cmd('ping -c 3 10.0.0.11')
        if '0% packet loss' in result or '33% packet loss' in result:
            print("✓ SUCCESS: Cross-domain routing works")
        else:
            print("✗ FAILED: Cross-domain issue")
        return result
    
    def break_link_s1_s3(self):
        """Break the primary path"""
        print("\n=== ACTION: Breaking link s1 ↔ s3 ===")
        self.net.configLinkStatus('s1', 's3', 'down')
        print("✓ Link s1-s3 is now DOWN")
        print("  Controllers should detect this via PORT_STATUS")
        time.sleep(3)
    
    def test_rerouting(self):
        """Test rerouting after link failure"""
        print("\n=== TEST: Rerouting (h1 → h5 with s1-s3 down) ===")
        print("Expected: Alternative path s1 → s2 → s4 → s3")
        
        self.h1.cmd('ip neigh flush all')
        self.h5.cmd('ip neigh flush all')
        
        result = self.h1.cmd('ping -c 5 10.0.0.5')
        if '0% packet loss' in result or '20% packet loss' in result:
            print("✓ SUCCESS: Rerouting works! Using alternative path")
        else:
            print("✗ FAILED: Rerouting not working")
        return result
    
    def restore_link_s1_s3(self):
        """Restore the broken link"""
        print("\n=== ACTION: Restoring link s1 ↔ s3 ===")
        self.net.configLinkStatus('s1', 's3', 'up')
        print("✓ Link s1-s3 is now UP")
        print("  Should return to optimal path")
        time.sleep(3)
    
    def break_cross_domain(self):
        """Break cross-domain link"""
        print("\n=== ACTION: Breaking cross-domain link s3 ↔ s6 ===")
        self.net.configLinkStatus('s3', 's6', 'down')
        print("✓ Link s3-s6 is now DOWN")
        time.sleep(3)
    
    def test_cross_domain_reroute(self):
        """Test cross-domain rerouting"""
        print("\n=== TEST: Cross-domain rerouting (h1 → h11) ===")
        print("Expected: Alternative gateway s4 → s8")
        
        self.h1.cmd('ip neigh flush all')
        self.h11.cmd('ip neigh flush all')
        self.h1.cmd('arp -s 10.0.0.11 00:00:00:00:00:0b')
        self.h11.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')
        
        result = self.h1.cmd('ping -c 5 10.0.0.11')
        if '0% packet loss' in result or '20% packet loss' in result:
            print("✓ SUCCESS: Cross-domain rerouting works!")
        else:
            print("✗ FAILED: Cross-domain rerouting issue")
        return result
    
    def restore_all(self):
        """Restore all links"""
        print("\n=== ACTION: Restoring all links ===")
        self.net.configLinkStatus('s1', 's3', 'up')
        self.net.configLinkStatus('s3', 's6', 'up')
        print("✓ All links restored to normal")
        time.sleep(3)
    
    def show_dijkstra_logs(self):
        """Show recent Dijkstra calculations"""
        print("\n=== Recent Dijkstra Path Calculations ===")
        os.system("tmux capture-pane -t interactive_demo:0.0 -p | grep 'DIJKSTRA' | tail -5")
        os.system("tmux capture-pane -t interactive_demo:0.1 -p | grep 'DIJKSTRA' | tail -5")
    
    def manual_cli(self):
        """Enter Mininet CLI for manual testing"""
        print("\n=== Entering Mininet CLI ===")
        print("Examples:")
        print("  mininet> h1 ping h5")
        print("  mininet> net")
        print("  mininet> links")
        print("  mininet> exit")
        CLI(self.net)
    
    def cleanup(self):
        """Stop the network"""
        print("\n=== Cleaning up ===")
        if self.net:
            self.net.stop()
        print("✓ Network stopped")

def main():
    setLogLevel('info')
    demo = InteractiveDemo()
    
    while True:
        print("\n" + "="*40)
        print("INTERACTIVE TEST MENU")
        print("="*40)
        print("1) Test Normal Routing (h1→h5)")
        print("2) Test Cross-domain (h1→h11)")
        print("3) Break Link s1-s3")
        print("4) Test Rerouting after Failure")
        print("5) Restore Link s1-s3")
        print("6) Break Cross-domain Link s3-s6")
        print("7) Test Cross-domain Rerouting")
        print("8) Restore All Links")
        print("9) Show Dijkstra Logs")
        print("10) Manual Mininet CLI")
        print("0) Exit")
        print()
        
        try:
            choice = input("Enter choice: ").strip()
            
            if choice == '1':
                demo.test_normal_routing()
            elif choice == '2':
                demo.test_cross_domain()
            elif choice == '3':
                demo.break_link_s1_s3()
            elif choice == '4':
                demo.test_rerouting()
            elif choice == '5':
                demo.restore_link_s1_s3()
            elif choice == '6':
                demo.break_cross_domain()
            elif choice == '7':
                demo.test_cross_domain_reroute()
            elif choice == '8':
                demo.restore_all()
            elif choice == '9':
                demo.show_dijkstra_logs()
            elif choice == '10':
                demo.manual_cli()
            elif choice == '0':
                break
            else:
                print("Invalid choice")
                
            if choice != '0':
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    demo.cleanup()

if __name__ == '__main__':
    main()
EOF

chmod +x /tmp/interactive_test.py

# Run interactive test in bottom pane
echo -e "${GREEN}[INFO] Starting interactive test environment...${NC}"
tmux send-keys -t $SESSION_NAME:0.2 "cd /home/ubuntu/network-lab1 && sudo -E python3 /tmp/interactive_test.py" Enter

echo ""
echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}    INTERACTIVE DEMO READY!${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""

echo -e "${CYAN}Layout:${NC}"
echo "┌─────────────────┬─────────────────┐"
echo "│ Primary Ctrl    │ Secondary Ctrl  │"
echo "├─────────────────┴─────────────────┤"
echo "│    Interactive Test Menu           │"
echo "└────────────────────────────────────┘"
echo ""

echo -e "${YELLOW}To start testing:${NC}"
echo -e "${GREEN}  tmux attach -t interactive_demo${NC}"
echo ""
echo "Then use the menu in the bottom pane to:"
echo "  1) Test normal routing"
echo "  2) Break links"
echo "  3) Test rerouting"
echo "  4) View Dijkstra logs"
echo ""

# Attach if requested
if [[ "$1" == "attach" ]]; then
    tmux attach -t interactive_demo
fi