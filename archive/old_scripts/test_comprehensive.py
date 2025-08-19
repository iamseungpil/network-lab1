#!/usr/bin/env python3
"""
Comprehensive test for 10-switch, 20-host topology with dynamic controller
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

def create_topology():
    """Create 10-switch, 20-host topology exactly like graph_topology_10sw_20h.py"""
    
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    
    info("*** Creating 10-Switch, 20-Host Graph Topology\n")
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    # Add 10 switches
    switches = []
    for i in range(1, 11):
        sw = net.addSwitch(f's{i}', dpid=f'{i:016x}')
        switches.append(sw)
        info(f"  Added switch s{i}\n")
    
    # Add 20 hosts (2 per switch)
    hosts = []
    host_num = 1
    for i, sw in enumerate(switches, 1):
        for j in range(2):
            ip = f'10.0.{i}.{j+1}'
            mac = f'00:00:00:00:{i:02x}:{j+1:02x}'
            h = net.addHost(f'h{host_num}', ip=ip, mac=mac)
            hosts.append(h)
            net.addLink(h, sw, port1=1, port2=(j+1))
            info(f"  h{host_num} ({ip}) -> s{i}\n")
            host_num += 1
    
    # Ring backbone
    info("*** Creating ring backbone\n")
    for i in range(10):
        s1 = switches[i]
        s2 = switches[(i + 1) % 10]
        port1 = 10 + i
        port2 = 20 + i
        net.addLink(s1, s2, port1=port1, port2=port2)
        info(f"    s{i+1} <-> s{((i+1)%10)+1}\n")
    
    # Cross-connections
    info("*** Adding cross-connections\n")
    cross_links = [
        (0, 2, 30, 30), (0, 4, 31, 31), (0, 5, 32, 32),
        (1, 3, 33, 33), (1, 6, 34, 34), (2, 5, 35, 35),
        (2, 7, 36, 36), (3, 6, 37, 37), (3, 8, 38, 38),
        (4, 7, 39, 39), (4, 9, 40, 40), (5, 8, 41, 41),
        (6, 9, 42, 42), (7, 9, 43, 43), (8, 0, 44, 44),
    ]
    
    for s1_idx, s2_idx, port1, port2 in cross_links:
        net.addLink(switches[s1_idx], switches[s2_idx], port1=port1, port2=port2)
        info(f"    s{s1_idx+1} <-> s{s2_idx+1}\n")
    
    return net, hosts, switches

def comprehensive_test(net, hosts):
    """Run comprehensive connectivity tests"""
    info("\n" + "="*60 + "\n")
    info("🧪 COMPREHENSIVE CONNECTIVITY TESTS\n")
    info("="*60 + "\n")
    
    test_cases = [
        # Same switch
        (1, 2, "Same switch"),
        # Adjacent switches
        (1, 3, "Adjacent switches"), 
        (3, 5, "Adjacent switches"),
        # Cross-connections
        (1, 11, "Cross-connection s1<->s6"),
        (1, 9, "Cross-connection s1<->s5"),
        # Far switches via ring
        (1, 17, "Far switches (s1->s9)"),
        (5, 19, "Far switches (s3->s10)"),
        # Maximum distance
        (1, 20, "Maximum distance (s1->s10)"),
        (2, 19, "Maximum distance (s1->s10)"),
        # Random pairs
        (7, 14, "Random pair (s4->s7)"),
        (13, 8, "Random pair (s7->s4)"),
    ]
    
    success = 0
    total = len(test_cases)
    
    for src, dst, description in test_cases:
        src_host = hosts[src-1]
        dst_host = hosts[dst-1]
        info(f"  Test {success+1:2d}: h{src} -> h{dst} ({description}): ")
        
        result = src_host.cmd(f'ping -c 2 -W 2 {dst_host.IP()}')
        if '0% packet loss' in result:
            info("✅\n")
            success += 1
        else:
            info("❌\n")
            # Print failed ping details
            info(f"    Failed: {src_host.IP()} -> {dst_host.IP()}\n")
    
    info("\n" + "="*60 + "\n")
    info(f"📊 RESULTS: {success}/{total} tests passed ({success/total*100:.1f}%)\n")
    info("="*60 + "\n")
    
    return success == total

def main():
    setLogLevel('info')
    
    info("\n" + "="*80 + "\n")
    info("🌐 COMPREHENSIVE 10-SWITCH TOPOLOGY TEST\n")
    info("="*80 + "\n")
    
    net, hosts, switches = create_topology()
    
    info("*** Starting network\n")
    net.start()
    
    info("*** Waiting for topology discovery...\n")
    import time
    time.sleep(10)  # Wait longer for full discovery
    
    # Run comprehensive tests
    all_passed = comprehensive_test(net, hosts)
    
    if all_passed:
        info("🎉 ALL TESTS PASSED! Network is fully functional.\n")
    else:
        info("⚠️  Some tests failed. Network may have issues.\n")
    
    info("\n*** Starting Interactive CLI\n")
    info("Available commands:\n")
    info("  h1 ping h20    - Test specific connectivity\n") 
    info("  pingall        - Test all pairs (takes time!)\n")
    info("  link s1 s2 down/up - Test link failure\n")
    info("  exit           - Exit CLI\n")
    
    CLI(net)
    
    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    main()