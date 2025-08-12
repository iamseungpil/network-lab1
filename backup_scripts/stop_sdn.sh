#!/bin/bash
# SDN 네트워크 정리 스크립트

echo "============================================"
echo "    Stopping Dijkstra SDN Network"
echo "============================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. tmux 세션 종료
echo -e "${YELLOW}[1/5] Stopping tmux sessions...${NC}"
tmux kill-session -t sdn_dijkstra 2>/dev/null
tmux kill-session -t dijkstra 2>/dev/null
tmux kill-session -t sdn 2>/dev/null
echo -e "${GREEN}✓ tmux sessions terminated${NC}"

# 2. Mininet 정리
echo -e "${YELLOW}[2/5] Cleaning up Mininet...${NC}"
sudo mn -c > /dev/null 2>&1
echo -e "${GREEN}✓ Mininet cleaned${NC}"

# 3. 컨트롤러 프로세스 종료
echo -e "${YELLOW}[3/5] Stopping controller processes...${NC}"
pkill -f "ryu-manager.*dijkstra_primary" > /dev/null 2>&1
pkill -f "ryu-manager.*dijkstra_secondary" > /dev/null 2>&1
pkill -f "ryu-manager.*gateway_primary" > /dev/null 2>&1
pkill -f "ryu-manager.*gateway_secondary" > /dev/null 2>&1
pkill -f ryu-manager > /dev/null 2>&1
sudo pkill -f "topology.py" > /dev/null 2>&1
echo -e "${GREEN}✓ Controllers stopped${NC}"

# 4. OVS 정리
echo -e "${YELLOW}[4/5] Cleaning up Open vSwitch...${NC}"
sudo ovs-vsctl list-br 2>/dev/null | while read bridge; do
    sudo ovs-vsctl del-br $bridge 2>/dev/null
done
echo -e "${GREEN}✓ OVS bridges removed${NC}"

# 5. 대기
echo -e "${YELLOW}[5/5] Final cleanup...${NC}"
sleep 3

# 최종 상태 확인
echo ""
echo -e "${YELLOW}=== Status Check ===${NC}"

# 컨트롤러 포트 확인
if netstat -tlnp 2>/dev/null | grep -E "(6633|6634)" > /dev/null; then
    echo -e "${RED}⚠  Some ports may still be in use${NC}"
    netstat -tlnp 2>/dev/null | grep -E "(6633|6634)"
else
    echo -e "${GREEN}✓ Controller ports (6633, 6634) are free${NC}"
fi

# RYU 프로세스 확인
if ps aux | grep -v grep | grep "ryu-manager" > /dev/null; then
    echo -e "${RED}⚠  Some RYU processes may still be running${NC}"
    echo "  Try: sudo pkill -9 -f ryu-manager"
else
    echo -e "${GREEN}✓ No RYU controller processes running${NC}"
fi

# Mininet 프로세스 확인
if ps aux | grep -v grep | grep -E "mininet" > /dev/null; then
    echo -e "${RED}⚠  Some Mininet processes may still be running${NC}"
    echo "  Try: sudo mn -c"
else
    echo -e "${GREEN}✓ No Mininet processes running${NC}"
fi

echo ""
echo -e "${GREEN}============================================"
echo "    SDN Network Stopped Successfully"
echo "============================================${NC}"
echo ""
echo "To restart the network, run:"
echo -e "  ${GREEN}./start_sdn_dijkstra.sh${NC}"
echo ""