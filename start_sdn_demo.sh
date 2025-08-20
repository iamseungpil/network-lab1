#!/bin/bash

# SDN Dijkstra Demo Script
# Automatically starts controller and topology in tmux

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 SDN DIJKSTRA ROUTING DEMO${NC}"
echo -e "${BLUE}================================================${NC}"

# Check if tmux is available
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}Error: tmux is required but not installed${NC}"
    exit 1
fi

# Kill existing session if it exists
echo -e "${YELLOW}🧹 Cleaning up existing sessions...${NC}"
tmux kill-session -t sdn_demo 2>/dev/null || true
sudo mn -c 2>/dev/null || true
pkill -f ryu-manager 2>/dev/null || true
sleep 2

# Create new tmux session
echo -e "${YELLOW}📺 Creating tmux session 'sdn_demo'...${NC}"
tmux new-session -d -s sdn_demo

# Split window: top for controller, bottom for topology
tmux split-window -v -t sdn_demo

# Configure top pane for controller
tmux select-pane -t sdn_demo:0.0
tmux send-keys -t sdn_demo:0.0 "echo '=== CONTROLLER WINDOW (상단) ==='" Enter
tmux send-keys -t sdn_demo:0.0 "echo '🎛️  Starting Dijkstra Controller with detailed logging...'" Enter
tmux send-keys -t sdn_demo:0.0 "sleep 2" Enter

# Start controller in top pane
tmux send-keys -t sdn_demo:0.0 "ryu-manager --observe-links ryu-controller/main_controller_stp.py" Enter

# Configure bottom pane for topology
tmux select-pane -t sdn_demo:0.1
tmux send-keys -t sdn_demo:0.1 "echo '=== TOPOLOGY WINDOW (하단) ==='" Enter
tmux send-keys -t sdn_demo:0.1 "echo '⏳ Waiting for controller to start...'" Enter
tmux send-keys -t sdn_demo:0.1 "sleep 5" Enter

# Choose topology based on argument
if [ "$1" = "ring" ]; then
    TOPOLOGY="mininet/ring_topology.py"
    echo -e "${GREEN}🌐 Using 10-switch ring topology${NC}"
elif [ "$1" = "graph" ]; then
    TOPOLOGY="mininet/graph_topology.py"
    echo -e "${GREEN}📊 Using graph topology${NC}"
else
    TOPOLOGY="mininet/diamond_topology.py"
    echo -e "${GREEN}💎 Using simple diamond topology${NC}"
fi

# Start topology in bottom pane
tmux send-keys -t sdn_demo:0.1 "echo '🌐 Starting topology...'" Enter
tmux send-keys -t sdn_demo:0.1 "sudo python3 $TOPOLOGY" Enter

# Instructions
echo -e "${GREEN}✅ SDN Demo started successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 How to use:${NC}"
echo -e "   1. tmux attach -t sdn_demo    # 세션 연결"
echo -e "   2. Ctrl+b + ↑/↓             # 창 전환 (컨트롤러 ↔ 토폴로지)"
echo -e "   3. CLI commands:              # mininet CLI에서 실행"
echo -e "      h1 ping h4                 # 기본 연결 테스트"
echo -e "      h1 ping h3                 # 크로스 연결 테스트"
echo -e "      link s1 s2 down           # 링크 실패 시뮬레이션"
echo -e "      h1 ping h4                 # 재라우팅 확인"
echo -e "      link s1 s2 up             # 링크 복구"
echo -e "      pingall                    # 전체 연결 테스트"
echo -e "      exit                       # CLI 종료"
echo -e "   4. Ctrl+b + d                # tmux 세션에서 나가기"
echo ""
echo -e "${BLUE}📊 컨트롤러 로그에서 다음을 확인하세요:${NC}"
echo -e "   • 🔌 OpenFlow 스위치 연결"
echo -e "   • 🔗 LLDP 토폴로지 발견"
echo -e "   • 📦 패킷 처리 과정"
echo -e "   • 🛤️  Dijkstra 경로 계산"
echo -e "   • 💥 링크 실패 감지"
echo -e "   • ✅ 자동 재라우팅"
echo ""
echo -e "${GREEN}🎯 Ready! Connect to session:${NC} tmux attach -t sdn_demo"

# Optional: Auto-attach if requested
if [ "$2" = "attach" ]; then
    echo -e "${YELLOW}🔗 Auto-connecting to session...${NC}"
    sleep 3
    tmux attach -t sdn_demo
fi