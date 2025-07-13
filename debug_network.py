#!/usr/bin/env python3
"""
SDN 네트워크 디버깅 도구
현재 네트워크 상태를 상세히 분석하고 문제를 찾아내는 도구
"""

import subprocess
import json
import os
from datetime import datetime

class NetworkDebugger:
    def __init__(self):
        self.debug_data = {
            'timestamp': datetime.now().isoformat(),
            'processes': {},
            'network': {},
            'mininet': {},
            'ovs': {},
            'controllers': {}
        }
    
    def run_command(self, cmd, description=""):
        """명령어 실행 및 결과 저장"""
        try:
            if isinstance(cmd, str):
                cmd = cmd.split()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return {
                'command': ' '.join(cmd),
                'returncode': result.returncode,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'success': result.returncode == 0
            }
        except Exception as e:
            return {
                'command': ' '.join(cmd) if isinstance(cmd, list) else cmd,
                'error': str(e),
                'success': False
            }
    
    def check_processes(self):
        """프로세스 상태 확인"""
        print("🔍 1. Process Status Check...")
        
        # RYU 컨트롤러 프로세스
        ryu_ps = self.run_command("ps aux")
        if ryu_ps['success']:
            lines = ryu_ps['stdout'].split('\n')
            ryu_processes = [line for line in lines if 'ryu-manager' in line]
            self.debug_data['processes']['ryu_controllers'] = ryu_processes
            print(f"   📡 RYU Controllers: {len(ryu_processes)} found")
            for proc in ryu_processes:
                print(f"      {proc}")
        
        # Mininet 프로세스  
        mininet_ps = [line for line in ryu_ps['stdout'].split('\n') if 'mininet' in line or 'python3 mininet/topology.py' in line]
        self.debug_data['processes']['mininet'] = mininet_ps
        print(f"   🌐 Mininet: {len(mininet_ps)} found")
        
        # OVS 프로세스
        ovs_ps = [line for line in ryu_ps['stdout'].split('\n') if 'ovs' in line]
        self.debug_data['processes']['ovs'] = ovs_ps[:5]  # 처음 5개만
        print(f"   🔀 OVS: {len(ovs_ps)} found")
    
    def check_network_namespaces(self):
        """네트워크 네임스페이스 확인"""
        print("\n🔍 2. Network Namespaces Check...")
        
        # 네임스페이스 목록
        ns_list = self.run_command("ip netns list")
        if ns_list['success']:
            namespaces = ns_list['stdout'].split('\n') if ns_list['stdout'] else []
            self.debug_data['network']['namespaces'] = namespaces
            print(f"   📦 Namespaces: {len(namespaces)} found")
            for ns in namespaces[:10]:  # 처음 10개만 출력
                if ns.strip():
                    print(f"      {ns}")
        
        # 네트워크 인터페이스
        interfaces = self.run_command("ip link show")
        if interfaces['success']:
            self.debug_data['network']['interfaces'] = interfaces['stdout']
            # veth 인터페이스 개수 계산
            veth_count = interfaces['stdout'].count('veth')
            print(f"   🔗 Virtual Interfaces: {veth_count} veth pairs found")
    
    def check_ovs_status(self):
        """OVS 스위치 상태 확인"""
        print("\n🔍 3. OVS Switch Status...")
        
        # OVS 브리지 목록
        bridges = self.run_command("ovs-vsctl list-br")
        if bridges['success']:
            bridge_list = bridges['stdout'].split('\n') if bridges['stdout'] else []
            self.debug_data['ovs']['bridges'] = bridge_list
            print(f"   🌉 OVS Bridges: {len(bridge_list)} found")
            
            # 각 브리지의 상태 확인
            for bridge in bridge_list:
                if bridge.strip():
                    print(f"      🔀 {bridge}")
                    
                    # 브리지 상세 정보
                    bridge_info = self.run_command(f"ovs-vsctl show {bridge}")
                    
                    # 컨트롤러 연결 확인
                    controller_info = self.run_command(f"ovs-vsctl get-controller {bridge}")
                    if controller_info['success']:
                        print(f"         Controller: {controller_info['stdout']}")
                        self.debug_data['ovs'][f'{bridge}_controller'] = controller_info['stdout']
                    
                    # 포트 정보
                    ports = self.run_command(f"ovs-vsctl list-ports {bridge}")
                    if ports['success']:
                        port_list = ports['stdout'].split('\n') if ports['stdout'] else []
                        print(f"         Ports: {len(port_list)} ({', '.join(port_list[:3])}{', ...' if len(port_list) > 3 else ''})")
                        self.debug_data['ovs'][f'{bridge}_ports'] = port_list
    
    def check_controller_connections(self):
        """컨트롤러 연결 상태 확인"""
        print("\n🔍 4. Controller Connection Status...")
        
        # 포트 6700, 6800 리스닝 확인
        for port in [6700, 6800]:
            netstat = self.run_command(f"netstat -tlnp | grep :{port}")
            if netstat['success'] and netstat['stdout']:
                print(f"   ✅ Port {port}: LISTENING")
                self.debug_data['controllers'][f'port_{port}'] = 'LISTENING'
            else:
                print(f"   ❌ Port {port}: NOT LISTENING")
                self.debug_data['controllers'][f'port_{port}'] = 'NOT_LISTENING'
        
        # 컨트롤러 로그 마지막 몇 줄 확인
        for controller, logfile in [('primary', 'primary.log'), ('secondary', 'secondary.log')]:
            if os.path.exists(logfile):
                tail_log = self.run_command(f"tail -n 5 {logfile}")
                if tail_log['success']:
                    self.debug_data['controllers'][f'{controller}_log'] = tail_log['stdout']
                    print(f"   📄 {controller.title()} log (last 5 lines):")
                    for line in tail_log['stdout'].split('\n'):
                        if line.strip():
                            print(f"      {line}")
    
    def check_mininet_topology(self):
        """Mininet 토폴로지 확인"""
        print("\n🔍 5. Mininet Topology Check...")
        
        # 현재 실행 중인 토폴로지가 있는지 확인
        mn_ps = self.run_command("ps aux | grep 'python3.*topology.py'")
        if mn_ps['success'] and 'topology.py' in mn_ps['stdout']:
            print("   ✅ Mininet topology is running")
            self.debug_data['mininet']['status'] = 'RUNNING'
            
            # 네트워크 네임스페이스에서 호스트 확인
            print("   🔍 Checking host accessibility...")
            
            # h1이 존재하는지 확인 (네임스페이스에서)
            namespaces = self.debug_data.get('network', {}).get('namespaces', [])
            h1_found = any('h1' in ns for ns in namespaces)
            
            if h1_found:
                print("   ✅ Host h1 namespace found")
                
                # h1에서 인터페이스 확인
                h1_if = self.run_command("ip netns exec h1 ip addr show")
                if h1_if['success']:
                    self.debug_data['mininet']['h1_interfaces'] = h1_if['stdout']
                    print("   📱 h1 interfaces:")
                    for line in h1_if['stdout'].split('\n')[:5]:
                        if line.strip():
                            print(f"      {line}")
            else:
                print("   ❌ Host h1 namespace not found")
                self.debug_data['mininet']['status'] = 'NO_HOSTS'
        else:
            print("   ❌ Mininet topology not running")
            self.debug_data['mininet']['status'] = 'NOT_RUNNING'
    
    def test_connectivity_in_namespace(self):
        """네임스페이스 내에서 연결성 테스트"""
        print("\n🔍 6. Namespace Connectivity Test...")
        
        # h1이 h2에 ping할 수 있는지 테스트
        h1_to_h2 = self.run_command("ip netns exec h1 ping -c 1 -W 2 10.0.0.2")
        if h1_to_h2['success']:
            print("   ✅ h1 → h2: SUCCESS")
            self.debug_data['mininet']['h1_to_h2'] = 'SUCCESS'
        else:
            print("   ❌ h1 → h2: FAILED")
            self.debug_data['mininet']['h1_to_h2'] = 'FAILED'
            print(f"      Error: {h1_to_h2.get('stderr', 'Unknown error')}")
        
        # h1이 h12에 ping할 수 있는지 테스트 (크로스 컨트롤러)
        h1_to_h12 = self.run_command("ip netns exec h1 ping -c 1 -W 2 10.0.0.12")
        if h1_to_h12['success']:
            print("   ✅ h1 → h12: SUCCESS")
            self.debug_data['mininet']['h1_to_h12'] = 'SUCCESS'
        else:
            print("   ❌ h1 → h12: FAILED")
            self.debug_data['mininet']['h1_to_h12'] = 'FAILED'
            print(f"      Error: {h1_to_h12.get('stderr', 'Unknown error')}")
    
    def analyze_flow_tables(self):
        """플로우 테이블 분석"""
        print("\n🔍 7. Flow Table Analysis...")
        
        bridges = self.debug_data.get('ovs', {}).get('bridges', [])
        for bridge in bridges[:3]:  # 처음 3개 브리지만
            if bridge.strip():
                flows = self.run_command(f"ovs-ofctl dump-flows {bridge}")
                if flows['success']:
                    flow_lines = flows['stdout'].split('\n')
                    flow_count = len([line for line in flow_lines if 'actions=' in line])
                    print(f"   🔀 {bridge}: {flow_count} flow rules")
                    self.debug_data['ovs'][f'{bridge}_flows'] = flows['stdout']
                    
                    # 첫 번째 플로우 룰 출력 (디버깅용)
                    for line in flow_lines[:2]:
                        if 'actions=' in line:
                            print(f"      {line[:80]}...")
    
    def generate_diagnosis(self):
        """진단 결과 생성"""
        print("\n" + "="*60)
        print("📋 DIAGNOSIS SUMMARY")
        print("="*60)
        
        issues = []
        
        # 컨트롤러 상태
        ryu_count = len(self.debug_data.get('processes', {}).get('ryu_controllers', []))
        if ryu_count != 2:
            issues.append(f"❌ Expected 2 RYU controllers, found {ryu_count}")
        else:
            print("✅ Controllers: 2 RYU controllers running")
        
        # 포트 리스닝
        for port in [6700, 6800]:
            if self.debug_data.get('controllers', {}).get(f'port_{port}') != 'LISTENING':
                issues.append(f"❌ Controller port {port} not listening")
        if not any(f'port_{port}' in issue for issue in issues for port in [6700, 6800]):
            print("✅ Ports: Controllers listening on 6700, 6800")
        
        # OVS 브리지
        bridge_count = len(self.debug_data.get('ovs', {}).get('bridges', []))
        if bridge_count < 10:
            issues.append(f"❌ Expected 10 OVS bridges, found {bridge_count}")
        else:
            print(f"✅ OVS: {bridge_count} bridges found")
        
        # Mininet 상태
        mn_status = self.debug_data.get('mininet', {}).get('status', 'UNKNOWN')
        if mn_status != 'RUNNING':
            issues.append(f"❌ Mininet topology not running properly")
        else:
            print("✅ Mininet: Topology running")
        
        # 연결성
        h1_h2 = self.debug_data.get('mininet', {}).get('h1_to_h2', 'UNKNOWN')
        h1_h12 = self.debug_data.get('mininet', {}).get('h1_to_h12', 'UNKNOWN')
        
        if h1_h2 != 'SUCCESS':
            issues.append("❌ Same-controller connectivity failed (h1→h2)")
        else:
            print("✅ Same-controller: h1→h2 working")
            
        if h1_h12 != 'SUCCESS':
            issues.append("❌ Cross-controller connectivity failed (h1→h12)")
        else:
            print("✅ Cross-controller: h1→h12 working")
        
        if issues:
            print(f"\n🚨 ISSUES FOUND ({len(issues)}):")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n🎉 ALL CHECKS PASSED!")
        
        return issues
    
    def save_debug_data(self):
        """디버그 데이터 저장"""
        with open('debug_network.json', 'w') as f:
            json.dump(self.debug_data, f, indent=2)
        print(f"\n💾 Debug data saved to: debug_network.json")

def main():
    debugger = NetworkDebugger()
    
    print("🔧 SDN Network Debugger")
    print("="*60)
    
    try:
        debugger.check_processes()
        debugger.check_network_namespaces()
        debugger.check_ovs_status()
        debugger.check_controller_connections()
        debugger.check_mininet_topology()
        debugger.test_connectivity_in_namespace()
        debugger.analyze_flow_tables()
        
        issues = debugger.generate_diagnosis()
        debugger.save_debug_data()
        
        return len(issues) == 0
        
    except Exception as e:
        print(f"\n❌ Debugger failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)