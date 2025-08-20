#!/usr/bin/env python3
"""
Complex Graph Topology: 10 Switches, 20 Hosts
Creates a mesh-like graph topology with multiple redundant paths
Each switch connects to 2 hosts and multiple other switches
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
# import networkx as nx  # Not needed for this topology
import random

def create_graph_topology():
    """Create a complex graph topology with 10 switches and 20 hosts"""
    
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    
    info("*** Creating Graph Topology: 10 Switches, 20 Hosts\n")
    
    # Add controller
    c0 = net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6633
    )
    
    # Add 10 switches
    info("*** Adding 10 switches\n")
    switches = []
    for i in range(1, 11):
        sw = net.addSwitch(f's{i}', dpid=f'{i:016x}')
        switches.append(sw)
        info(f"  Added switch s{i}\n")
    
    # Add 20 hosts (2 per switch)
    info("\n*** Adding 20 hosts (2 per switch)\n")
    hosts = []
    host_num = 1
    for i, sw in enumerate(switches, 1):
        # Add 2 hosts per switch
        for j in range(2):
            ip = f'10.0.{i}.{j+1}'
            mac = f'00:00:00:00:{i:02x}:{j+1:02x}'
            h = net.addHost(f'h{host_num}', ip=ip, mac=mac)
            hosts.append(h)
            # Connect host to switch
            net.addLink(h, sw, port1=1, port2=(j+1))
            info(f"  h{host_num} ({ip}) -> s{i}\n")
            host_num += 1
    
    # Create mesh-like connections between switches
    info("\n*** Creating mesh topology between switches\n")
    
    # Create a more structured mesh with guaranteed connectivity
    # Ring topology first (ensures basic connectivity)
    info("  Creating ring backbone:\n")
    for i in range(10):
        s1 = switches[i]
        s2 = switches[(i + 1) % 10]
        port1 = 10 + i
        port2 = 20 + i
        net.addLink(s1, s2, port1=port1, port2=port2)
        info(f"    s{i+1} <-> s{((i+1)%10)+1}\n")
    
    # Add cross-connections for redundancy
    info("  Adding cross-connections:\n")
    cross_links = [
        (0, 2, 30, 30),  # s1 <-> s3
        (0, 4, 31, 31),  # s1 <-> s5
        (0, 5, 32, 32),  # s1 <-> s6
        (1, 3, 33, 33),  # s2 <-> s4
        (1, 6, 34, 34),  # s2 <-> s7
        (2, 5, 35, 35),  # s3 <-> s6
        (2, 7, 36, 36),  # s3 <-> s8
        (3, 6, 37, 37),  # s4 <-> s7
        (3, 8, 38, 38),  # s4 <-> s9
        (4, 7, 39, 39),  # s5 <-> s8
        (4, 9, 40, 40),  # s5 <-> s10
        (5, 8, 41, 41),  # s6 <-> s9
        (6, 9, 42, 42),  # s7 <-> s10
        (7, 9, 43, 43),  # s8 <-> s10
        (8, 0, 44, 44),  # s9 <-> s1 (close the mesh)
    ]
    
    for s1_idx, s2_idx, port1, port2 in cross_links:
        net.addLink(switches[s1_idx], switches[s2_idx], port1=port1, port2=port2)
        info(f"    s{s1_idx+1} <-> s{s2_idx+1}\n")
    
    return net, hosts, switches

def test_basic_connectivity(net, hosts):
    """Test connectivity between various host pairs"""
    info("\n*** Testing Basic Connectivity\n")
    
    # Test between hosts on same switch
    info("  Testing hosts on same switch (h1 -> h2):\n")
    result = hosts[0].cmd(f'ping -c 3 -W 1 {hosts[1].IP()}')
    if '0% packet loss' in result:
        info("    ✅ Same switch: Connected\n")
    else:
        info("    ❌ Same switch: Failed\n")
    
    # Test between hosts on adjacent switches
    info("  Testing hosts on adjacent switches (h1 -> h3):\n")
    result = hosts[0].cmd(f'ping -c 3 -W 1 {hosts[2].IP()}')
    if '0% packet loss' in result:
        info("    ✅ Adjacent switches: Connected\n")
    else:
        info("    ❌ Adjacent switches: Failed\n")
    
    # Test between hosts on far switches
    info("  Testing hosts on far switches (h1 -> h19):\n")
    result = hosts[0].cmd(f'ping -c 3 -W 1 {hosts[18].IP()}')
    if '0% packet loss' in result:
        info("    ✅ Far switches: Connected\n")
    else:
        info("    ❌ Far switches: Failed\n")

def test_all_pairs_sample(net, hosts):
    """Test connectivity between sample host pairs"""
    info("\n*** Testing Sample Host Pairs\n")
    
    # Test random sample of host pairs
    test_pairs = [
        (1, 5),   # h1 -> h5
        (2, 10),  # h2 -> h10
        (3, 15),  # h3 -> h15
        (7, 18),  # h7 -> h18
        (11, 20), # h11 -> h20
    ]
    
    success = 0
    for src, dst in test_pairs:
        src_host = hosts[src-1]
        dst_host = hosts[dst-1]
        info(f"  Testing h{src} ({src_host.IP()}) -> h{dst} ({dst_host.IP()}): ")
        
        result = src_host.cmd(f'ping -c 2 -W 1 {dst_host.IP()}')
        if '0% packet loss' in result:
            info("✅\n")
            success += 1
        else:
            info("❌\n")
    
    info(f"\n  Result: {success}/{len(test_pairs)} pairs connected\n")
    return success == len(test_pairs)

def test_link_failure(net, hosts, switches):
    """Test link failure and recovery"""
    info("\n*** Testing Link Failure Scenarios\n")
    
    # Start continuous ping
    info("  Starting ping from h1 to h20...\n")
    hosts[0].cmd(f'ping {hosts[19].IP()} > /tmp/ping_test.log 2>&1 &')
    ping_pid = hosts[0].cmd('echo $!').strip()
    
    import time
    time.sleep(3)
    
    # Fail a link
    info("  💥 Failing link s1 <-> s2\n")
    net.configLinkStatus('s1', 's2', 'down')
    
    time.sleep(5)
    
    # Check if still connected
    result = hosts[0].cmd(f'ping -c 3 -W 1 {hosts[19].IP()}')
    if '0% packet loss' in result:
        info("    ✅ Rerouting successful!\n")
    else:
        info("    ⚠️  Some packet loss during rerouting\n")
    
    # Restore link
    info("  🔧 Restoring link s1 <-> s2\n")
    net.configLinkStatus('s1', 's2', 'up')
    
    # Stop ping
    hosts[0].cmd(f'kill {ping_pid} 2>/dev/null')
    
    # Analyze results
    result = hosts[0].cmd('cat /tmp/ping_test.log | grep -c "bytes from"')
    success_count = int(result.strip()) if result.strip().isdigit() else 0
    info(f"  Total successful pings during test: {success_count}\n")

def run_graph_topology():
    """Main function to run the graph topology"""
    setLogLevel('info')
    
    info("\n" + "="*80 + "\n")
    info("🌐 GRAPH TOPOLOGY TEST: 10 SWITCHES, 20 HOSTS\n")
    info("="*80 + "\n")
    
    # Create topology
    net, hosts, switches = create_graph_topology()
    
    # Start network
    info("\n*** Starting network\n")
    net.start()
    
    info("\n*** Waiting for controller connection...\n")
    import time
    time.sleep(5)
    
    # Run tests
    test_basic_connectivity(net, hosts)
    test_all_pairs_sample(net, hosts)
    test_link_failure(net, hosts, switches)
    
    # Show host list
    info("\n*** Available hosts:\n")
    for i, h in enumerate(hosts, 1):
        info(f"  h{i}: {h.IP()}\n")
    
    # Interactive CLI
    info("\n*** Starting CLI\n")
    info("You can now test with commands like:\n")
    info("  h1 ping h20\n")
    info("  h5 ping h15\n")
    info("  pingall (warning: tests 20*19=380 connections!)\n")
    info("  link s1 s2 down/up\n")
    
    CLI(net)
    
    # Cleanup
    info("\n*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    run_graph_topology()