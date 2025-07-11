#!/bin/bash

echo "=== Docker 권한 설정 스크립트 ==="

echo "1. 현재 사용자 그룹 확인:"
groups

echo ""
echo "2. Docker 그룹 존재 여부 확인:"
getent group docker

echo ""
echo "3. 다음 명령어들을 순서대로 실행하세요:"
echo ""
echo "# Docker 그룹이 없다면 생성 (일반적으로 이미 있음)"
echo "sudo groupadd docker"
echo ""
echo "# 현재 사용자를 docker 그룹에 추가"
echo "sudo usermod -aG docker \$USER"
echo ""
echo "# Docker 소켓 권한 확인 및 설정"
echo "sudo chown root:docker /var/run/docker.sock"
echo "sudo chmod 660 /var/run/docker.sock"
echo ""
echo "# 그룹 변경사항 즉시 적용 (둘 중 하나 선택)"
echo "newgrp docker"
echo "# 또는"
echo "exec su -l \$USER"
echo ""
echo "# 권한 확인"
echo "docker ps"

echo ""
echo "=== 실행 후 테스트 ==="
echo "docker --version"
echo "docker ps"
echo ""
echo "성공하면 아래 명령어로 SDN 환경 재시작:"
echo "cd /home/starmooc/starmooc-lab1/scripts"
echo "./start-sdn.sh"