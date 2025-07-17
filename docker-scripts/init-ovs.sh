#!/bin/bash
# OVS 서비스 시작 - systemd 없이도 작동하도록 개선

echo "Initializing Open vSwitch..."

# OVS 모듈 로드
modprobe openvswitch 2>/dev/null || true

# OVS 디렉토리 생성
mkdir -p /var/run/openvswitch
mkdir -p /var/log/openvswitch

# OVS 데이터베이스 초기화
if [ ! -f /etc/openvswitch/conf.db ]; then
    echo "Creating OVS database..."
    ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema
fi

# ovsdb-server 시작
if ! pgrep -x ovsdb-server > /dev/null; then
    echo "Starting ovsdb-server..."
    ovsdb-server --remote=punix:/var/run/openvswitch/db.sock \
                 --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
                 --private-key=db:Open_vSwitch,SSL,private_key \
                 --certificate=db:Open_vSwitch,SSL,certificate \
                 --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert \
                 --pidfile --detach --log-file
    sleep 2
fi

# OVS 초기화
echo "Initializing OVS..."
ovs-vsctl --no-wait init

# ovs-vswitchd 시작
if ! pgrep -x ovs-vswitchd > /dev/null; then
    echo "Starting ovs-vswitchd..."
    ovs-vswitchd --pidfile --detach --log-file
    sleep 2
fi

# OVS 상태 확인
echo "OVS status:"
ovs-vsctl show

echo "OVS initialization complete."
