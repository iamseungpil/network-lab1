#!/usr/bin/env python3
"""
Check actual Mininet topology - especially loop
"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def check_topology():
    print("\n=== TOPOLOGY CHECK ===\n")
    
    # Create network WITHOUT controller to see pure topology
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    print("[1] Creating switches...")
    # Create 5 switches for primary domain
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    s4 = net.addSwitch('s4')
    s5 = net.addSwitch('s5')
    
    print("[2] Creating hosts...")
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    h5 = net.addHost('h5', ip='10.0.0.5/24')
    
    print("[3] Creating links...")
    print("   Host connections:")
    net.addLink(h1, s1)
    print("   - h1 <-> s1")
    net.addLink(h2, s1)
    print("   - h2 <-> s1")
    net.addLink(h3, s3)
    print("   - h3 <-> s3")
    net.addLink(h4, s4)
    print("   - h4 <-> s4")
    net.addLink(h5, s5)
    print("   - h5 <-> s5")
    
    print("\n   Switch connections (PRIMARY PATHS):")
    l1 = net.addLink(s1, s2)
    print(f"   - s1 <-> s2: {l1}")
    l2 = net.addLink(s1, s3)
    print(f"   - s1 <-> s3: {l2}")
    l3 = net.addLink(s2, s4)
    print(f"   - s2 <-> s4: {l3}")
    l4 = net.addLink(s2, s5)
    print(f"   - s2 <-> s5: {l4}")
    
    print("\n   LOOP LINK (BACKUP PATH):")
    l5 = net.addLink(s4, s3)
    print(f"   - s4 <-> s3: {l5} [THIS CREATES THE LOOP!]")
    
    print("\n[4] Starting network...")
    net.start()
    
    print("\n=== VERIFICATION ===\n")
    
    # Check links
    print("Links in network:")
    for link in net.links:
        print(f"  {link}")
    
    print("\nSwitch connections:")
    for switch in [s1, s2, s3, s4, s5]:
        ports = switch.ports
        connections = []
        for port in ports.values():
            if port.link:
                other = port.link.intf1 if port.link.intf2 == port else port.link.intf2
                connections.append(str(other))
        print(f"  {switch.name}: {connections}")
    
    print("\n=== TOPOLOGY SUMMARY ===")
    print("Expected loop: s1 -> s2 -> s4 -> s3 -> s1")
    print("Alternative paths:")
    print("  - s1 to s3: Direct (s1-s3) OR via s2-s4 (s1-s2-s4-s3)")
    print("  - s1 to s4: Via s2 (s1-s2-s4) OR via s3 (s1-s3-s4)")
    
    print("\n=== MININET CLI ===")
    print("Commands to verify:")
    print("  mininet> net")
    print("  mininet> links")
    print("  mininet> dump")
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    check_topology()