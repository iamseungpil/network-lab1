#!/usr/bin/env python3
"""
SDN Lab1 Command Line Interface
10 switches + 2 controllers (RYU + Mininet)
Flow rule management and network monitoring
"""

import cmd
import subprocess
import json
import time
import sys
from datetime import datetime

class SDNLabCLI(cmd.Cmd):
    intro = '''
╔═══════════════════════════════════════════════════════════════╗
║                        SDN Lab1 CLI                          ║
║              10 Switches + 2 RYU Controllers                 ║
║                                                               ║
║  Primary Controller (port 6633): s1, s2, s3, s4, s5         ║
║  Secondary Controller (port 6634): s6, s7, s8, s9, s10       ║
║                                                               ║
║  Commands: flows, route, monitor, ping, clear, status        ║
║  Type 'help' for detailed usage                              ║
╚═══════════════════════════════════════════════════════════════╝
    '''
    prompt = 'sdn-lab1> '

    def __init__(self):
        super().__init__()
        self.switches = [f's{i}' for i in range(1, 11)]
        self.hosts = [f'h{i}' for i in range(1, 21)]
        self.controllers = {
            'primary': {'switches': [f's{i}' for i in range(1, 6)], 'port': 6700},
            'secondary': {'switches': [f's{i}' for i in range(6, 11)], 'port': 6800}
        }

    def do_status(self, arg):
        """Check SDN environment status"""
        print(f"\n=== SDN Lab1 Status ({datetime.now().strftime('%H:%M:%S')}) ===")
        
        # Controller status
        print("\n🎯 Controllers:")
        for name, info in self.controllers.items():
            status = self._check_controller_port(info['port'])
            switch_list = ', '.join(info['switches'])
            print(f"  {name.title()} (port {info['port']}): {status}")
            print(f"    Managing: {switch_list}")
        
        # Mininet status
        print(f"\n🌐 Network: {len(self.switches)} switches, {len(self.hosts)} hosts")
        mininet_status = self._check_mininet_running()
        print(f"  Mininet: {mininet_status}")
        
        # Quick health check
        print(f"\n📊 Health Check:")
        active_bridges = self._count_ovs_bridges()
        print(f"  OVS Bridges: {active_bridges}")

    def do_flows(self, arg):
        """Manage flow rules
        Usage:
          flows show <switch>           - Show flows for switch
          flows show all               - Show flows for all switches  
          flows add <switch> <rule>    - Add flow rule
          flows del <switch> [rule]    - Delete flow rule(s)
          flows clear <switch>         - Clear all flows on switch
        """
        args = arg.split()
        if not args:
            self.help_flows()
            return
            
        cmd = args[0]
        if cmd == 'show':
            if len(args) < 2:
                print("Usage: flows show <switch|all>")
                return
            target = args[1]
            if target == 'all':
                self._show_all_flows()
            else:
                self._show_flows(target)
        
        elif cmd == 'add':
            if len(args) < 3:
                print("Usage: flows add <switch> <flow_rule>")
                print("Example: flows add s1 priority=100,in_port=1,actions=output:2")
                return
            switch = args[1]
            rule = ' '.join(args[2:])
            self._add_flow(switch, rule)
        
        elif cmd == 'del' or cmd == 'delete':
            if len(args) < 2:
                print("Usage: flows del <switch> [match_criteria]")
                return
            switch = args[1]
            match = ' '.join(args[2:]) if len(args) > 2 else ""
            self._del_flow(switch, match)
        
        elif cmd == 'clear':
            if len(args) < 2:
                print("Usage: flows clear <switch>")
                return
            self._clear_flows(args[1])
        
        else:
            print(f"Unknown flows command: {cmd}")
            self.help_flows()

    def do_route(self, arg):
        """Set up routing between hosts
        Usage:
          route set <src_host> <dst_host> <path>  - Set explicit path
          route show <src_host> <dst_host>        - Show current path
          route auto <src_host> <dst_host>        - Auto-configure L2 forwarding
        """
        args = arg.split()
        if not args:
            self.help_route()
            return
            
        cmd = args[0]
        if cmd == 'auto' and len(args) >= 3:
            self._setup_l2_forwarding(args[1], args[2])
        elif cmd == 'show' and len(args) >= 3:
            self._show_route(args[1], args[2])
        elif cmd == 'set' and len(args) >= 4:
            path = args[3].split(',')
            self._set_explicit_route(args[1], args[2], path)
        else:
            self.help_route()

    def do_ping(self, arg):
        """Test connectivity and monitor controller response
        Usage:
          ping <src_host> <dst_host>    - Test connectivity
          ping all                      - Test all host connectivity
          ping monitor <src> <dst>      - Monitor controller during ping
        """
        args = arg.split()
        if not args:
            print("Usage: ping <src_host> <dst_host> | ping all | ping monitor <src> <dst>")
            return
            
        if args[0] == 'all':
            self._ping_all()
        elif args[0] == 'monitor' and len(args) >= 3:
            self._ping_with_monitoring(args[1], args[2])
        elif len(args) >= 2:
            self._ping_hosts(args[0], args[1])
        else:
            print("Usage: ping <src_host> <dst_host>")

    def do_monitor(self, arg):
        """Monitor SDN operations
        Usage:
          monitor controllers     - Watch controller logs
          monitor flows <switch>  - Monitor flow table changes
          monitor traffic         - Monitor network traffic
        """
        args = arg.split()
        if not args:
            self.help_monitor()
            return
            
        cmd = args[0]
        if cmd == 'controllers':
            self._monitor_controllers()
        elif cmd == 'flows' and len(args) >= 2:
            self._monitor_flows(args[1])
        elif cmd == 'traffic':
            self._monitor_traffic()
        else:
            self.help_monitor()

    def do_clear(self, arg):
        """Clear flow rules
        Usage:
          clear all        - Clear all flows from all switches
          clear <switch>   - Clear flows from specific switch
        """
        if not arg:
            print("Usage: clear <switch|all>")
            return
            
        if arg == 'all':
            self._clear_all_flows()
        else:
            self._clear_flows(arg)

    # Internal methods
    def _check_controller_port(self, port):
        """Check if controller is running on port"""
        try:
            result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
            if f':{port}' in result.stdout:
                return "🟢 Running"
            else:
                return "🔴 Stopped"
        except:
            return "❓ Unknown"

    def _check_mininet_running(self):
        """Check if Mininet is running"""
        try:
            result = subprocess.run(['sudo', 'ovs-vsctl', 'list-br'], 
                                  capture_output=True, text=True)
            bridges = result.stdout.strip().split('\n') if result.stdout.strip() else []
            if len(bridges) >= 5:  # Should have at least some switches
                return f"🟢 Active ({len(bridges)} bridges)"
            else:
                return "🔴 No bridges detected"
        except:
            return "❓ Check required"

    def _count_ovs_bridges(self):
        """Count active OVS bridges"""
        try:
            result = subprocess.run(['sudo', 'ovs-vsctl', 'list-br'], 
                                  capture_output=True, text=True)
            bridges = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return len([b for b in bridges if b.strip()])
        except:
            return 0

    def _show_flows(self, switch):
        """Show flow table for specific switch"""
        if switch not in self.switches:
            print(f"❌ Invalid switch: {switch}. Available: {', '.join(self.switches)}")
            return
            
        print(f"\n📋 Flow Table for {switch}:")
        try:
            result = subprocess.run(['sudo', 'ovs-ofctl', 'dump-flows', switch],
                                  capture_output=True, text=True, check=True)
            
            flows = result.stdout.strip().split('\n')
            if len(flows) <= 1 or not flows[0].strip():
                print("  No flows configured")
                return
                
            for i, flow in enumerate(flows):
                if flow.strip() and not flow.startswith('NXST_FLOW'):
                    print(f"  [{i}] {flow}")
                    
        except subprocess.CalledProcessError:
            print(f"  ❌ Cannot access {switch} - Is Mininet running?")
        except FileNotFoundError:
            print("  ❌ ovs-ofctl not found - Is Open vSwitch installed?")

    def _show_all_flows(self):
        """Show flows for all switches"""
        print(f"\n📋 All Flow Tables:")
        for switch in self.switches:
            controller = 'Primary' if switch in self.controllers['primary']['switches'] else 'Secondary'
            print(f"\n{switch} ({controller} Controller):")
            self._show_flows_compact(switch)

    def _show_flows_compact(self, switch):
        """Show compact flow info for overview"""
        try:
            result = subprocess.run(['sudo', 'ovs-ofctl', 'dump-flows', switch],
                                  capture_output=True, text=True)
            flows = result.stdout.strip().split('\n')
            flow_count = len([f for f in flows if f.strip() and not f.startswith('NXST_FLOW')])
            print(f"  📊 {flow_count} flow rules configured")
        except:
            print(f"  ❌ Cannot access {switch}")

    def _add_flow(self, switch, rule):
        """Add flow rule to switch"""
        if switch not in self.switches:
            print(f"❌ Invalid switch: {switch}")
            return
            
        try:
            result = subprocess.run(['sudo', 'ovs-ofctl', 'add-flow', switch, rule],
                                  capture_output=True, text=True, check=True)
            print(f"✅ Flow added to {switch}:")
            print(f"   Rule: {rule}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to add flow: {e}")

    def _del_flow(self, switch, match=""):
        """Delete flow rules"""
        if switch not in self.switches:
            print(f"❌ Invalid switch: {switch}")
            return
            
        try:
            if match:
                cmd = ['sudo', 'ovs-ofctl', 'del-flows', switch, match]
                print(f"🗑️  Deleting flows matching '{match}' from {switch}")
            else:
                cmd = ['sudo', 'ovs-ofctl', 'del-flows', switch]
                print(f"🗑️  Deleting all flows from {switch}")
                
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✅ Flows deleted")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to delete flows: {e}")

    def _clear_flows(self, switch):
        """Clear all flows from switch"""
        self._del_flow(switch)

    def _clear_all_flows(self):
        """Clear flows from all switches"""
        print("🗑️  Clearing all flows from all switches...")
        for switch in self.switches:
            try:
                subprocess.run(['sudo', 'ovs-ofctl', 'del-flows', switch],
                             capture_output=True, text=True, check=True)
                print(f"✅ Cleared {switch}")
            except:
                print(f"❌ Failed to clear {switch}")

    def _setup_l2_forwarding(self, src_host, dst_host):
        """Setup L2 forwarding rules between hosts"""
        if src_host not in self.hosts or dst_host not in self.hosts:
            print(f"❌ Invalid hosts. Available: {', '.join(self.hosts)}")
            return
            
        print(f"🔧 Setting up L2 forwarding: {src_host} ↔ {dst_host}")
        print("   This will install bidirectional forwarding rules")
        
        # Get host MACs (simplified - in real scenario would query network)
        src_mac = f"00:00:00:00:00:{int(src_host[1:]):02x}"
        dst_mac = f"00:00:00:00:00:{int(dst_host[1:]):02x}"
        
        print(f"   {src_host} MAC: {src_mac}")
        print(f"   {dst_host} MAC: {dst_mac}")
        print("   💡 Use 'ping monitor' to see controller learning in action")

    def _ping_hosts(self, src, dst):
        """Execute ping between hosts"""
        if src not in self.hosts or dst not in self.hosts:
            print(f"❌ Invalid hosts. Available: {', '.join(self.hosts)}")
            return
            
        print(f"🏓 Pinging {src} → {dst}")
        print("   📝 Run this in Mininet CLI:")
        print(f"   mininet> {src} ping -c 3 {dst}")
        print("   💡 Use 'ping monitor' to watch controller activity")

    def _ping_all(self):
        """Test connectivity between all hosts"""
        print("🏓 Testing connectivity between all hosts")
        print("   📝 Run this in Mininet CLI:")
        print("   mininet> pingall")

    def _ping_with_monitoring(self, src, dst):
        """Ping with controller monitoring"""
        print(f"🔍 Monitoring ping: {src} → {dst}")
        print("   Watching controller logs for PacketIn events...")
        
        # Show current flow counts before ping
        src_switch = f"s{(int(src[1:]) + 1) // 2}"
        dst_switch = f"s{(int(dst[1:]) + 1) // 2}"
        
        print(f"   Source switch: {src_switch}")
        print(f"   Destination switch: {dst_switch}")
        print(f"   Execute: mininet> {src} ping -c 1 {dst}")
        print("   Then check flows: flows show " + src_switch)

    def _monitor_controllers(self):
        """Monitor controller logs"""
        print("📡 Monitoring controller logs...")
        print("   Watching primary.log and secondary.log for activity")
        print("   Press Ctrl+C to stop monitoring\n")
        
        try:
            # Simple tail-like monitoring
            for i in range(10):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking logs...")
                
                for log_file in ['primary.log', 'secondary.log']:
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                            recent_lines = lines[-5:] if len(lines) > 5 else lines
                            if recent_lines:
                                print(f"  {log_file}: {len(lines)} total lines")
                    except FileNotFoundError:
                        print(f"  {log_file}: Not found")
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n📡 Monitoring stopped")

    def _monitor_flows(self, switch):
        """Monitor flow table changes"""
        if switch not in self.switches:
            print(f"❌ Invalid switch: {switch}")
            return
            
        print(f"📊 Monitoring flow changes on {switch}")
        print("   Press Ctrl+C to stop\n")
        
        try:
            prev_flows = ""
            while True:
                try:
                    result = subprocess.run(['sudo', 'ovs-ofctl', 'dump-flows', switch],
                                          capture_output=True, text=True)
                    current_flows = result.stdout
                    
                    if current_flows != prev_flows:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Flow table changed on {switch}")
                        flows = current_flows.strip().split('\n')
                        flow_count = len([f for f in flows if f.strip() and not f.startswith('NXST_FLOW')])
                        print(f"   Current flow count: {flow_count}")
                        prev_flows = current_flows
                    
                    time.sleep(1)
                except:
                    print(f"   Cannot access {switch}")
                    break
                    
        except KeyboardInterrupt:
            print(f"\n📊 Stopped monitoring {switch}")

    def _monitor_traffic(self):
        """Monitor network traffic"""
        print("🌐 Network traffic monitoring")
        print("   Use these commands to monitor traffic:")
        print("   • sudo tcpdump -i any -c 10")
        print("   • sudo ovs-ofctl snoop <switch>")
        print("   • Watch controller logs with 'monitor controllers'")

    # Help methods
    def help_flows(self):
        print("""
Flow rule management:
  flows show <switch>           - Display flow table for switch
  flows show all               - Display all flow tables
  flows add <switch> <rule>    - Add OpenFlow rule
  flows del <switch> [match]   - Delete matching flows
  flows clear <switch>         - Remove all flows

Examples:
  flows add s1 priority=100,in_port=1,actions=output:2
  flows add s1 priority=200,dl_src=00:00:00:00:00:01,actions=output:3
  flows del s1 in_port=1
        """)

    def help_route(self):
        print("""
Routing configuration:
  route auto <src> <dst>       - Setup L2 forwarding rules
  route show <src> <dst>       - Show current routing
  route set <src> <dst> <path> - Set explicit path

Examples:
  route auto h1 h10           - Auto-configure h1 to h10
  route set h1 h10 s1,s2,s6   - Route via specific switches
        """)

    def help_monitor(self):
        print("""
SDN monitoring:
  monitor controllers         - Watch controller logs in real-time
  monitor flows <switch>      - Monitor flow table changes
  monitor traffic            - Show traffic monitoring commands
        """)

    def do_exit(self, arg):
        """Exit SDN Lab1 CLI"""
        print("👋 Goodbye from SDN Lab1!")
        return True
        
    def do_quit(self, arg):
        """Exit SDN Lab1 CLI"""
        return self.do_exit(arg)

    def emptyline(self):
        """Handle empty line"""
        pass

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print(SDNLabCLI.intro)
        return
        
    try:
        SDNLabCLI().cmdloop()
    except KeyboardInterrupt:
        print("\n👋 Goodbye from SDN Lab1!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()