#!/usr/bin/env python3
"""
Unified test script using exact topology from topology_config.py
"""

import time
import sys
import os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

# Import topology configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from topology_config import get_topology_links, get_host_connections, TOPOLOGY_DIAGRAM

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def create_topology():
    """Create the exact topology from configuration"""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}   CREATING 10-SWITCH TOPOLOGY{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    # Add controller
    print(f"{Colors.BLUE}Adding controller...{Colors.END}")
    c0 = net.addController('c0', controller=RemoteController,
                          ip='127.0.0.1', port=6633)
    
    # Create switches
    print(f"{Colors.BLUE}Creating 10 switches...{Colors.END}")
    switches = {}
    for i in range(1, 11):
        switches[i] = net.addSwitch(f's{i}', protocols='OpenFlow13', dpid=str(i))
    
    # Create hosts
    print(f"{Colors.BLUE}Creating 10 hosts...{Colors.END}")
    hosts = {}
    host_connections = get_host_connections()
    for sw_id, port in host_connections:
        hosts[sw_id] = net.addHost(f'h{sw_id}', ip=f'10.0.0.{sw_id}/24')
        net.addLink(hosts[sw_id], switches[sw_id], port1=0, port2=port)
        print(f"  h{sw_id} -> s{sw_id}:p{port}")
    
    # Create switch interconnections
    print(f"{Colors.BLUE}Creating switch links...{Colors.END}")
    links = get_topology_links()
    for sw1, sw2, port1, port2 in links:
        net.addLink(switches[sw1], switches[sw2], port1=port1, port2=port2)
        print(f"  s{sw1}:p{port1} <--> s{sw2}:p{port2}")
    
    print(f"{Colors.GREEN}✅ Topology created successfully!{Colors.END}")
    return net, hosts, switches

def test_basic_connectivity(hosts):
    """Test basic connectivity between hosts"""
    print(f"\n{Colors.YELLOW}📍 TEST: Basic Connectivity{Colors.END}")
    
    tests = [
        (1, 2, "Adjacent switches"),
        (1, 10, "To central s10"),
        (1, 9, "Corner to corner"),
    ]
    
    results = []
    for h1_id, h2_id, desc in tests:
        print(f"  Testing h{h1_id} -> h{h2_id} ({desc})...", end=' ')
        result = hosts[h1_id].cmd(f'ping -c 2 -W 1 10.0.0.{h2_id}')
        if '0% packet loss' in result:
            print(f"{Colors.GREEN}✅ SUCCESS{Colors.END}")
            results.append(True)
        else:
            print(f"{Colors.RED}❌ FAILED{Colors.END}")
            results.append(False)
    
    return all(results)

def test_link_failure(net, hosts):
    """Test link failure and rerouting"""
    print(f"\n{Colors.YELLOW}📍 TEST: Link Failure and Rerouting{Colors.END}")
    
    # Test initial path
    print(f"  Initial test h1 -> h3...", end=' ')
    result = hosts[1].cmd('ping -c 2 -W 1 10.0.0.3')
    initial = '0% packet loss' in result
    print(f"{Colors.GREEN if initial else Colors.RED}{'✅' if initial else '❌'}{Colors.END}")
    
    # Break link s1-s2
    print(f"  {Colors.RED}Breaking link s1 <-> s2...{Colors.END}")
    net.configLinkStatus('s1', 's2', 'down')
    time.sleep(3)
    
    # Test rerouting
    print(f"  Testing rerouting h1 -> h3...", end=' ')
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.3')
    rerouted = '0% packet loss' in result
    print(f"{Colors.GREEN if rerouted else Colors.RED}{'✅ REROUTED' if rerouted else '❌ NO PATH'}{Colors.END}")
    
    # Restore link
    print(f"  {Colors.GREEN}Restoring link s1 <-> s2...{Colors.END}")
    net.configLinkStatus('s1', 's2', 'up')
    time.sleep(3)
    
    # Test restoration
    print(f"  Testing restored path h1 -> h3...", end=' ')
    result = hosts[1].cmd('ping -c 2 -W 1 10.0.0.3')
    restored = '0% packet loss' in result
    print(f"{Colors.GREEN if restored else Colors.RED}{'✅' if restored else '❌'}{Colors.END}")
    
    return initial and rerouted and restored

def test_multiple_failures(net, hosts):
    """Test multiple link failures"""
    print(f"\n{Colors.YELLOW}📍 TEST: Multiple Link Failures{Colors.END}")
    
    # Initial test
    print(f"  Initial test h1 -> h9...", end=' ')
    result = hosts[1].cmd('ping -c 2 -W 1 10.0.0.9')
    initial = '0% packet loss' in result
    print(f"{Colors.GREEN if initial else Colors.RED}{'✅' if initial else '❌'}{Colors.END}")
    
    # Break multiple links
    links_to_break = [('s1', 's2'), ('s1', 's4'), ('s2', 's5')]
    print(f"  {Colors.RED}Breaking multiple links:{Colors.END}")
    for s1, s2 in links_to_break:
        print(f"    - {s1} <-> {s2}")
        net.configLinkStatus(s1, s2, 'down')
    time.sleep(4)
    
    # Test with multiple failures
    print(f"  Testing with failures h1 -> h9...", end=' ')
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.9')
    multi_route = '0% packet loss' in result
    print(f"{Colors.GREEN if multi_route else Colors.RED}{'✅ REROUTED' if multi_route else '❌'}{Colors.END}")
    
    # Restore all links
    print(f"  {Colors.GREEN}Restoring all links...{Colors.END}")
    for s1, s2 in links_to_break:
        net.configLinkStatus(s1, s2, 'up')
    time.sleep(3)
    
    return initial and multi_route

def main():
    setLogLevel('warning')
    
    # Clean up
    os.system("sudo mn -c 2>/dev/null")
    
    # Create topology
    net, hosts, switches = create_topology()
    
    # Start network
    print(f"\n{Colors.BLUE}Starting network...{Colors.END}")
    net.start()
    time.sleep(5)
    
    # Show topology diagram
    print(TOPOLOGY_DIAGRAM)
    
    # Run tests
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}   RUNNING AUTOMATED TESTS{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    
    test_results = []
    
    # Test 1: Basic connectivity
    test_results.append(test_basic_connectivity(hosts))
    
    # Test 2: Link failure
    test_results.append(test_link_failure(net, hosts))
    
    # Test 3: Multiple failures
    test_results.append(test_multiple_failures(net, hosts))
    
    # Summary
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}   TEST SUMMARY{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"  Basic Connectivity: {Colors.GREEN if test_results[0] else Colors.RED}{'PASS' if test_results[0] else 'FAIL'}{Colors.END}")
    print(f"  Link Failure/Recovery: {Colors.GREEN if test_results[1] else Colors.RED}{'PASS' if test_results[1] else 'FAIL'}{Colors.END}")
    print(f"  Multiple Failures: {Colors.GREEN if test_results[2] else Colors.RED}{'PASS' if test_results[2] else 'FAIL'}{Colors.END}")
    
    print(f"\n  Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n{Colors.GREEN}🎉 ALL TESTS PASSED!{Colors.END}")
    
    # Enter CLI for manual testing
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}   ENTERING MININET CLI{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"\nUseful commands:")
    print(f"  h1 ping h9        - Test corner to corner")
    print(f"  link s5 s8 down   - Break a central link")
    print(f"  pingall           - Test all connectivity")
    print(f"  exit              - Quit\n")
    
    CLI(net)
    
    # Cleanup
    net.stop()
    print(f"\n{Colors.GREEN}✅ Test completed!{Colors.END}")

if __name__ == '__main__':
    main()