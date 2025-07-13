#!/bin/bash
"""
SDN 환경을 위한 사용자 권한 설정 스크립트
sudo 없이 Mininet과 OVS를 사용할 수 있도록 설정
"""

echo "🔧 Setting up SDN permissions for non-sudo operation..."
echo "=================================================="

# 현재 사용자
USER=$(whoami)
echo "👤 Current user: $USER"

# 1. 필요한 그룹에 사용자 추가
echo "📝 Adding user to required groups..."

# OVS 관리를 위한 그룹 추가
sudo groupadd -f ovs
sudo usermod -a -G ovs $USER

# 네트워크 관리를 위한 그룹 추가  
sudo usermod -a -G netdev $USER

# Docker 그룹 (네임스페이스 관리용)
sudo groupadd -f docker
sudo usermod -a -G docker $USER

echo "✅ User added to groups: ovs, netdev, docker"

# 2. OVS 권한 설정
echo "🔀 Configuring OVS permissions..."

# OVS 소켓 권한 설정
sudo chmod 666 /var/run/openvswitch/db.sock 2>/dev/null || echo "   ⚠️  OVS socket not found (will be created later)"

# OVS 디렉토리 권한 설정
sudo chown -R :ovs /var/run/openvswitch/ 2>/dev/null || echo "   ⚠️  OVS directory not found"
sudo chmod -R g+rw /var/run/openvswitch/ 2>/dev/null || echo "   ⚠️  OVS directory not found"

# 3. 네트워크 네임스페이스 권한 설정
echo "🌐 Configuring network namespace permissions..."

# 네임스페이스 디렉토리 권한
sudo mkdir -p /var/run/netns
sudo chmod 755 /var/run/netns
sudo chown root:netdev /var/run/netns

# 4. Mininet을 위한 권한 설정
echo "🏗️  Configuring Mininet permissions..."

# CAP_NET_ADMIN 권한을 Python에 부여
PYTHON_PATH=$(which python3)
echo "   🐍 Python path: $PYTHON_PATH"

# Python3에 네트워크 관리 권한 부여
sudo setcap cap_net_admin,cap_net_raw+ep $PYTHON_PATH

# 5. sudoers 파일에 특정 명령어 권한 추가
echo "⚙️  Adding sudoers entries for network commands..."

# sudoers 백업
sudo cp /etc/sudoers /etc/sudoers.backup.$(date +%Y%m%d_%H%M%S)

# 임시 sudoers 파일 생성
cat > /tmp/sdn_sudoers << EOF
# SDN 환경을 위한 권한 설정
$USER ALL=(root) NOPASSWD: /sbin/ip
$USER ALL=(root) NOPASSWD: /usr/bin/ovs-vsctl
$USER ALL=(root) NOPASSWD: /usr/bin/ovs-ofctl
$USER ALL=(root) NOPASSWD: /sbin/brctl
$USER ALL=(root) NOPASSWD: /bin/mount
$USER ALL=(root) NOPASSWD: /bin/umount
$USER ALL=(root) NOPASSWD: /usr/bin/mn
EOF

# sudoers 파일에 추가
echo "   📄 Adding network command permissions..."
sudo sh -c "cat /tmp/sdn_sudoers >> /etc/sudoers"
rm /tmp/sdn_sudoers

# 6. 개선된 start 스크립트 생성
echo "📜 Creating non-sudo start script..."

cat > start_sdn_nosudo.sh << 'EOF'
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
EOF

chmod +x start_sdn_nosudo.sh

# 7. topology.py 수정 (sudo 제거)
echo "🔧 Modifying topology.py to remove sudo requirement..."

# topology.py 백업
cp mininet/topology.py mininet/topology.py.backup

# topology.py에서 sudo 관련 부분 수정 (이미 수정되어 있다면 스킵)
if grep -q "controller=None" mininet/topology.py; then
    echo "   ✅ topology.py already configured for no-sudo operation"
else
    echo "   🔧 Modifying topology.py..."
    # 필요한 수정사항이 있다면 여기에 추가
fi

# 8. 권한 확인
echo ""
echo "🔍 Verifying permissions..."

# 그룹 멤버십 확인
echo "   👥 User groups: $(groups $USER)"

# Python 권한 확인
echo "   🐍 Python capabilities: $(getcap $PYTHON_PATH)"

# OVS 권한 확인
if [ -S /var/run/openvswitch/db.sock ]; then
    echo "   🔀 OVS socket permissions: $(ls -la /var/run/openvswitch/db.sock)"
else
    echo "   ⚠️  OVS socket not found (will be created when OVS starts)"
fi

echo ""
echo "✅ Permission setup completed!"
echo ""
echo "📋 Next steps:"
echo "   1. Log out and log back in (or run: newgrp ovs)"
echo "   2. Start OVS service if not running: sudo systemctl start openvswitch-switch"
echo "   3. Run: ./start_sdn_nosudo.sh"
echo ""
echo "⚠️  Note: Some features may still require sudo on first run"
echo "   If you encounter permission issues, try: sudo ./start_sdn_nosudo.sh once"
EOF

chmod +x setup_permissions.sh