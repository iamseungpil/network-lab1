#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Simple SDN Lab Launcher ==="
echo

CONTAINER_NAME="sdn-lab"
IMAGE_NAME="sdn-lab-image"

# Git Bash 경로 변환 문제 해결
export MSYS_NO_PATHCONV=1

# 1. 기존 컨테이너 정리
echo -e "${YELLOW}Cleaning up...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null
docker rm $CONTAINER_NAME 2>/dev/null

# 2. 이미지 빌드
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

# 3. 컨테이너 실행 옵션
echo
echo -e "${GREEN}Docker image ready!${NC}"
echo
echo "Choose an option:"
echo "1) Run SDN environment automatically"
echo "2) Start container and connect manually"
echo "3) Exit"
echo
read -p "Select (1-3): " choice

case $choice in
    1)
        echo -e "${YELLOW}Starting SDN environment...${NC}"
        docker run -it --rm \
            --name $CONTAINER_NAME \
            --privileged=true \
            --cap-add=ALL \
            -p 6700:6700 \
            -p 6800:6800 \
            $IMAGE_NAME
        ;;
    2)
        echo -e "${YELLOW}Starting container...${NC}"
        docker run -d \
            --name $CONTAINER_NAME \
            --privileged=true \
            --cap-add=ALL \
            -p 6700:6700 \
            -p 6800:6800 \
            $IMAGE_NAME \
            tail -f /dev/null
        
        echo -e "${GREEN}Container started!${NC}"
        echo
        echo "To connect:"
        echo "  docker exec -it $CONTAINER_NAME bash"
        echo
        echo "Inside container:"
        echo "  /docker-start-sdn.sh"
        ;;
    3)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac
