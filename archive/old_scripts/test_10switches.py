#!/usr/bin/env python3
"""
10-Switch Topology Test with Link Failure Scenarios
"""

import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def create_10switch_topology():
    """Create the 10-switch mesh topology matching controller configuration"""
    print("\n" + "="*70)
    print(" CREATING 10-SWITCH MESH TOPOLOGY")
    print("="*70)
    
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Create 10 switches
    switches = {}
    for i in range(1, 11):
        switches[i] = net.addSwitch(f's{i}', protocols='OpenFlow13', dpid=str(i))
    
    # Add hosts (one per switch for testing)
    hosts = {}
    for i in range(1, 11):
        hosts[i] = net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
        net.addLink(hosts[i], switches[i], port1=0, port2=1)
    
    print("\n🔗 Creating switch interconnections...")
    
    # Row 1 connections (s1-s2-s3)
    net.addLink(switches[1], switches[2], port1=2, port2=2)  # s1:2 <-> s2:2
    net.addLink(switches[2], switches[3], port1=3, port2=2)  # s2:3 <-> s3:2
    
    # Row 2 connections (s4-s5-s6)
    net.addLink(switches[4], switches[5], port1=3, port2=2)  # s4:3 <-> s5:2
    net.addLink(switches[5], switches[6], port1=3, port2=2)  # s5:3 <-> s6:2
    
    # Row 3 connections (s7-s8-s9)
    net.addLink(switches[7], switches[8], port1=2, port2=2)  # s7:2 <-> s8:2
    net.addLink(switches[8], switches[9], port1=3, port2=2)  # s8:3 <-> s9:2
    
    # Vertical connections
    net.addLink(switches[1], switches[4], port1=4, port2=3)  # s1:4 <-> s4:3
    net.addLink(switches[2], switches[5], port1=4, port2=3)  # s2:4 <-> s5:3
    net.addLink(switches[3], switches[6], port1=4, port2=3)  # s3:4 <-> s6:3
    net.addLink(switches[4], switches[7], port1=5, port2=3)  # s4:5 <-> s7:3
    net.addLink(switches[5], switches[8], port1=5, port2=3)  # s5:5 <-> s8:3
    net.addLink(switches[6], switches[9], port1=5, port2=3)  # s6:5 <-> s9:3
    
    # Diagonal connections for redundancy
    net.addLink(switches[1], switches[5], port1=5, port2=4)  # s1:5 <-> s5:4
    net.addLink(switches[2], switches[4], port1=5, port2=4)  # s2:5 <-> s4:4
    net.addLink(switches[2], switches[6], port1=6, port2=4)  # s2:6 <-> s6:4
    net.addLink(switches[3], switches[5], port1=5, port2=6)  # s3:5 <-> s5:6
    net.addLink(switches[4], switches[8], port1=6, port2=4)  # s4:6 <-> s8:4
    net.addLink(switches[5], switches[7], port1=7, port2=4)  # s5:7 <-> s7:4
    net.addLink(switches[5], switches[9], port1=8, port2=4)  # s5:8 <-> s9:4
    net.addLink(switches[6], switches[8], port1=6, port2=5)  # s6:6 <-> s8:5
    
    # Connect s10 to s8
    net.addLink(switches[8], switches[10], port1=10, port2=2)  # s8:10 <-> s10:2
    
    print("✅ Topology created successfully!")
    
    return net, hosts

def run_test_scenario(net, hosts, scenario_name, test_func):
    """Run a test scenario with detailed output"""
    print("\n" + "="*70)
    print(f" SCENARIO: {scenario_name}")
    print("="*70)
    test_func(net, hosts)
    print("\n✅ Scenario completed")
    time.sleep(2)

def test_normal_routing(net, hosts):
    """Test normal routing without failures"""
    print("\n📍 TEST 1: Short path (h1 -> h2)")
    print("   Expected: Direct link s1 -> s2")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.2')
    print(f"   Result: {'✅ SUCCESS' if '0% packet loss' in result else '❌ FAILED'}")
    
    print("\n📍 TEST 2: Medium path (h1 -> h5)")
    print("   Expected: s1 -> s5 (diagonal) or s1 -> s2 -> s5")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.5')
    print(f"   Result: {'✅ SUCCESS' if '0% packet loss' in result else '❌ FAILED'}")
    
    print("\n📍 TEST 3: Long path (h1 -> h9)")
    print("   Expected: Multiple hops through mesh")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.9')
    print(f"   Result: {'✅ SUCCESS' if '0% packet loss' in result else '❌ FAILED'}")
    
    print("\n📍 TEST 4: To isolated switch (h1 -> h10)")
    print("   Expected: Path through s8")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.10')
    print(f"   Result: {'✅ SUCCESS' if '0% packet loss' in result else '❌ FAILED'}")

def test_single_link_failure(net, hosts):
    """Test single link failure and rerouting"""
    print("\n🔴 Breaking critical link: s1 <-> s2")
    net.configLinkStatus('s1', 's2', 'down')
    time.sleep(3)
    
    print("\n📍 TEST: h1 -> h2 after link failure")
    print("   Expected: Reroute via s1 -> s4 -> s2 or s1 -> s5 -> s2")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.2')
    print(f"   Result: {'✅ REROUTED' if '0% packet loss' in result else '❌ FAILED'}")
    
    print("\n🟢 Restoring link: s1 <-> s2")
    net.configLinkStatus('s1', 's2', 'up')
    time.sleep(3)
    
    print("\n📍 TEST: h1 -> h2 after restoration")
    print("   Expected: Back to direct path")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.2')
    print(f"   Result: {'✅ RESTORED' if '0% packet loss' in result else '❌ FAILED'}")

def test_multiple_link_failures(net, hosts):
    """Test multiple simultaneous link failures"""
    print("\n🔴 Breaking multiple links:")
    print("   - s1 <-> s2 (horizontal)")
    print("   - s1 <-> s4 (vertical)")
    net.configLinkStatus('s1', 's2', 'down')
    net.configLinkStatus('s1', 's4', 'down')
    time.sleep(3)
    
    print("\n📍 TEST: h1 -> h2 with 2 links down")
    print("   Expected: Reroute via diagonal s1 -> s5 -> s2")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.2')
    print(f"   Result: {'✅ REROUTED' if '0% packet loss' in result else '❌ FAILED'}")
    
    print("\n🔴 Breaking diagonal link too: s1 <-> s5")
    net.configLinkStatus('s1', 's5', 'down')
    time.sleep(3)
    
    print("\n📍 TEST: h1 -> h2 with all direct paths down")
    print("   Expected: No path - network partitioned")
    result = hosts[1].cmd('ping -c 3 -W 1 10.0.0.2')
    print(f"   Result: {'❌ ISOLATED (expected)' if '100% packet loss' in result else '⚠️ UNEXPECTED'}")
    
    print("\n🟢 Restoring all links")
    net.configLinkStatus('s1', 's2', 'up')
    net.configLinkStatus('s1', 's4', 'up')
    net.configLinkStatus('s1', 's5', 'up')
    time.sleep(3)

def test_cascading_failures(net, hosts):
    """Test cascading link failures"""
    print("\n📍 Initial test: h1 -> h9")
    result = hosts[1].cmd('ping -c 2 -W 1 10.0.0.9')
    print(f"   Initial: {'✅ OK' if '0% packet loss' in result else '❌ FAILED'}")
    
    links_to_fail = [
        ('s5', 's8', "Central vertical link"),
        ('s5', 's9', "Diagonal to s9"),
        ('s6', 's9', "Vertical to s9")
    ]
    
    for s1, s2, desc in links_to_fail:
        print(f"\n🔴 Breaking: {s1} <-> {s2} ({desc})")
        net.configLinkStatus(s1, s2, 'down')
        time.sleep(3)
        
        result = hosts[1].cmd('ping -c 2 -W 1 10.0.0.9')
        status = '✅ Still connected' if '0% packet loss' in result else '❌ Lost connection'
        print(f"   h1 -> h9: {status}")
    
    print("\n🟢 Restoring all failed links")
    for s1, s2, _ in links_to_fail:
        net.configLinkStatus(s1, s2, 'up')
    time.sleep(3)

def main():
    setLogLevel('warning')
    
    # Clean up first
    print("🧹 Cleaning up previous sessions...")
    import os
    os.system("sudo mn -c 2>/dev/null")
    
    # Create topology
    net, hosts = create_10switch_topology()
    
    print("\n⏳ Starting network...")
    net.start()
    time.sleep(5)
    
    # Run test scenarios
    scenarios = [
        ("Normal Routing", test_normal_routing),
        ("Single Link Failure", test_single_link_failure),
        ("Multiple Link Failures", test_multiple_link_failures),
        ("Cascading Failures", test_cascading_failures)
    ]
    
    for name, test_func in scenarios:
        run_test_scenario(net, hosts, name, test_func)
    
    print("\n" + "="*70)
    print(" ENTERING INTERACTIVE CLI")
    print("="*70)
    print("\n💡 Useful commands:")
    print("   link s1 s2 down    - Break a link")
    print("   link s1 s2 up      - Restore a link")
    print("   h1 ping h9         - Test connectivity")
    print("   links              - Show all links")
    print("   nodes              - Show all nodes")
    print("   exit               - Quit")
    print("")
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()