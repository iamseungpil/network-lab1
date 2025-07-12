#!/usr/bin/env python3
"""
SDN Flow Rule Management CLI
간단한 명령행 인터페이스로 플로우 규칙을 설정하고 관리
"""

import cmd
import subprocess
import json
import re
import sys
from datetime import datetime

class SDNCLI(cmd.Cmd):
    intro = '''
=== SDN Flow Rule Management CLI ===
10개 스위치 + 2개 컨트롤러 환경 관리

주요 명령어:
  show flows <switch>     - 플로우 테이블 조회
  show switches          - 모든 스위치 상태
  add flow <args>        - 플로우 규칙 추가  
  del flow <switch> <id> - 플로우 규칙 삭제
  test ping <src> <dst>  - 연결성 테스트
  help                   - 도움말

Type 'help <command>' for detailed usage.
'''
    prompt = 'sdn> '

    def __init__(self):
        super().__init__()
        self.switches = [f's{i}' for i in range(1, 11)]
        self.hosts = [f'h{i}' for i in range(1, 21)]
        self.controllers = {
            'primary': {'switches': ['s1', 's2', 's3', 's4', 's5'], 'port': 6633},
            'secondary': {'switches': ['s6', 's7', 's8', 's9', 's10'], 'port': 6634}
        }

    def do_show(self, arg):
        """Show network information
        Usage: 
          show flows <switch>    - Show flow table for specific switch
          show switches         - Show all switches status
          show topology         - Show network topology
          show hosts            - Show all hosts
        """
        args = arg.split()
        if not args:
            self.help_show()
            return
            
        cmd = args[0]
        if cmd == 'flows':
            if len(args) < 2:
                print("Usage: show flows <switch>")
                return
            self._show_flows(args[1])
        elif cmd == 'switches':
            self._show_switches()
        elif cmd == 'topology':
            self._show_topology()
        elif cmd == 'hosts':
            self._show_hosts()
        else:
            print(f"Unknown show command: {cmd}")
            self.help_show()

    def _show_flows(self, switch):
        """Show flow table for a specific switch"""
        if switch not in self.switches:
            print(f"Error: Switch {switch} not found. Available: {', '.join(self.switches)}")
            return
            
        try:
            result = subprocess.run(
                ['sudo', 'ovs-ofctl', 'dump-flows', switch],
                capture_output=True, text=True, check=True
            )
            print(f"\n=== Flow Table for {switch} ===")
            flows = result.stdout.strip().split('\n')
            
            if len(flows) <= 1:
                print("No flows found")
                return
                
            for i, flow in enumerate(flows):
                if flow.strip() and not flow.startswith('NXST_FLOW'):
                    # 플로우 파싱 및 포맷팅
                    flow_id = i
                    if 'priority=' in flow:
                        priority = re.search(r'priority=(\d+)', flow)
                        priority = priority.group(1) if priority else 'N/A'
                    else:
                        priority = 'N/A'
                        
                    print(f"Flow {flow_id}: priority={priority}")
                    print(f"  {flow}")
                    
        except subprocess.CalledProcessError as e:
            print(f"Error: Cannot access switch {switch}. Is Mininet running?")
        except FileNotFoundError:
            print("Error: ovs-ofctl not found. Is Open vSwitch installed?")

    def _show_switches(self):
        """Show status of all switches"""
        print("\n=== Switch Status ===")
        for switch in self.switches:
            controller = 'Primary' if switch in self.controllers['primary']['switches'] else 'Secondary'
            try:
                result = subprocess.run(
                    ['sudo', 'ovs-vsctl', 'show'],
                    capture_output=True, text=True, check=True
                )
                if switch in result.stdout:
                    status = "Active"
                else:
                    status = "Inactive"
            except:
                status = "Unknown"
                
            print(f"  {switch}: {status} (Controller: {controller})")

    def _show_topology(self):
        """Show network topology"""
        print("\n=== Network Topology ===")
        print("""
                    s1 (root)
                   /         \\
                 s2           s3
                / \\          /  \\
              s4   s5      s6   s7
             / \\    |           
           s8   s9  s10         

Controllers:
- Primary (127.0.0.1:6633): s1, s2, s3, s4, s5
- Secondary (127.0.0.1:6634): s6, s7, s8, s9, s10

Hosts: 2 hosts per switch (h1,h2 on s1, h3,h4 on s2, ...)
""")

    def _show_hosts(self):
        """Show all hosts and their assignments"""
        print("\n=== Host Assignments ===")
        for i in range(1, 11):
            switch = f's{i}'
            host1 = f'h{i*2-1}'
            host2 = f'h{i*2}'
            controller = 'Primary' if switch in self.controllers['primary']['switches'] else 'Secondary'
            print(f"  {switch} ({controller}): {host1} (10.0.0.{i*2-1}), {host2} (10.0.0.{i*2})")

    def do_add(self, arg):
        """Add flow rule
        Usage: add flow <switch> <src_mac> <dst_mac> <action>
        Example: add flow s1 00:00:00:00:00:01 00:00:00:00:00:03 output:2
        """
        args = arg.split()
        if len(args) < 5 or args[0] != 'flow':
            print("Usage: add flow <switch> <src_mac> <dst_mac> <action>")
            return
            
        switch, src_mac, dst_mac, action = args[1], args[2], args[3], args[4]
        self._add_flow(switch, src_mac, dst_mac, action)

    def _add_flow(self, switch, src_mac, dst_mac, action):
        """Add a flow rule to the specified switch"""
        if switch not in self.switches:
            print(f"Error: Switch {switch} not found")
            return
            
        try:
            flow_rule = f"priority=100,dl_src={src_mac},dl_dst={dst_mac},actions={action}"
            result = subprocess.run(
                ['sudo', 'ovs-ofctl', 'add-flow', switch, flow_rule],
                capture_output=True, text=True, check=True
            )
            print(f"✓ Flow rule added to {switch}")
            print(f"  Rule: {flow_rule}")
        except subprocess.CalledProcessError as e:
            print(f"Error adding flow rule: {e}")

    def do_del(self, arg):
        """Delete flow rule
        Usage: del flow <switch> [match_criteria]
        Example: 
          del flow s1                           - Delete all flows
          del flow s1 dl_src=00:00:00:00:00:01  - Delete specific flow
        """
        args = arg.split()
        if len(args) < 2 or args[0] != 'flow':
            print("Usage: del flow <switch> [match_criteria]")
            return
            
        switch = args[1]
        match = args[2] if len(args) > 2 else ""
        self._del_flow(switch, match)

    def _del_flow(self, switch, match=""):
        """Delete flow rules from the specified switch"""
        if switch not in self.switches:
            print(f"Error: Switch {switch} not found")
            return
            
        try:
            if match:
                cmd = ['sudo', 'ovs-ofctl', 'del-flows', switch, match]
                print(f"Deleting flows matching '{match}' from {switch}")
            else:
                cmd = ['sudo', 'ovs-ofctl', 'del-flows', switch]
                print(f"Deleting all flows from {switch}")
                
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✓ Flow rules deleted")
        except subprocess.CalledProcessError as e:
            print(f"Error deleting flow rules: {e}")

    def do_test(self, arg):
        """Test network connectivity
        Usage: 
          test ping <src_host> <dst_host>     - Test ping between hosts
          test pingall                        - Test connectivity between all hosts
        """
        args = arg.split()
        if not args:
            self.help_test()
            return
            
        cmd = args[0]
        if cmd == 'ping':
            if len(args) < 3:
                print("Usage: test ping <src_host> <dst_host>")
                return
            self._test_ping(args[1], args[2])
        elif cmd == 'pingall':
            self._test_pingall()
        else:
            print(f"Unknown test command: {cmd}")
            self.help_test()

    def _test_ping(self, src, dst):
        """Test ping between two hosts"""
        if src not in self.hosts or dst not in self.hosts:
            print(f"Error: Invalid hosts. Available: {', '.join(self.hosts)}")
            return
            
        print(f"\n=== Testing {src} → {dst} ===")
        try:
            # Mininet이 실행 중인지 확인
            result = subprocess.run(
                ['sudo', 'mn', '--test', 'none'],
                capture_output=True, text=True, timeout=5
            )
            print("Please run this command in Mininet CLI:")
            print(f"mininet> {src} ping -c 3 {dst}")
        except:
            print("Note: This command should be run when Mininet is active")

    def _test_pingall(self):
        """Test connectivity between all hosts"""
        print("\n=== Testing connectivity between all hosts ===")
        print("Please run this command in Mininet CLI:")
        print("mininet> pingall")

    def do_clear(self, arg):
        """Clear all flow rules from all switches"""
        print("Clearing all flow rules from all switches...")
        for switch in self.switches:
            try:
                subprocess.run(
                    ['sudo', 'ovs-ofctl', 'del-flows', switch],
                    capture_output=True, text=True, check=True
                )
                print(f"✓ Cleared flows from {switch}")
            except subprocess.CalledProcessError:
                print(f"✗ Failed to clear flows from {switch}")

    def do_status(self, arg):
        """Show overall SDN network status"""
        print(f"\n=== SDN Network Status ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
        
        # 컨트롤러 상태 확인
        print("\nController Status:")
        for name, info in self.controllers.items():
            try:
                result = subprocess.run(
                    ['ps', 'aux'], capture_output=True, text=True
                )
                if f'{name}_controller.py' in result.stdout:
                    status = "Running"
                else:
                    status = "Stopped"
            except:
                status = "Unknown"
            print(f"  {name.title()} Controller (port {info['port']}): {status}")
        
        # 스위치 요약
        print(f"\nSwitch Summary: {len(self.switches)} switches")
        print(f"Host Summary: {len(self.hosts)} hosts")
        
        # 빠른 연결 테스트
        print("\nQuick connectivity check:")
        print("Run 'test pingall' for full connectivity test")

    def do_exit(self, arg):
        """Exit the CLI"""
        print("Goodbye!")
        return True
        
    def do_quit(self, arg):
        """Exit the CLI"""
        return self.do_exit(arg)

    def help_show(self):
        print("""
Show network information:
  show flows <switch>    - Display flow table for specific switch
  show switches         - Display status of all switches  
  show topology         - Display network topology diagram
  show hosts            - Display host-to-switch assignments
        """)

    def help_test(self):
        print("""
Test network functionality:
  test ping <src> <dst>  - Test connectivity between two hosts
  test pingall          - Test connectivity between all hosts
        """)

    def emptyline(self):
        """Handle empty line input"""
        pass

def main():
    """Main function to start CLI"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print(SDNCLI.intro)
        return
        
    try:
        SDNCLI().cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()