#!/bin/bash

echo "=== SDN Lab 환경 설치 시작 ==="

# 실행 권한 부여
chmod +x install-docker.sh
chmod +x install-mininet.sh
chmod +x install-ryu.sh

# 순차 설치
echo "1. Docker 설치 중..."
./install-docker.sh

echo "2. Mininet 설치 중..."
./install-mininet.sh

echo "3. RYU 설치 중..."
./install-ryu.sh

echo "=== 모든 설치 완료 ==="
echo ""
echo "다음 단계:"
echo "1. 로그아웃 후 다시 로그인 (Docker 그룹 적용)"
echo "2. 설치 확인:"
echo "   - docker --version"
echo "   - sudo mn --version"
echo "   - ryu-manager --help"