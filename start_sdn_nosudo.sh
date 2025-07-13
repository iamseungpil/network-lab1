#!/bin/bash

echo "=== Starting SDN Environment (No Sudo) ==="
echo

# Conda 환경 활성화
echo "Activating conda environment 'sdn-lab'..."
source /home/starmooc/miniconda3/bin/activate sdn-lab

if [[ "$CONDA_DEFAULT_ENV" != "sdn-lab" ]]; then
    echo "❌ Failed to activate conda environment 'sdn-lab'"
    exit 1
fi

echo "✅ Conda environment 'sdn-lab' activated ($(python --version))"
echo

# 기존 프로세스 정리
echo "Cleaning up existing processes..."
pkill -f ryu-manager > /dev/null 2>&1
sudo mn -c > /dev/null 2>&1

# 디렉토리 이동
cd "$(dirname "$0")"

echo "Starting controllers..."

# Primary Controller 시작 (포트 6700)
echo "Starting Primary Controller (s1-s5) on port 6700..."
ryu-manager ryu-controller/primary_controller.py --ofp-tcp-listen-port 6700 > primary.log 2>&1 &
PRIMARY_PID=$!
sleep 2

# Secondary Controller 시작 (포트 6800)
echo "Starting Secondary Controller (s6-s10) on port 6800..."
ryu-manager ryu-controller/secondary_controller.py --ofp-tcp-listen-port 6800 > secondary.log 2>&1 &
SECONDARY_PID=$!
sleep 2

echo "Controllers started successfully!"
echo "Primary Controller PID: $PRIMARY_PID"
echo "Secondary Controller PID: $SECONDARY_PID"
echo

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
echo "Starting Mininet topology (no sudo)..."
echo "This will start the network with 10 switches and 20 hosts"
echo

# Mininet 토폴로지 실행 (sudo 없이)
python3 mininet/topology.py

# 종료 시 정리
echo
echo "Cleaning up..."
pkill -f ryu-manager > /dev/null 2>&1
sudo mn -c > /dev/null 2>&1

echo "SDN environment stopped."
echo "To use again, run: ./start_sdn_nosudo.sh"
