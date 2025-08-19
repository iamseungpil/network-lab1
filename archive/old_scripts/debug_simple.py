#!/usr/bin/env python3
"""
Simple debug topology - 4 switches, 4 hosts
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

def create_debug_topology():
    """Create simple 4-switch topology for debugging"""
    
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    
    info("*** Creating Debug Topology: 4 switches, 4 hosts\n")
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    # Add 4 switches
    s1 = net.addSwitch('s1', dpid='0000000000000001')
    s2 = net.addSwitch('s2', dpid='0000000000000002')  
    s3 = net.addSwitch('s3', dpid='0000000000000003')
    s4 = net.addSwitch('s4', dpid='0000000000000004')
    
    # Add 4 hosts
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4', mac='00:00:00:00:00:04')
    
    # Connect hosts to switches
    net.addLink(h1, s1, port1=1, port2=1)
    net.addLink(h2, s2, port1=1, port2=1)
    net.addLink(h3, s3, port1=1, port2=1)
    net.addLink(h4, s4, port1=1, port2=1)
    
    # Create diamond topology between switches
    net.addLink(s1, s2, port1=2, port2=2)  # s1-s2
    net.addLink(s1, s3, port1=3, port2=2)  # s1-s3
    net.addLink(s2, s4, port1=3, port2=2)  # s2-s4
    net.addLink(s3, s4, port1=3, port2=3)  # s3-s4
    
    info("*** Links created:\n")
    info("  h1 - s1 - s2 - h2\n")
    info("  h1 - s1 - s3 - h3\n") 
    info("  Connections: s1-s2, s1-s3, s2-s4, s3-s4\n")
    
    return net, [h1, h2, h3, h4], [s1, s2, s3, s4]

def debug_connectivity(net, hosts):
    """Debug connectivity step by step"""
    info("\n*** DEBUGGING CONNECTIVITY ***\n")
    
    # Test same switch (should fail since no same switch pairs)
    info("1. Testing adjacent switches h1 -> h2 (s1 -> s2):\n")
    result = hosts[0].cmd('ping -c 2 -W 2 10.0.0.2')
    info(f"Result: {result}\n")
    
    info("2. Testing h1 -> h3 (s1 -> s3):\n") 
    result = hosts[0].cmd('ping -c 2 -W 2 10.0.0.3')
    info(f"Result: {result}\n")
    
    info("3. Testing ARP table on h1:\n")
    result = hosts[0].cmd('arp -a')
    info(f"ARP: {result}\n")
    
    info("4. Testing routes on h1:\n")
    result = hosts[0].cmd('route -n')
    info(f"Routes: {result}\n")

def main():
    setLogLevel('info')
    
    info("\n" + "="*60 + "\n")
    info("🐛 DEBUG SESSION - SIMPLE TOPOLOGY\n")
    info("="*60 + "\n")
    
    net, hosts, switches = create_debug_topology()
    
    info("*** Starting network\n")
    net.start()
    
    info("*** Waiting for controller connection...\n")
    import time
    time.sleep(8)
    
    debug_connectivity(net, hosts)
    
    info("\n*** Starting CLI for manual testing\n")
    info("Try: h1 ping h2, h1 ping h3\n")
    CLI(net)
    
    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    main()