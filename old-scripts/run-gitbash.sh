#!/bin/bash
# Alternative run script for Git Bash compatibility

echo "=== SDN Lab Launcher (Git Bash Compatible) ==="
echo

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 컨테이너 설정
CONTAINER_NAME="sdn-lab"
IMAGE_NAME="sdn-lab-image"

# Git Bash 경로 변환 문제 해결
export MSYS_NO_PATHCONV=1

# 1. 기존 컨테이너 정리
echo -e "${YELLOW}Step 1: Cleaning up existing containers...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true
echo

# 2. Docker 이미지 빌드
echo -e "${YELLOW}Step 2: Building Docker image...${NC}"
docker build -t $IMAGE_NAME .
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Docker image build failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker image built successfully${NC}"
echo

# 3. Docker 컨테이너 시작
echo -e "${YELLOW}Step 3: Starting Docker container...${NC}"
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

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Docker container start failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker container started${NC}"
echo

# 4. 컨테이너 초기화 대기
echo -e "${YELLOW}Step 4: Waiting for container initialization...${NC}"
echo "This may take up to 30 seconds..."
sleep 10

# systemd가 완전히 시작될 때까지 대기
for i in {1..20}; do
    if docker exec $CONTAINER_NAME systemctl is-system-running &>/dev/null; then
        echo -e "${GREEN}✓ Container is fully ready${NC}"
        break
    fi
    echo -n "."
    sleep 1
done
echo

# 5. SDN 환경 시작 옵션 제공
echo -e "${YELLOW}Container is ready!${NC}"
echo
echo "Choose how to start the SDN environment:"
echo
echo "Option 1: Automatic start (may not work in Git Bash)"
echo "  The script will try to start SDN automatically"
echo
echo "Option 2: Manual start (recommended for Git Bash)"
echo "  Connect to the container and start manually"
echo
read -p "Select option (1 or 2): " option

if [ "$option" = "1" ]; then
    echo
    echo "Attempting automatic start..."
    # Git Bash에서 winpty 사용 시도
    if command -v winpty &> /dev/null; then
        echo "Using winpty for Git Bash compatibility..."
        winpty docker exec -it $CONTAINER_NAME bash -c "cd /network-lab && ./docker-start-sdn.sh"
    else
        docker exec -it $CONTAINER_NAME bash -c "cd /network-lab && ./docker-start-sdn.sh"
    fi
else
    echo
    echo -e "${GREEN}=== Manual Start Instructions ===${NC}"
    echo
    echo "1. Open a new terminal/command prompt"
    echo
    echo "2. Connect to the container:"
    echo "   docker exec -it $CONTAINER_NAME bash"
    echo
    echo "   Or in Git Bash:"
    echo "   winpty docker exec -it $CONTAINER_NAME bash"
    echo
    echo "3. Inside the container, run:"
    echo "   cd /network-lab"
    echo "   ./docker-start-sdn.sh"
    echo
    echo "4. The Mininet CLI will start automatically"
    echo
    echo -e "${YELLOW}Container '$CONTAINER_NAME' is running and ready for connection.${NC}"
    echo
    echo "Additional commands:"
    echo "  View logs: docker exec -it $CONTAINER_NAME tail -f /tmp/sdn.log"
    echo "  Stop SDN: docker exec $CONTAINER_NAME /stop-sdn.sh"
    echo "  Stop container: docker stop $CONTAINER_NAME"
fi
