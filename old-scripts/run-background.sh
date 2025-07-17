#!/bin/bash
# 백그라운드 실행 스크립트 - SDN 실험을 백그라운드에서 시작

echo "=== SDN Lab Background Launcher ==="
echo

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 컨테이너 설정
CONTAINER_NAME="sdn-lab"
IMAGE_NAME="sdn-lab-image"

# 함수: 성공/실패 메시지 출력
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

# 1. 컨테이너 상태 확인
echo -e "${YELLOW}Checking container status...${NC}"
if docker ps --filter name=$CONTAINER_NAME --format "{{.Names}}" | grep -q $CONTAINER_NAME; then
    echo -e "${GREEN}Container is already running${NC}"
else
    # 컨테이너가 없으면 생성
    echo -e "${YELLOW}Container not found. Creating new container...${NC}"
    
    # 이미지 확인
    if ! docker images | grep -q $IMAGE_NAME; then
        echo -e "${YELLOW}Building Docker image...${NC}"
        docker build -t $IMAGE_NAME .
        print_status $? "Docker image built"
    fi
    
    # Git Bash 경로 변환 문제 해결
    export MSYS_NO_PATHCONV=1
    
    # 컨테이너 시작
    docker run -d \
        --name $CONTAINER_NAME \
        --privileged=true \
        --cap-add=ALL \
        -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
        --cgroupns=host \
        -p 6700:6700 \
        -p 6800:6800 \
        $IMAGE_NAME \
        /sbin/init
    print_status $? "Container started"
    
    echo "Waiting for initialization..."
    sleep 5
fi
echo

# 2. SDN 환경 시작 (백그라운드)
echo -e "${YELLOW}Starting SDN environment in background...${NC}"
docker exec -d $CONTAINER_NAME bash -c "cd /network-lab && nohup ./docker-start-sdn.sh > /tmp/sdn.log 2>&1 &"
print_status $? "SDN environment started in background"
echo

# 3. 접속 정보 제공
echo -e "${BLUE}=== Connection Information ===${NC}"
echo -e "${GREEN}The SDN environment is starting in the background.${NC}"
echo
echo "To connect to Mininet CLI:"
echo -e "  ${YELLOW}docker exec -it $CONTAINER_NAME bash${NC}"
echo -e "  ${YELLOW}cd /network-lab${NC}"
echo -e "  ${YELLOW}screen -r mininet${NC}  (if using screen)"
echo
echo "To view logs:"
echo -e "  ${YELLOW}docker exec -it $CONTAINER_NAME tail -f /tmp/sdn.log${NC}"
echo
echo "To check controller status:"
echo -e "  ${YELLOW}docker exec $CONTAINER_NAME ps aux | grep ryu-manager${NC}"
echo
echo "To stop everything:"
echo -e "  ${YELLOW}docker stop $CONTAINER_NAME${NC}"
echo
echo -e "${GREEN}Controllers are accessible at:${NC}"
echo "  Primary Controller: localhost:6700"
echo "  Secondary Controller: localhost:6800"
