#!/usr/bin/env python3
"""
Simple Ring Topology: 10 Switches in a ring
Each switch has 1 host connected
Clean and simple for testing
"""

import sys
import argparse
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

def create_ring_topology(controller_port=6633):
    """Create a simple ring topology with 10 switches"""
    
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    
    info("*** Creating Ring Topology: 10 Switches, 10 Hosts\n")
    info("*** Simple ring structure for easier debugging\n\n")
    
    # Add controller
    c0 = net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=controller_port
    )
    
    # Add 10 switches
    info("*** Adding switches\n")
    switches = []
    for i in range(1, 11):
        sw = net.addSwitch(f's{i}', dpid=f'{i:016x}')
        switches.append(sw)
        info(f"  Added switch s{i}\n")
    
    # Add 10 hosts (1 per switch)
    info("\n*** Adding hosts (1 per switch)\n")
    hosts = []
    for i in range(1, 11):
        ip = f'10.0.0.{i}'
        mac = f'00:00:00:00:00:{i:02x}'
        h = net.addHost(f'h{i}', ip=ip, mac=mac)
        hosts.append(h)
        # Connect host to switch on port 1
        net.addLink(h, switches[i-1], port1=1, port2=1)
        info(f"  h{i} ({ip}) -> s{i} on port 1\n")
    
    # Create ring connections
    info("\n*** Creating ring topology\n")
    for i in range(10):
        s1 = switches[i]
        s2 = switches[(i + 1) % 10]
        # Use ports 2 and 3 for ring connections
        port1 = 2 if i < 9 else 3  # Last switch uses port 3 to connect to first
        port2 = 3 if i > 0 else 2   # First switch uses port 2 from last
        
        if i == 0:
            # First connection: s1 port 2 -> s2 port 3
            net.addLink(s1, s2, port1=2, port2=3)
            info(f"  s{i+1}:2 <-> s{i+2}:3\n")
        elif i == 9:
            # Last connection: s10 port 2 -> s1 port 3
            net.addLink(s1, s2, port1=2, port2=3)
            info(f"  s{i+1}:2 <-> s1:3\n")
        else:
            # Middle connections
            net.addLink(s1, s2, port1=2, port2=3)
            info(f"  s{i+1}:2 <-> s{i+2}:3\n")
    
    info("\n*** Ring topology created:\n")
    info("    s1 --- s2 --- s3 --- s4 --- s5\n")
    info("    |                           |\n")
    info("   s10                          s6\n")
    info("    |                           |\n")
    info("    s9 --- s8 --- s7 -----------\n")
    
    return net, hosts, switches

def test_ring_connectivity(net, hosts):
    """Test basic connectivity in ring topology"""
    info("\n*** Testing Ring Connectivity\n")
    
    # Test adjacent hosts
    info("  Testing adjacent hosts (h1 -> h2):\n")
    result = hosts[0].cmd(f'ping -c 3 -W 1 {hosts[1].IP()}')
    if '0% packet loss' in result:
        info("    ✅ Adjacent: Connected\n")
    else:
        info("    ❌ Adjacent: Failed\n")
    
    # Test opposite side of ring
    info("  Testing opposite side (h1 -> h6):\n")
    result = hosts[0].cmd(f'ping -c 3 -W 1 {hosts[5].IP()}')
    if '0% packet loss' in result:
        info("    ✅ Opposite: Connected\n")
    else:
        info("    ❌ Opposite: Failed\n")
    
    # Test far hosts
    info("  Testing far hosts (h1 -> h10):\n")
    result = hosts[0].cmd(f'ping -c 3 -W 1 {hosts[9].IP()}')
    if '0% packet loss' in result:
        info("    ✅ Far: Connected\n")
    else:
        info("    ❌ Far: Failed\n")

def main():
    parser = argparse.ArgumentParser(description='Ring topology with configurable controller port')
    parser.add_argument('--controller-port', type=int, default=6633, 
                       help='Controller port (default: 6633)')
    args = parser.parse_args()
    
    setLogLevel('info')
    
    info("\n" + "="*80 + "\n")
    info("🔄 RING TOPOLOGY: 10 SWITCHES\n")
    info(f"📡 Controller port: {args.controller_port}\n")
    info("="*80 + "\n")
    
    # Create topology
    net, hosts, switches = create_ring_topology(controller_port=args.controller_port)
    
    # Start network
    info("\n*** Starting network\n")
    net.start()
    
    info("\n*** Waiting for controller connection...\n")
    import time
    time.sleep(5)
    
    # Run basic tests
    test_ring_connectivity(net, hosts)
    
    # Show available commands
    info("\n*** Network ready!\n")
    info("*** Available hosts: h1-h10 (10.0.0.1 - 10.0.0.10)\n")
    info("*** Test commands:\n")
    info("  h1 ping h6   # Test across ring\n")
    info("  h1 ping h10  # Test adjacent\n")
    info("  pingall      # Test all connections\n")
    info("  link s1 s2 down  # Simulate link failure\n")
    info("  link s1 s2 up    # Restore link\n")
    
    # Start CLI
    CLI(net)
    
    # Cleanup
    info("\n*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    main()