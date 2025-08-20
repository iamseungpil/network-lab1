#!/usr/bin/env python3
"""
Verify loop topology exists and test STP
"""

from mininet.net import Mininet
from mininet.node import OVSSwitch, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
import time

def verify_loop():
    print("\n" + "="*60)
    print("  LOOP TOPOLOGY VERIFICATION")
    print("="*60)
    
    # Create network
    net = Mininet(controller=Controller, switch=OVSSwitch)
    
    # Add switches
    print("\n[1] Creating diamond topology with loop...")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    s4 = net.addSwitch('s4')
    
    # Add hosts at endpoints
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    
    # Connect hosts
    net.addLink(h1, s1)
    net.addLink(h4, s4)
    
    # Create diamond/loop topology
    print("\n[2] Creating links (diamond with loop):")
    print("     h1")
    print("      |")
    print("     s1")
    print("    /  \\")
    print("   s2  s3")
    print("    \\  /")
    print("     s4")
    print("      |")
    print("     h4")
    
    l1 = net.addLink(s1, s2)
    print(f"   Link 1: s1 <-> s2")
    
    l2 = net.addLink(s1, s3)
    print(f"   Link 2: s1 <-> s3")
    
    l3 = net.addLink(s2, s4)
    print(f"   Link 3: s2 <-> s4")
    
    l4 = net.addLink(s3, s4)
    print(f"   Link 4: s3 <-> s4")
    
    print("\n   => LOOP EXISTS: s1->s2->s4->s3->s1")
    
    print("\n[3] Starting network...")
    net.start()
    
    print("\n[4] Testing connectivity with loop present...")
    
    # Let network stabilize
    time.sleep(2)
    
    # Test ping
    print("\n   Testing h1 ping h4 (with loop):")
    result = h1.cmd('ping -c 3 -W 1 10.0.0.4')
    if "Destination Host Unreachable" in result:
        print("   ✗ BROADCAST STORM or NO CONTROLLER")
    elif "0% packet loss" in result:
        print("   ✓ CONTROLLER HANDLING LOOP")
    else:
        print(f"   Result: {result[:100]}...")
    
    print("\n[5] Checking switch flow tables...")
    for switch in [s1, s2, s3, s4]:
        flows = switch.cmd('ovs-ofctl dump-flows', switch.name)
        print(f"\n   {switch.name} flows:")
        # Show first line of flows
        first_flow = flows.split('\n')[1] if len(flows.split('\n')) > 1 else "No flows"
        print(f"   {first_flow[:80]}...")
    
    print("\n" + "="*60)
    print("  MININET CLI - Manual Testing")
    print("  Try these commands:")
    print("    mininet> links        # See all links")
    print("    mininet> h1 ping h4   # Test with loop")
    print("    mininet> link s2 s4 down  # Break one path")
    print("    mininet> h1 ping h4   # Test alternate path")
    print("="*60)
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    verify_loop()