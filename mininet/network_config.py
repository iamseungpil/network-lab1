#!/usr/bin/env python3

"""네트워크 설정 및 유틸리티"""

# 네트워크 설정
NETWORK_CONFIG = {
    'switches': {
        'count': 10,
        'dpid_format': '000000000000000{:x}',
        'base_name': 's'
    },
    'hosts': {
        'per_switch': 2,
        'ip_base': '10.0.0',
        'base_name': 'h'
    },
    'controllers': {
        'primary': {
            'name': 'c1',
            'ip': 'controller1',
            'port': 6633
        },
        'secondary': {
            'name': 'c2', 
            'ip': 'controller2',
            'port': 6633
        }
    }
}

# 스위치 연결 구조 (트리 토폴로지)
SWITCH_LINKS = [
    ('s1', 's2'), ('s1', 's3'),
    ('s2', 's4'), ('s2', 's5'),
    ('s3', 's6'), ('s3', 's7'),
    ('s4', 's8'), ('s4', 's9'),
    ('s5', 's10')
]

def get_switch_dpid(switch_num):
    """스위치 번호로부터 DPID 생성"""
    return NETWORK_CONFIG['switches']['dpid_format'].format(switch_num)

def get_host_ip(host_num):
    """호스트 번호로부터 IP 주소 생성"""
    return f"{NETWORK_CONFIG['hosts']['ip_base']}.{host_num}/24"

def print_topology_info():
    """토폴로지 정보 출력"""
    print("=== SDN Network Topology ===")
    print(f"Switches: {NETWORK_CONFIG['switches']['count']}")
    print(f"Hosts: {NETWORK_CONFIG['switches']['count'] * NETWORK_CONFIG['hosts']['per_switch']}")
    print(f"Controllers: 2 (Primary + Secondary)")
    print("\nSwitch Links:")
    for link in SWITCH_LINKS:
        print(f"  {link[0]} -- {link[1]}")

if __name__ == '__main__':
    print_topology_info()