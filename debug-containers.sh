#!/bin/bash

echo "=== Debug SDN Containers ==="

# 컨테이너 목록 확인 (권한 문제 시 sudo 사용)
echo "1. Checking container status..."
if docker ps 2>/dev/null; then
    echo "Docker access OK"
else
    echo "Using sudo for docker commands..."
    DOCKER_CMD="sudo docker"
fi

# 기본 명령어 설정
DOCKER_CMD=${DOCKER_CMD:-docker}

echo ""
echo "2. All containers:"
$DOCKER_CMD ps -a

echo ""
echo "3. Container logs:"
echo "--- Controller1 logs ---"
$DOCKER_CMD logs sdn-controller1 2>&1 | tail -20

echo ""
echo "--- Controller2 logs ---"  
$DOCKER_CMD logs sdn-controller2 2>&1 | tail -20

echo ""
echo "--- CLI logs ---"
$DOCKER_CMD logs sdn-cli 2>&1 | tail -20

echo ""
echo "--- Mininet logs ---"
$DOCKER_CMD logs sdn-mininet 2>&1 | tail -20

echo ""
echo "4. Network status:"
$DOCKER_CMD network ls | grep compose

echo ""
echo "5. Compose status:"
cd "$(dirname "$0")/docker/compose"
$DOCKER_CMD compose ps