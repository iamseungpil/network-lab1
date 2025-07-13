#!/bin/bash

echo "=== Stopping SDN Environment ==="
echo

# Conda 환경 활성화 (환경 변수 확인용)
eval "$(conda shell.bash hook)" 2>/dev/null
if [[ "$CONDA_DEFAULT_ENV" == "sdn-lab" ]]; then
    echo "✓ Conda environment 'sdn-lab' detected"
else
    echo "ℹ Running outside conda environment"
fi

echo

# Mininet 정리
echo "Stopping Mininet network..."
sudo mn -c > /dev/null 2>&1

# RYU 컨트롤러 프로세스 종료
echo "Stopping RYU controllers..."
pkill -f "ryu-manager.*primary_controller" > /dev/null 2>&1
pkill -f "ryu-manager.*secondary_controller" > /dev/null 2>&1

# 더 강력한 정리 (모든 ryu-manager 프로세스)
pkill -f ryu-manager > /dev/null 2>&1

# Python 토폴로지 프로세스 종료
sudo pkill -f "python.*topology.py" > /dev/null 2>&1

# 5초 대기
echo "Waiting for cleanup..."
sleep 3

# 최종 상태 확인
echo
echo "=== Final Status Check ==="

# 컨트롤러 포트 확인
if netstat -tlnp 2>/dev/null | grep -E "(6633|6634)" > /dev/null; then
    echo "⚠️  Warning: Some controller processes may still be running"
    echo "   Active ports:"
    netstat -tlnp 2>/dev/null | grep -E "(6633|6634)"
else
    echo "✓ Controller ports (6633, 6634) are free"
fi

# RYU 프로세스 확인
if ps aux | grep -v grep | grep "ryu-manager" > /dev/null; then
    echo "⚠️  Warning: Some RYU processes may still be running"
    ps aux | grep -v grep | grep "ryu-manager" | awk '{print "   PID " $2 ": " $11 " " $12}'
else
    echo "✓ No RYU controller processes running"
fi

# Mininet 프로세스 확인
if ps aux | grep -v grep | grep -E "(mininet|mn)" > /dev/null; then
    echo "⚠️  Warning: Some Mininet processes may still be running"
else
    echo "✓ No Mininet processes running"
fi

echo
echo "=== SDN Environment Stopped ==="
echo
echo "To restart the environment, run:"
echo "  ./start_sdn.sh"
echo
echo "If processes are still running, try:"
echo "  sudo pkill -9 -f ryu-manager"
echo "  sudo mn -c"
echo "  sudo pkill -9 -f mininet"