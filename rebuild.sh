#!/bin/bash
# Quick rebuild script

echo "=== Quick Rebuild SDN Lab ==="
echo

CONTAINER_NAME="sdn-lab"
IMAGE_NAME="sdn-lab-image"

# Git Bash 경로 변환 문제 해결
export MSYS_NO_PATHCONV=1

# 1. 정리
echo "1. Cleaning up..."
docker stop $CONTAINER_NAME 2>/dev/null
docker rm $CONTAINER_NAME 2>/dev/null
docker rmi $IMAGE_NAME 2>/dev/null

# 2. 재빌드
echo
echo "2. Rebuilding Docker image..."
docker build --no-cache -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo
echo "✅ Rebuild complete!"
echo
echo "Now run: ./run-all.sh"
