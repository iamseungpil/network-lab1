#!/bin/bash

echo "=== Starting SDN Controllers Only ==="
echo

# Python 환경 확인
echo "Python environment check:"
echo "  Python version: $(python3 --version)"
echo "  Python path: $(which python3)"
echo

# RYU 설치 확인
if ! command -v ryu-manager &> /dev/null; then
    echo "❌ RYU controller not found"
    echo "Please install RYU:"
    echo "  pip install setuptools==67.6.1"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo "✅ RYU controller $(ryu-manager --version | head -1)"
echo

# 기존 프로세스 정리
echo "Cleaning up existing processes..."
pkill -f ryu-manager > /dev/null 2>&1
mn -c > /dev/null 2>&1

# 디렉토리 이동
cd "$(dirname "$0")"

echo "Starting controllers..."

# Gateway Primary Controller 시작 (포트 6700)
echo "Starting Gateway Primary Controller (s1-s5) on port 6700..."
ryu-manager ryu-controller/gateway_primary.py --ofp-tcp-listen-port 6700 &
PRIMARY_PID=$!
sleep 2

# Gateway Secondary Controller 시작 (포트 6800)
echo "Starting Gateway Secondary Controller (s6-s10) on port 6800..."
ryu-manager ryu-controller/gateway_secondary.py --ofp-tcp-listen-port 6800 &
SECONDARY_PID=$!
sleep 2

echo "Controllers started successfully!"
echo "Primary Controller PID: $PRIMARY_PID"
echo "Secondary Controller PID: $SECONDARY_PID"
echo

# 컨트롤러 연결 확인
echo "Checking controller status..."
if ps -p $PRIMARY_PID > /dev/null; then
    echo "✓ Primary Controller is running (port 6700)"
else
    echo "✗ Primary Controller failed to start"
    exit 1
fi

if ps -p $SECONDARY_PID > /dev/null; then
    echo "✓ Secondary Controller is running (port 6800)"
else
    echo "✗ Secondary Controller failed to start"
    exit 1
fi

echo
echo "Controllers are ready!"
echo "Primary Controller: 127.0.0.1:6700 (handles s1-s5)"
echo "Secondary Controller: 127.0.0.1:6800 (handles s6-s10)"
echo
echo "Gateway-based cross-controller communication enabled"
echo "MAC address-based domain routing: Primary(01-0a), Secondary(0b-14)"
echo
echo "Controllers will continue running until stopped with: pkill -f ryu-manager"
echo

# 컨트롤러 로그 모니터링
echo "=== Controller Logs (Press Ctrl+C to detach) ==="
tail -f /dev/null &
wait
