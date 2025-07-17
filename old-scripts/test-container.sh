#!/bin/bash
# Test script to verify container setup

CONTAINER_NAME="sdn-lab"

echo "=== Testing Container Setup ==="
echo

# 1. 파일 확인
echo "1. Checking script files:"
echo "   In /network-lab:"
docker exec $CONTAINER_NAME ls -la /network-lab/*.sh 2>&1 || echo "Failed to list /network-lab"
echo
echo "   In root:"
docker exec $CONTAINER_NAME ls -la /*.sh 2>&1 || echo "Failed to list root"
echo

# 2. Python 및 RYU 확인
echo "2. Checking Python and RYU:"
docker exec $CONTAINER_NAME python3 --version
docker exec $CONTAINER_NAME which ryu-manager
docker exec $CONTAINER_NAME ryu-manager --version 2>&1 | head -1
echo

# 3. OVS 확인
echo "3. Checking Open vSwitch:"
docker exec $CONTAINER_NAME which ovs-vsctl
echo

# 4. 스크립트 내용 확인
echo "4. Checking if docker-start-sdn.sh exists and is executable:"
docker exec $CONTAINER_NAME test -x /docker-start-sdn.sh && echo "✓ /docker-start-sdn.sh is executable" || echo "✗ /docker-start-sdn.sh not found or not executable"
docker exec $CONTAINER_NAME test -x /network-lab/docker-start-sdn.sh && echo "✓ /network-lab/docker-start-sdn.sh is executable" || echo "✗ /network-lab/docker-start-sdn.sh not found or not executable"
echo

echo "=== Rebuild Instructions ==="
echo "If files are missing, rebuild the container:"
echo "  docker stop $CONTAINER_NAME"
echo "  docker rm $CONTAINER_NAME"
echo "  docker build --no-cache -t sdn-lab-image ."
echo "  ./run-all.sh"
