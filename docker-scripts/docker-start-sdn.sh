#!/bin/bash

# 사용법 출력 함수
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -b, --background    Run Mininet in screen session (detached)"
    echo "  -h, --help          Show this help message"
    echo "  -l, --log FILE      Log output to file (default: /tmp/sdn.log)"
    exit 1
}

# 옵션 파싱
BACKGROUND=false
LOGFILE="/tmp/sdn.log"

while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--background)
            BACKGROUND=true
            shift
            ;;
        -l|--log)
            LOGFILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

echo "=== Starting SDN Environment in Docker ==="
echo

# OVS 초기화
echo "Initializing Open vSwitch..."
/init-ovs.sh

# 환경 확인
echo "Python version: $(python3 --version)"
echo

# RYU 설치 확인
if ! command -v ryu-manager &> /dev/null; then
    echo "❌ RYU controller not found"
    exit 1
fi

echo "✅ RYU controller $(ryu-manager --version | head -1)"
echo

# 기존 프로세스 정리
echo "Cleaning up existing processes..."
pkill -f ryu-manager > /dev/null 2>&1 || true
mn -c > /dev/null 2>&1 || true
screen -S mininet -X quit > /dev/null 2>&1 || true

# 디렉토리 이동
cd /network-lab

echo "Starting controllers..."

# 로그 파일 초기화
echo "[$(date)] Starting SDN Environment" > $LOGFILE

# Gateway Primary Controller 시작 (포트 6700)
echo "Starting Gateway Primary Controller (s1-s5) on port 6700..."
ryu-manager ryu-controller/gateway_primary.py --ofp-tcp-listen-port 6700 >> $LOGFILE 2>&1 &
PRIMARY_PID=$!
sleep 2

# Gateway Secondary Controller 시작 (포트 6800)
echo "Starting Gateway Secondary Controller (s6-s10) on port 6800..."
ryu-manager ryu-controller/gateway_secondary.py --ofp-tcp-listen-port 6800 >> $LOGFILE 2>&1 &
SECONDARY_PID=$!
sleep 2

echo "Controllers started successfully!"
echo "Primary Controller PID: $PRIMARY_PID"
echo "Secondary Controller PID: $SECONDARY_PID"
echo

# 컨트롤러 PID 저장
echo $PRIMARY_PID > /tmp/primary.pid
echo $SECONDARY_PID > /tmp/secondary.pid

# 컨트롤러 연결 확인
echo "Checking controller status..."
if ps -p $PRIMARY_PID > /dev/null; then
    echo "✓ Primary Controller is running"
else
    echo "✗ Primary Controller failed to start"
fi

if ps -p $SECONDARY_PID > /dev/null; then
    echo "✓ Secondary Controller is running"
else
    echo "✗ Secondary Controller failed to start"
fi

echo
echo "Starting Mininet topology..."
echo "This will start the network with 10 switches and 20 hosts"
echo
echo "NOTE: Gateway-based cross-controller communication enabled"
echo "MAC address-based domain routing: Primary(01-0a), Secondary(0b-14)"
echo

# Mininet 실행
if [ "$BACKGROUND" = true ]; then
    echo "Starting Mininet in background (screen session)..."
    echo "To attach: screen -r mininet"
    screen -dmS mininet python3 mininet/topology.py
    echo
    echo "✓ Mininet started in screen session 'mininet'"
    echo "✓ Controllers running in background"
    echo "✓ Logs available at: $LOGFILE"
    echo
    echo "Commands:"
    echo "  Attach to Mininet: screen -r mininet"
    echo "  View logs: tail -f $LOGFILE"
    echo "  Stop everything: /stop-sdn.sh"
else
    # 인터랙티브 모드
    python3 mininet/topology.py
    
    # 종료 시 정리
    echo
    echo "Cleaning up..."
    pkill -f ryu-manager > /dev/null 2>&1 || true
    mn -c > /dev/null 2>&1 || true
    
    echo "SDN environment stopped."
fi
