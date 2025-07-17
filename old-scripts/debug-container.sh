#!/bin/bash
# Debug script to check container status

CONTAINER_NAME="sdn-lab"

echo "=== Container Debugging ==="
echo

# 1. 컨테이너 상태 확인
echo "1. Container status:"
docker ps --filter name=$CONTAINER_NAME --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
echo

# 2. 컨테이너 로그 확인
echo "2. Recent container logs:"
docker logs --tail 20 $CONTAINER_NAME
echo

# 3. systemd 상태 확인
echo "3. Systemd status:"
docker exec $CONTAINER_NAME systemctl is-system-running 2>&1 || echo "Systemd not ready"
echo

# 4. 네트워크 설정 확인
echo "4. Network configuration:"
docker exec $CONTAINER_NAME ip addr show 2>&1 || echo "Network not ready"
echo

# 5. OVS 상태 확인
echo "5. Open vSwitch status:"
docker exec $CONTAINER_NAME service openvswitch-switch status 2>&1 || echo "OVS not ready"
echo

# 6. 파일 확인
echo "6. Checking files:"
docker exec $CONTAINER_NAME ls -la /network-lab/ 2>&1 || echo "Files not accessible"
echo

echo "=== Manual connection instructions ==="
echo "If the container is running, you can connect manually:"
echo "  docker exec -it $CONTAINER_NAME bash"
echo "  cd /network-lab"
echo "  ./docker-start-sdn.sh"
echo
echo "Or if using Git Bash, try with winpty:"
echo "  winpty docker exec -it $CONTAINER_NAME bash"
