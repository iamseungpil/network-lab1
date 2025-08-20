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

# Conda environment setup
echo -e "${YELLOW}🐍 Setting up conda environment...${NC}"

# Initialize conda for this script - dynamic detection
CONDA_BASE=""

# Method 1: Use conda info if conda is already in PATH
if command -v conda &> /dev/null; then
    CONDA_BASE=$(conda info --base 2>/dev/null)
fi

# Method 2: Check CONDA_PREFIX if we're in a conda environment
if [ -z "$CONDA_BASE" ] && [ -n "$CONDA_PREFIX" ]; then
    # Extract base path from CONDA_PREFIX (remove /envs/env_name part)
    CONDA_BASE=$(echo "$CONDA_PREFIX" | sed 's|/envs/.*||')
fi

# Method 3: Search common conda installation locations
if [ -z "$CONDA_BASE" ]; then
    for path in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/miniforge3" "/opt/miniconda3" "/opt/anaconda3" "/opt/miniforge3" "/data/miniforge3" "/usr/local/miniconda3" "/usr/local/anaconda3"; do
        if [ -f "$path/etc/profile.d/conda.sh" ]; then
            CONDA_BASE="$path"
            break
        fi
    done
fi

# Try to source conda.sh if we found a conda installation
if [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    echo -e "${GREEN}✅ Found conda at: $CONDA_BASE${NC}"
else
    echo -e "${RED}Error: Conda not found! Please install conda first${NC}"
    echo -e "${YELLOW}Searched locations:${NC}"
    echo -e "  - conda command in PATH"
    echo -e "  - CONDA_PREFIX environment variable"
    echo -e "  - Common installation paths (\$HOME/miniconda3, \$HOME/anaconda3, etc.)"
    exit 1
fi

# Check if sdn-lab environment exists
ENV_NAME="sdn-lab"
if conda env list | grep -q "^${ENV_NAME} "; then
    echo -e "${GREEN}✅ Conda environment '${ENV_NAME}' already exists${NC}"
else
    echo -e "${YELLOW}🔧 Creating conda environment '${ENV_NAME}'...${NC}"
    conda create -n ${ENV_NAME} python=3.10 -y
    echo -e "${GREEN}✅ Environment '${ENV_NAME}' created${NC}"
fi

# Activate environment
echo -e "${YELLOW}🔄 Activating conda environment '${ENV_NAME}'...${NC}"
conda activate ${ENV_NAME}

# Check and install requirements
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📦 Installing/updating requirements...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Requirements installed${NC}"
else
    echo -e "${YELLOW}⚠️  No requirements.txt found, installing basic packages...${NC}"
    pip install ryu networkx
    echo -e "${GREEN}✅ Basic packages installed${NC}"
fi

# Verify installation
echo -e "${YELLOW}🔍 Verifying installation...${NC}"
if python -c "import ryu, networkx; print('✅ All packages available')" 2>/dev/null; then
    echo -e "${GREEN}✅ Environment setup complete!${NC}"
else
    echo -e "${RED}❌ Package verification failed${NC}"
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

# Start controller in top pane (with conda environment)
tmux send-keys -t sdn_demo:0.0 "source $CONDA_BASE/etc/profile.d/conda.sh && conda activate sdn-lab && ryu-manager --observe-links ryu-controller/main_controller_stp.py" Enter

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

# Start topology in bottom pane (with conda environment)
tmux send-keys -t sdn_demo:0.1 "echo '🌐 Starting topology...'" Enter
tmux send-keys -t sdn_demo:0.1 "source $CONDA_BASE/etc/profile.d/conda.sh && conda activate sdn-lab && sudo -E python3 $TOPOLOGY" Enter

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