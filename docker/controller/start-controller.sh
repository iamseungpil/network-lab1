#!/bin/bash

echo "Starting Controller ${CONTROLLER_ID} (${CONTROLLER_TYPE})"

# 설정 파일 확인
if [ ! -f /app/config/controller.json ]; then
    echo "Warning: No config file found"
fi

# 컨트롤러 실행 방식 선택
if [ "${USE_SIMPLE_CONTROLLER:-true}" = "true" ]; then
    echo "Starting Simple Python Controller..."
    python3 /app/controllers/simple_controller.py
else
    # RYU 사용 (eventlet 문제로 인해 현재 비활성화)
    if [ "${CONTROLLER_TYPE}" = "primary" ]; then
        echo "Starting Primary Controller..."
        ryu-manager /app/controllers/primary_controller.py --verbose --observe-links
    else
        echo "Starting Secondary Controller..."
        ryu-manager /app/controllers/secondary_controller.py --verbose --observe-links
    fi
fi