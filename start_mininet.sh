#!/bin/bash

echo "=== Starting Mininet Topology ==="
echo

# 컨트롤러 연결 확인
echo "Checking if controllers are running..."

# Python을 사용한 포트 체크 함수
check_port() {
    python3 -c "import socket; sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); result = sock.connect_ex(('127.0.0.1', $1)); sock.close(); exit(result)"
}

if ! check_port 6700; then
    echo "❌ Primary Controller (port 6700) is not running!"
    echo "Please start controllers first in another window"
    exit 1
fi

if ! check_port 6800; then
    echo "❌ Secondary Controller (port 6800) is not running!"
    echo "Please start controllers first in another window"
    exit 1
fi

echo "✓ Primary Controller is running on port 6700"
echo "✓ Secondary Controller is running on port 6800"
echo

# 디렉토리 이동
cd "$(dirname "$0")"

echo "Starting Mininet topology..."
echo "This will start the network with 10 switches and 20 hosts"
echo
echo "NOTE: Gateway-based cross-controller communication enabled"
echo "MAC address-based domain routing: Primary(01-0a), Secondary(0b-14)"
echo "Example: h1 arp -s 10.0.0.11 00:00:00:00:00:0b"
echo

# Mininet 정리
mn -c > /dev/null 2>&1

# Mininet 토폴로지 실행 (interactive 모드)
python3 mininet/topology.py

echo
echo "Mininet session ended."
echo "Network has been cleaned up."
