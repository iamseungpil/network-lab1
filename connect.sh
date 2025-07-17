#!/bin/bash
# tmux 세션 재연결 스크립트

CONTAINER_NAME="sdn-lab"

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== SDN Lab tmux 세션 재연결 ==="
echo

# 컨테이너 실행 확인
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}❌ SDN Lab 컨테이너가 실행되고 있지 않습니다.${NC}"
    echo "다음 명령어로 실행하세요:"
    echo "  ./run-all-tmux.sh"
    exit 1
fi

echo -e "${GREEN}✓ SDN Lab 컨테이너가 실행 중입니다.${NC}"

# tmux 세션 확인
if ! docker exec $CONTAINER_NAME tmux has-session -t sdn-lab 2>/dev/null; then
    echo -e "${YELLOW}⚠️  tmux 세션 'sdn-lab'이 없습니다.${NC}"
    echo "다음 명령어로 새로 시작하세요:"
    echo "  ./run-all-tmux.sh"
    exit 1
fi

echo -e "${GREEN}✓ tmux 세션 'sdn-lab'이 실행 중입니다.${NC}"
echo

# 세션 정보 표시
echo -e "${YELLOW}세션 정보:${NC}"
docker exec $CONTAINER_NAME tmux list-windows -t sdn-lab

echo
echo -e "${YELLOW}tmux 세션에 연결합니다...${NC}"
echo

# tmux 세션에 연결
docker exec -it $CONTAINER_NAME tmux attach-session -t sdn-lab

echo
echo -e "${GREEN}=== tmux 세션이 종료되었습니다 ===${NC}"
