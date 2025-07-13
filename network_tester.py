#!/usr/bin/env python3
"""
SDN 네트워크 연결성 테스트 도구
Mininet CLI 없이 호스트 간 연결을 확인할 수 있는 독립적인 테스트 도구
"""

import subprocess
import time
import sys
import json
from datetime import datetime

class NetworkTester:
    def __init__(self):
        self.results = {}
        
    def ping_test(self, src_ip, dst_ip, count=1, timeout=3):
        """특정 IP 간 ping 테스트"""
        try:
            cmd = f"ping -c {count} -W {timeout} {dst_ip}"
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=timeout+2)
            
            if result.returncode == 0:
                # 성공 시 RTT 추출
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'time=' in line:
                        rtt = line.split('time=')[1].split(' ')[0]
                        return {'success': True, 'rtt': rtt, 'output': result.stdout}
                return {'success': True, 'rtt': 'unknown', 'output': result.stdout}
            else:
                return {'success': False, 'error': result.stderr, 'output': result.stdout}
                
        except Exception as e:
            return {'success': False, 'error': str(e), 'output': ''}
    
    def test_host_connectivity(self, host_pairs):
        """호스트 쌍들 간의 연결성 테스트"""
        print("🔍 SDN Network Connectivity Test")
        print("=" * 50)
        print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        results = {}
        
        for src, dst in host_pairs:
            src_name, src_ip = src
            dst_name, dst_ip = dst
            
            print(f"📡 Testing {src_name}({src_ip}) → {dst_name}({dst_ip})... ", end="", flush=True)
            
            result = self.ping_test(src_ip, dst_ip, count=1, timeout=2)
            
            if result['success']:
                print(f"✅ SUCCESS ({result['rtt']}ms)")
                results[f"{src_name}->{dst_name}"] = {'status': 'SUCCESS', 'rtt': result['rtt']}
            else:
                print(f"❌ FAILED")
                results[f"{src_name}->{dst_name}"] = {'status': 'FAILED', 'error': result.get('error', 'Unknown')}
                
            time.sleep(0.5)  # 테스트 간 간격
        
        return results
    
    def test_controller_areas(self):
        """Primary와 Secondary Controller 영역 간 테스트"""
        # Primary Controller 영역 (h1-h10)
        primary_hosts = [
            ('h1', '10.0.0.1'), ('h2', '10.0.0.2'), ('h3', '10.0.0.3'), ('h4', '10.0.0.4'),
            ('h5', '10.0.0.5'), ('h6', '10.0.0.6'), ('h7', '10.0.0.7'), ('h8', '10.0.0.8'),
            ('h9', '10.0.0.9'), ('h10', '10.0.0.10')
        ]
        
        # Secondary Controller 영역 (h11-h20)  
        secondary_hosts = [
            ('h11', '10.0.0.11'), ('h12', '10.0.0.12'), ('h13', '10.0.0.13'), ('h14', '10.0.0.14'),
            ('h15', '10.0.0.15'), ('h16', '10.0.0.16'), ('h17', '10.0.0.17'), ('h18', '10.0.0.18'),
            ('h19', '10.0.0.19'), ('h20', '10.0.0.20')
        ]
        
        test_pairs = []
        
        # 1. 같은 컨트롤러 내 테스트
        print("🏠 Same Controller Tests:")
        test_pairs.extend([
            (primary_hosts[0], primary_hosts[1]),    # h1 -> h2
            (primary_hosts[2], primary_hosts[3]),    # h3 -> h4
            (secondary_hosts[0], secondary_hosts[1]), # h11 -> h12
            (secondary_hosts[2], secondary_hosts[3]), # h13 -> h14
        ])
        
        # 2. 크로스 컨트롤러 테스트
        print("\n🌐 Cross-Controller Tests:")
        cross_tests = [
            (primary_hosts[0], secondary_hosts[1]),  # h1 -> h12
            (primary_hosts[4], secondary_hosts[0]),  # h5 -> h11
            (secondary_hosts[1], primary_hosts[0]),  # h12 -> h1
            (secondary_hosts[5], primary_hosts[2]),  # h16 -> h3
        ]
        
        # 같은 컨트롤러 테스트 실행
        same_controller_results = self.test_host_connectivity(test_pairs[:4])
        
        print("\n" + "="*50)
        
        # 크로스 컨트롤러 테스트 실행  
        cross_controller_results = self.test_host_connectivity(cross_tests)
        
        return {
            'same_controller': same_controller_results,
            'cross_controller': cross_controller_results
        }
    
    def check_controller_status(self):
        """컨트롤러 실행 상태 확인"""
        print("🔧 Controller Status Check:")
        print("-" * 30)
        
        try:
            # Primary Controller 확인
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            primary_running = 'primary_controller.py' in result.stdout and '6700' in result.stdout
            secondary_running = 'secondary_controller.py' in result.stdout and '6800' in result.stdout
            
            print(f"Primary Controller (6700):   {'🟢 RUNNING' if primary_running else '🔴 STOPPED'}")
            print(f"Secondary Controller (6800): {'🟢 RUNNING' if secondary_running else '🔴 STOPPED'}")
            print()
            
            return primary_running and secondary_running
            
        except Exception as e:
            print(f"❌ Error checking controllers: {e}")
            return False
    
    def generate_report(self, results):
        """테스트 결과 리포트 생성"""
        print("\n📊 Test Summary Report")
        print("=" * 50)
        
        total_tests = 0
        successful_tests = 0
        
        for category, tests in results.items():
            print(f"\n{category.replace('_', ' ').title()}:")
            for test_name, result in tests.items():
                total_tests += 1
                if result['status'] == 'SUCCESS':
                    successful_tests += 1
                    print(f"  ✅ {test_name}: {result['rtt']}ms")
                else:
                    print(f"  ❌ {test_name}: FAILED")
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\n📈 Overall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        
        return success_rate

def main():
    tester = NetworkTester()
    
    print("🚀 SDN Network Connectivity Tester")
    print("=" * 50)
    
    # 1. 컨트롤러 상태 확인
    if not tester.check_controller_status():
        print("⚠️  Warning: Controllers may not be running properly")
        print("   Please ensure both controllers are started before testing")
        print()
    
    # 2. 네트워크 연결성 테스트
    try:
        results = tester.test_controller_areas()
        
        # 3. 결과 리포트
        success_rate = tester.generate_report(results)
        
        # 4. 결과를 JSON으로 저장
        with open('network_test_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'success_rate': success_rate
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: network_test_results.json")
        
        # 5. 종료 코드 반환
        sys.exit(0 if success_rate >= 80 else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()