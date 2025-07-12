#!/usr/bin/env python3
"""
SDN 연결성 테스트 스크립트
"""

import subprocess
import time
import sys

def run_command(cmd):
    """명령어 실행 및 결과 반환"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_controllers():
    """컨트롤러 실행 상태 확인"""
    print("=== Controller Status Check ===")
    
    # Primary Controller 확인
    success, stdout, stderr = run_command("ps aux | grep -v grep | grep 'primary_controller.py'")
    if success and stdout.strip():
        print("✓ Primary Controller is running")
    else:
        print("✗ Primary Controller is not running")
        return False
    
    # Secondary Controller 확인
    success, stdout, stderr = run_command("ps aux | grep -v grep | grep 'secondary_controller.py'")
    if success and stdout.strip():
        print("✓ Secondary Controller is running")
    else:
        print("✗ Secondary Controller is not running")
        return False
    
    return True

def test_mininet_connectivity():
    """Mininet 내에서 연결성 테스트 (Mininet CLI 실행 중일 때)"""
    print("\n=== Connectivity Test Commands ===")
    print("Run these commands in the Mininet CLI:")
    print()
    print("1. Test basic connectivity:")
    print("   mininet> pingall")
    print()
    print("2. Test cross-controller communication:")
    print("   mininet> h1 ping h12  # Primary to Secondary")
    print("   mininet> h11 ping h2  # Secondary to Primary")
    print()
    print("3. Check flow tables:")
    print("   mininet> sh ovs-ofctl dump-flows s1")
    print("   mininet> sh ovs-ofctl dump-flows s6")
    print()
    print("4. Monitor controller logs (in separate terminals):")
    print("   $ tail -f /tmp/ryu.log")
    print()

def show_network_info():
    """네트워크 정보 표시"""
    print("\n=== Network Information ===")
    print("Topology: Tree structure with 10 switches")
    print()
    print("Controllers:")
    print("- Primary (127.0.0.1:6633): manages s1, s2, s3, s4, s5")
    print("- Secondary (127.0.0.1:6634): manages s6, s7, s8, s9, s10")
    print()
    print("Hosts:")
    print("- h1, h2 connected to s1")
    print("- h3, h4 connected to s2")
    print("- ...")
    print("- h19, h20 connected to s10")
    print()
    print("Switch connections (tree topology):")
    print("- s1 (root) ← → s2, s3")
    print("- s2 ← → s4, s5")
    print("- s3 ← → s6, s7")
    print("- s4 ← → s8, s9")
    print("- s5 ← → s10")

def main():
    """메인 함수"""
    print("SDN Connectivity Test Tool")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        show_network_info()
        return
    
    # 컨트롤러 상태 확인
    if not check_controllers():
        print("\nPlease start the controllers first:")
        print("./start_sdn.sh")
        return
    
    # 테스트 가이드 표시
    test_mininet_connectivity()
    show_network_info()

if __name__ == "__main__":
    main()