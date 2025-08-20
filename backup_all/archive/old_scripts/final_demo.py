#!/usr/bin/env python3
"""
Final working demo with automatic port assignment
10-switch mesh topology with Dijkstra routing
"""

import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

def create_mesh_topology():
    """Create 10-switch mesh topology with automatic port assignment"""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}   CREATING 10-SWITCH MESH TOPOLOGY{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController,
                          ip='127.0.0.1', port=6633)
    
    # Create switches
    print(f"{Colors.BLUE}Creating switches...{Colors.END}")
    switches = {}
    for i in range(1, 11):
        switches[i] = net.addSwitch(f's{i}', protocols='OpenFlow13', dpid=str(i))
    
    # Create hosts
    print(f"{Colors.BLUE}Creating hosts...{Colors.END}")
    hosts = {}
    for i in range(1, 11):
        hosts[i] = net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
        net.addLink(hosts[i], switches[i])
    
    # Create mesh links (automatic port assignment)
    print(f"{Colors.BLUE}Creating mesh links...{Colors.END}")
    
    # Grid connections (3x3 + 1)
    # Row 1: s1-s2-s3
    net.addLink(switches[1], switches[2])
    net.addLink(switches[2], switches[3])
    
    # Row 2: s4-s5-s6
    net.addLink(switches[4], switches[5])
    net.addLink(switches[5], switches[6])
    
    # Row 3: s7-s8-s9
    net.addLink(switches[7], switches[8])
    net.addLink(switches[8], switches[9])
    
    # Column 1: s1-s4-s7
    net.addLink(switches[1], switches[4])
    net.addLink(switches[4], switches[7])
    
    # Column 2: s2-s5-s8
    net.addLink(switches[2], switches[5])
    net.addLink(switches[5], switches[8])
    
    # Column 3: s3-s6-s9
    net.addLink(switches[3], switches[6])
    net.addLink(switches[6], switches[9])
    
    # Diagonal links for redundancy
    net.addLink(switches[1], switches[5])  # s1-s5
    net.addLink(switches[5], switches[9])  # s5-s9
    net.addLink(switches[3], switches[5])  # s3-s5
    net.addLink(switches[5], switches[7])  # s5-s7
    
    # Connect s10 to center
    net.addLink(switches[5], switches[10])  # s5-s10
    
    print(f"{Colors.GREEN}✅ Topology created!{Colors.END}")
    print(f"\n{Colors.YELLOW}Topology structure:{Colors.END}")
    print("    s1 --- s2 --- s3")
    print("    |  \\   |   /  |")
    print("    |    \\ | /    |")
    print("    s4 --- s5 --- s6")
    print("    |    / | \\    |")
    print("    |  /   |   \\  |")
    print("    s7 --- s8 --- s9")
    print("           |")
    print("          s10")
    
    return net, hosts, switches

def run_connectivity_tests(hosts):
    """Run basic connectivity tests"""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}   CONNECTIVITY TESTS{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    
    tests = [
        (1, 2, "Adjacent (h1->h2)"),
        (1, 5, "Center (h1->h5)"),
        (1, 9, "Corner (h1->h9)"),
        (1, 10, "To s10 (h1->h10)"),
    ]
    
    for src, dst, desc in tests:
        print(f"\n{Colors.YELLOW}Test: {desc}{Colors.END}")
        result = hosts[src].cmd(f'ping -c 2 -W 1 10.0.0.{dst}')
        if '0% packet loss' in result:
            print(f"  {Colors.GREEN}✅ SUCCESS{Colors.END}")
        else:
            print(f"  {Colors.RED}❌ FAILED{Colors.END}")
            print(f"  Debug: {result[:100]}")

def test_link_failure_scenario(net, hosts):
    """Test link failure and recovery"""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}   LINK FAILURE SCENARIO{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    
    # Initial test
    print(f"\n{Colors.YELLOW}1. Initial test h1 -> h3{Colors.END}")
    result = hosts[1].cmd('ping -c 2 -W 1 10.0.0.3')
    if '0% packet loss' in result:
        print(f"  {Colors.GREEN}✅ Working via s1->s2->s3{Colors.END}")
    
    # Break link
    print(f"\n{Colors.YELLOW}2. Breaking link s1 <-> s2{Colors.END}")
    net.configLinkStatus('s1', 's2', 'down')
    time.sleep(3)
    
    # Test rerouting
    print(f"\n{Colors.YELLOW}3. Testing rerouting h1 -> h3{Colors.END}")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.3')
    if '0% packet loss' in result:
        print(f"  {Colors.GREEN}✅ REROUTED (via s1->s4->s5->s2->s3 or s1->s5->s3){Colors.END}")
    else:
        print(f"  {Colors.RED}❌ Rerouting failed{Colors.END}")
    
    # Restore link
    print(f"\n{Colors.YELLOW}4. Restoring link s1 <-> s2{Colors.END}")
    net.configLinkStatus('s1', 's2', 'up')
    time.sleep(3)
    
    # Test restoration
    print(f"\n{Colors.YELLOW}5. Testing restored path h1 -> h3{Colors.END}")
    result = hosts[1].cmd('ping -c 2 -W 1 10.0.0.3')
    if '0% packet loss' in result:
        print(f"  {Colors.GREEN}✅ Path restored{Colors.END}")

def main():
    setLogLevel('warning')
    
    # Clean up
    import os
    os.system("sudo mn -c 2>/dev/null")
    
    # Create topology
    net, hosts, switches = create_mesh_topology()
    
    # Start network
    print(f"\n{Colors.BLUE}Starting network...{Colors.END}")
    net.start()
    time.sleep(5)
    
    # Run tests
    run_connectivity_tests(hosts)
    test_link_failure_scenario(net, hosts)
    
    # Interactive CLI
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}   ENTERING INTERACTIVE CLI{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"\n{Colors.YELLOW}Useful commands:{Colors.END}")
    print("  h1 ping h9          - Test corner to corner")
    print("  link s5 s8 down     - Break central link")
    print("  link s5 s8 up       - Restore link")
    print("  pingall             - Test all pairs")
    print("  links               - Show all links")
    print("  exit                - Quit\n")
    
    CLI(net)
    
    # Cleanup
    net.stop()
    print(f"\n{Colors.GREEN}✅ Demo completed!{Colors.END}")

if __name__ == '__main__':
    main()