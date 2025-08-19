#!/bin/bash
# Real-time routing monitoring with split screen

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}    REAL-TIME DIJKSTRA ROUTING MONITOR${NC}"
echo -e "${CYAN}============================================================${NC}"

# Function to show usage
usage() {
    echo -e "\n${YELLOW}Usage:${NC}"
    echo -e "  $0 [start|stop|watch]"
    echo -e ""
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  start  - Start controller and monitoring"
    echo -e "  stop   - Stop all sessions"
    echo -e "  watch  - Attach to monitoring session"
    echo ""
    exit 1
}

# Function to start monitoring
start_monitoring() {
    # Clean up first
    tmux kill-session -t dijkstra 2>/dev/null || true
    sudo mn -c 2>/dev/null || true
    pkill -9 ryu-manager 2>/dev/null || true
    
    echo -e "${BLUE}[SETUP]${NC} Creating tmux session with 3 panes..."
    
    # Create main session
    tmux new-session -d -s dijkstra -n "SDN-Monitor"
    
    # Split into 3 panes
    # Top: Controller logs
    # Middle: Network testing
    # Bottom: Commands
    
    tmux split-window -t dijkstra -v -p 66   # Split vertically (top 34%, middle+bottom 66%)
    tmux split-window -t dijkstra:0.1 -v -p 50  # Split bottom into two (middle 33%, bottom 33%)
    
    # Pane 0 (top): Controller
    tmux send-keys -t dijkstra:0.0 "echo -e '${GREEN}===== CONTROLLER LOGS =====${NC}'" Enter
    tmux send-keys -t dijkstra:0.0 "source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-lab" Enter
    tmux send-keys -t dijkstra:0.0 "ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/dijkstra_controller_10sw.py 2>&1 | grep -E 'DIJKSTRA|PATH|REROUTING|PORT|FLOW'" Enter
    
    # Pane 1 (middle): Network monitor
    tmux send-keys -t dijkstra:0.1 "echo -e '${YELLOW}===== NETWORK TESTS =====${NC}'" Enter
    tmux send-keys -t dijkstra:0.1 "echo 'Waiting for network setup...'" Enter
    tmux send-keys -t dijkstra:0.1 "sleep 5" Enter
    tmux send-keys -t dijkstra:0.1 "sudo python3 /tmp/monitor_test.py" Enter
    
    # Pane 2 (bottom): Command input
    tmux send-keys -t dijkstra:0.2 "echo -e '${CYAN}===== COMMANDS =====${NC}'" Enter
    tmux send-keys -t dijkstra:0.2 "echo 'Ready for Mininet CLI commands...'" Enter
    
    # Create monitoring test script
    cat > /tmp/monitor_test.py << 'EOTEST'
#!/usr/bin/env python3
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def monitor_demo():
    print("\n🚀 Starting 10-switch network...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Quick setup
    switches = {}
    hosts = {}
    for i in range(1, 11):
        switches[i] = net.addSwitch(f's{i}', protocols='OpenFlow13', dpid=str(i))
        hosts[i] = net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
        net.addLink(hosts[i], switches[i], port1=0, port2=1)
    
    # Links
    links = [
        (1,2,2,2), (2,3,3,2), (4,5,3,2), (5,6,3,2), (7,8,2,2), (8,9,3,2),
        (1,4,4,3), (2,5,4,3), (3,6,4,3), (4,7,5,3), (5,8,5,3), (6,9,5,3),
        (1,5,5,4), (2,4,5,4), (2,6,6,4), (3,5,5,6), (4,8,6,4), (5,7,7,4),
        (5,9,8,4), (6,8,6,5), (8,10,10,2)
    ]
    for s1,s2,p1,p2 in links:
        net.addLink(switches[s1], switches[s2], port1=p1, port2=p2)
    
    net.start()
    time.sleep(3)
    
    print("\n✅ Network ready!")
    print("\n📝 Quick Tests:")
    print("  1. pingall           - Test all connectivity")
    print("  2. h1 ping h9        - Corner to corner")
    print("  3. link s5 s8 down   - Break central link")
    print("  4. h1 ping h9        - Test rerouting")
    print("  5. link s5 s8 up     - Restore link")
    print("\n")
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('warning')
    monitor_demo()
EOTEST
    
    echo -e "\n${GREEN}✅ Monitoring session started!${NC}"
    echo -e "${YELLOW}Attaching to tmux session...${NC}\n"
    
    # Attach to session
    tmux attach -t dijkstra
}

# Function to stop monitoring
stop_monitoring() {
    echo -e "${RED}[STOP]${NC} Stopping all sessions..."
    tmux kill-session -t dijkstra 2>/dev/null || true
    sudo mn -c 2>/dev/null || true
    pkill -9 ryu-manager 2>/dev/null || true
    rm -f /tmp/monitor_test.py 2>/dev/null
    echo -e "${GREEN}✅ All sessions stopped${NC}"
}

# Function to watch existing session
watch_session() {
    if tmux has-session -t dijkstra 2>/dev/null; then
        echo -e "${GREEN}[ATTACH]${NC} Attaching to monitoring session..."
        tmux attach -t dijkstra
    else
        echo -e "${RED}[ERROR]${NC} No monitoring session found. Run '$0 start' first."
        exit 1
    fi
}

# Main logic
case "${1:-}" in
    start)
        start_monitoring
        ;;
    stop)
        stop_monitoring
        ;;
    watch)
        watch_session
        ;;
    *)
        usage
        ;;
esac