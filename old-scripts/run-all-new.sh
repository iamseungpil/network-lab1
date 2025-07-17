#!/bin/bash
# SDN Lab 통합 실행 스크립트

echo "=== SDN Lab All-in-One Launcher ==="
echo

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 컨테이너 설정
CONTAINER_NAME="sdn-lab"
IMAGE_NAME="sdn-lab-image"

# Git Bash 경로 변환 문제 해결
export MSYS_NO_PATHCONV=1

# 함수: 성공/실패 메시지 출력
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

# 1. 기존 컨테이너 정리
echo -e "${YELLOW}Step 1: Cleaning up existing containers...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true
echo

# 2. Docker 이미지 빌드
echo -e "${YELLOW}Step 2: Building Docker image...${NC}"
docker build -t $IMAGE_NAME .
print_status $? "Docker image built successfully"
echo

# 3. Docker 컨테이너 시작 (systemd 지원)
echo -e "${YELLOW}Step 3: Starting Docker container with systemd...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    --privileged \
    --cgroupns=host \
    -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
    -p 6700:6700 \
    -p 6800:6800 \
    $IMAGE_NAME \
    /sbin/init

print_status $? "Docker container started"
echo

# 4. systemd 초기화 대기
echo -e "${YELLOW}Step 4: Waiting for systemd initialization...${NC}"
echo "This may take up to 30 seconds..."

# systemd가 완전히 시작될 때까지 대기
for i in {1..30}; do
    if docker exec $CONTAINER_NAME systemctl is-system-running &>/dev/null; then
        print_status 0 "Systemd is ready"
        break
    elif [ $i -eq 30 ]; then
        echo -e "${YELLOW}Systemd status:${NC}"
        docker exec $CONTAINER_NAME systemctl is-system-running || true
        echo -e "${YELLOW}Continuing anyway...${NC}"
    else
        echo -n "."
        sleep 1
    fi
done
echo

# 5. OVS 서비스 시작 및 확인
echo -e "${YELLOW}Step 5: Starting OVS services...${NC}"

# OVS vswitchd가 실행 중인지 확인하고 없으면 시작
docker exec $CONTAINER_NAME bash -c '
if ! pgrep -f ovs-vswitchd > /dev/null; then
    echo "Starting ovs-vswitchd..."
    ovs-vswitchd --pidfile --detach --log-file
    sleep 2
fi
'

# OVS 상태 확인
echo "Checking OVS status..."
docker exec $CONTAINER_NAME ovs-vsctl show
echo

# 6. SDN Lab 서비스 시작
echo -e "${YELLOW}Step 6: Starting SDN Lab service...${NC}"
docker exec $CONTAINER_NAME systemctl restart sdn-lab
sleep 5

# 서비스 상태 확인
echo "Service status:"
echo -n "SDN Lab: "
docker exec $CONTAINER_NAME systemctl is-active sdn-lab || echo "inactive"
echo

# 7. SDN Lab 연결
echo -e "${YELLOW}Step 7: Connecting to SDN Lab...${NC}"
echo
echo -e "${GREEN}The SDN Lab environment is ready!${NC}"
echo
echo "You will be connected to the screen session with:"
echo "- RYU Controller logs"
echo "- Mininet CLI"
echo
echo "Screen navigation:"
echo "- Detach: Ctrl+A, D"
echo "- Reconnect later: ./run-all.sh"
echo
echo "Connecting in 3 seconds..."
sleep 3

# SDN Lab screen 세션에 연결
docker exec -it $CONTAINER_NAME screen -r sdn-lab

echo
echo -e "${GREEN}=== SDN Lab Session Ended ===${NC}"
echo "To reconnect: ./run-all.sh"
echo "To stop container: docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME"
