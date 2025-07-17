#!/bin/bash
# SDN Lab screen 연결 스크립트

CONTAINER_NAME="sdn-lab"

# screen 세션이 실행 중인지 확인
if ! docker exec $CONTAINER_NAME screen -list | grep -q sdn-lab; then
    echo "SDN Lab is not running. Starting it..."
    docker exec $CONTAINER_NAME bash -c "cd /network-lab && screen -dmS sdn-lab ./start_sdn.sh"
    sleep 3
fi

echo "Connecting to SDN Lab screen session..."
echo
echo "=== Important Navigation Tips ==="
echo "• To interrupt a command in Mininet: Press Ctrl+C normally"
echo "• To detach from screen: Ctrl+A, D"
echo "• To scroll up/down: Ctrl+A, ESC (then use arrows, press ESC again to exit)"
echo "• To clear screen in Mininet: Press Ctrl+L"
echo
echo "Connecting..."
sleep 2

# exec을 사용하여 현재 프로세스를 docker exec로 교체
# 이렇게 하면 signal handling이 더 깔끔해짐
exec docker exec -it $CONTAINER_NAME screen -r sdn-lab
