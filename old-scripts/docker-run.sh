#!/bin/bash
# Docker 컨테이너 빌드 및 실행 스크립트 (Git Bash용)

echo "=== SDN Lab Docker Environment Setup ==="
echo

# 컨테이너 이름
CONTAINER_NAME="sdn-lab"
IMAGE_NAME="sdn-lab-image"

# 기존 컨테이너 정리
echo "Cleaning up existing container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Docker 이미지 빌드
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "Error: Failed to build Docker image"
    exit 1
fi

echo "Docker image built successfully!"
echo

# Docker 컨테이너 실행
echo "Starting Docker container..."
# Git Bash 경로 변환 문제 해결
export MSYS_NO_PATHCONV=1

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
    echo "Error: Failed to start Docker container"
    exit 1
fi

echo "Docker container started successfully!"
echo

# 컨테이너가 완전히 시작될 때까지 대기
echo "Waiting for container to initialize..."
sleep 5

# 컨테이너 상태 확인
if docker ps | grep -q $CONTAINER_NAME; then
    echo "✓ Container is running"
    echo
    echo "=== Container Information ==="
    docker ps --filter name=$CONTAINER_NAME --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo
    echo "=== How to use ==="
    echo "1. Enter the container:"
    echo "   docker exec -it $CONTAINER_NAME bash"
    echo
    echo "2. Inside the container, run:"
    echo "   cd /network-lab"
    echo "   ./docker-start-sdn.sh"
    echo
    echo "3. To stop the container:"
    echo "   docker stop $CONTAINER_NAME"
    echo
    echo "4. To restart the container:"
    echo "   docker start $CONTAINER_NAME"
    echo "   docker exec -it $CONTAINER_NAME bash"
else
    echo "✗ Container failed to start"
    echo "Check logs with: docker logs $CONTAINER_NAME"
    exit 1
fi
