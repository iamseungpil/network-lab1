#!/usr/bin/env python3
"""
Simple test for dynamic controller with 10-switch topology
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

def create_simple_test():
    """Create a simple 10-switch test topology"""
    
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    
    info("*** Creating Simple 10-Switch Test\n")
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    # Add 10 switches
    switches = []
    for i in range(1, 11):
        sw = net.addSwitch(f's{i}', dpid=f'{i:016x}')
        switches.append(sw)
    
    # Add 20 hosts (2 per switch)
    hosts = []
    for i in range(1, 11):
        for j in range(2):
            h = net.addHost(f'h{(i-1)*2+j+1}', ip=f'10.0.{i}.{j+1}')
            hosts.append(h)
            net.addLink(h, switches[i-1])
    
    # Create ring topology between switches
    for i in range(10):
        s1 = switches[i]
        s2 = switches[(i + 1) % 10]
        net.addLink(s1, s2)
    
    # Add a few cross-connections
    net.addLink(switches[0], switches[4])  # s1 <-> s5
    net.addLink(switches[2], switches[7])  # s3 <-> s8
    
    return net, hosts, switches

def test_connectivity(net, hosts):
    """Test basic connectivity"""
    info("\n*** Testing Connectivity\n")
    
    # Test h1 -> h4 (different switches)
    result = hosts[0].cmd(f'ping -c 2 -W 2 {hosts[3].IP()}')
    if '0% packet loss' in result:
        info("✅ h1 -> h4: CONNECTED\n")
    else:
        info("❌ h1 -> h4: FAILED\n")
        info(result + "\n")
    
    # Test h1 -> h10 (far switch)
    result = hosts[0].cmd(f'ping -c 2 -W 2 {hosts[9].IP()}')
    if '0% packet loss' in result:
        info("✅ h1 -> h10: CONNECTED\n")
    else:
        info("❌ h1 -> h10: FAILED\n")

def main():
    setLogLevel('info')
    
    info("\n" + "="*60 + "\n")
    info("🧪 DYNAMIC CONTROLLER TEST\n")
    info("="*60 + "\n")
    
    net, hosts, switches = create_simple_test()
    
    info("*** Starting network\n")
    net.start()
    
    info("*** Waiting for controller connection...\n")
    import time
    time.sleep(8)
    
    test_connectivity(net, hosts)
    
    info("\n*** Starting CLI (type 'exit' to quit)\n")
    info("Available hosts: h1-h20\n")
    info("Try: h1 ping h4, h1 ping h10\n")
    CLI(net)
    
    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    main()