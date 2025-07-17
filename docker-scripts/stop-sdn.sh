#!/bin/bash

echo "Stopping SDN environment..."

# PID 파일에서 컨트롤러 PID 읽기
if [ -f /tmp/primary.pid ]; then
    PRIMARY_PID=$(cat /tmp/primary.pid)
    if ps -p $PRIMARY_PID > /dev/null 2>&1; then
        kill $PRIMARY_PID
        echo "✓ Primary Controller stopped"
    fi
    rm /tmp/primary.pid
fi

if [ -f /tmp/secondary.pid ]; then
    SECONDARY_PID=$(cat /tmp/secondary.pid)
    if ps -p $SECONDARY_PID > /dev/null 2>&1; then
        kill $SECONDARY_PID
        echo "✓ Secondary Controller stopped"
    fi
    rm /tmp/secondary.pid
fi

# Screen 세션 종료
screen -S mininet -X quit > /dev/null 2>&1

# 기타 프로세스 정리
pkill -f ryu-manager > /dev/null 2>&1 || true
mn -c > /dev/null 2>&1 || true

echo "✓ SDN environment stopped"
