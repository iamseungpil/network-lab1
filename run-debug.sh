#!/bin/bash
# SDN Lab 디버그 실행 스크립트 (컨트롤러 로그 포함)

echo "=== SDN Lab Debug Launcher (with Controller Logs) ==="
echo

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 컨테이너가 이미 실행 중인지 확인
if docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}Container already running. Connecting to SDN Lab...${NC}"
else
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

    # 4. 초기화 대기
    echo -e "${YELLOW}Step 4: Waiting for container initialization...${NC}"
    echo "Initializing services..."
    sleep 10
    print_status 0 "Container is ready"
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
fi

# 6. SDN Lab 실행
echo -e "${YELLOW}Step 6: Starting SDN Lab with full logs...${NC}"
echo
echo -e "${GREEN}=== SDN Lab Interactive Session ===${NC}"
echo
echo -e "${BLUE}You will see:${NC}"
echo "- ${YELLOW}RYU Controller logs${NC} in real-time"
echo "- ${YELLOW}OpenFlow messages${NC} for debugging"
echo "- ${YELLOW}Mininet CLI${NC} for network testing"
echo
echo -e "${BLUE}Key Information:${NC}"
echo "- Primary Controller: port 6700 (handles s1-s5)"
echo "- Secondary Controller: port 6800 (handles s6-s10)"
echo "- Gateway-based cross-controller communication"
echo
echo -e "${BLUE}Testing commands:${NC}"
echo "- ${YELLOW}h1 ping h2${NC}: Test same-controller communication"
echo "- ${YELLOW}h1 ping h11${NC}: Test cross-controller communication"
echo "- ${YELLOW}pingall${NC}: Test all connections"
echo "- ${YELLOW}exit${NC}: Stop Mininet and controllers"
echo
echo "Starting in 3 seconds..."
sleep 3

# SDN Lab 실행 (로그 포함)
docker exec -it $CONTAINER_NAME bash -c "cd /network-lab && ./start_sdn.sh"

echo
echo -e "${GREEN}=== SDN Lab Session Ended ===${NC}"
echo
echo "Available commands:"
echo "- ${YELLOW}./run-debug.sh${NC}: Restart with full logs"
echo "- ${YELLOW}./run.sh${NC}: Use tmux version (separate windows)"
echo "- ${YELLOW}docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME${NC}: Stop container"
