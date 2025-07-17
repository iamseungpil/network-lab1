#!/bin/bash
# SDN Lab 통합 실행 스크립트 (개선된 tmux 버전)

echo "=== SDN Lab All-in-One Launcher (tmux) ==="
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

# 6. tmux 세션 설정
echo -e "${YELLOW}Step 6: Setting up tmux session...${NC}"

# 기존 tmux 세션 종료
docker exec $CONTAINER_NAME tmux kill-session -t sdn-lab 2>/dev/null || true

# 새 tmux 세션 생성 (컨트롤러 윈도우)
echo "Creating tmux session with controllers window..."
docker exec $CONTAINER_NAME bash -c "cd /network-lab && tmux new-session -d -s sdn-lab -n controllers"

# 컨트롤러 시작
echo "Starting controllers in tmux..."
docker exec $CONTAINER_NAME tmux send-keys -t sdn-lab:controllers './start_controllers.sh' Enter

# Mininet 윈도우 생성
echo "Creating Mininet window..."
docker exec $CONTAINER_NAME tmux new-window -t sdn-lab -n mininet

# 컨트롤러 시작 대기
echo "Waiting for controllers to initialize..."
sleep 8

# Mininet 시작 준비 메시지 전송
docker exec $CONTAINER_NAME tmux send-keys -t sdn-lab:mininet 'echo "=== Mininet Window ==="' Enter
docker exec $CONTAINER_NAME tmux send-keys -t sdn-lab:mininet 'echo "Controllers should be running in the other window."' Enter
docker exec $CONTAINER_NAME tmux send-keys -t sdn-lab:mininet 'echo "Starting Mininet in 3 seconds..."' Enter
docker exec $CONTAINER_NAME tmux send-keys -t sdn-lab:mininet 'sleep 3' Enter
docker exec $CONTAINER_NAME tmux send-keys -t sdn-lab:mininet './start_mininet.sh' Enter

# Mininet 윈도우로 전환
docker exec $CONTAINER_NAME tmux select-window -t sdn-lab:mininet

sleep 3
echo -e "${GREEN}✓ SDN Lab is running in tmux with dual windows${NC}"
echo

# 7. SDN Lab 연결
echo -e "${YELLOW}Connecting to SDN Lab tmux session...${NC}"
echo
echo -e "${GREEN}=== SDN Lab Interactive Session (tmux) ===${NC}"
echo
echo -e "${BLUE}Session Layout:${NC}"
echo "- ${YELLOW}Window 0 (controllers)${NC}: RYU Controllers running"
echo "- ${YELLOW}Window 1 (mininet)${NC}: Mininet CLI (current)"
echo
echo -e "${BLUE}Navigation:${NC}"
echo "- ${YELLOW}Ctrl+B, 0${NC}: Switch to controllers window"
echo "- ${YELLOW}Ctrl+B, 1${NC}: Switch to mininet window"
echo "- ${YELLOW}Ctrl+B, D${NC}: Detach from tmux (keeps session running)"
echo "- ${YELLOW}Ctrl+B, [${NC}: Scroll mode (q to exit)"
echo "- ${YELLOW}Ctrl+C${NC}: Works normally in Mininet CLI"
echo "- ${YELLOW}exit${NC}: Stop Mininet and close session"
echo
echo "Connecting in 3 seconds..."
sleep 3

# tmux 세션에 연결 (Mininet 윈도우로)
docker exec -it $CONTAINER_NAME tmux attach-session -t sdn-lab

echo
echo -e "${GREEN}=== SDN Lab Session Ended ===${NC}"
echo
echo "Available commands:"
echo "- ${YELLOW}./run-all-tmux.sh${NC}: Reconnect to session"
echo "- ${YELLOW}docker exec -it $CONTAINER_NAME tmux attach-session -t sdn-lab${NC}: Direct reconnect"
echo "- ${YELLOW}docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME${NC}: Stop container"
