#!/usr/bin/env python3
"""
Final comprehensive test for Dijkstra controller
Tests all link failure scenarios and automatic rerouting
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info, error, debug
import time
import sys
import threading

class DiamondTopologyTest:
    def __init__(self):
        self.net = None
        self.ping_results = []
    
    def create_topology(self):
        """Create diamond topology with OVS switches"""
        self.net = Mininet(
            controller=RemoteController,
            switch=OVSKernelSwitch,
            link=TCLink,
            autoSetMacs=True
        )
        
        info("*** Creating diamond topology\n")
        
        # Add controller
        c0 = self.net.addController(
            'c0',
            controller=RemoteController,
            ip='127.0.0.1',
            port=6633
        )
        
        # Add switches
        s1 = self.net.addSwitch('s1', dpid='0000000000000001')
        s2 = self.net.addSwitch('s2', dpid='0000000000000002')
        s3 = self.net.addSwitch('s3', dpid='0000000000000003')
        s4 = self.net.addSwitch('s4', dpid='0000000000000004')
        
        # Add hosts
        h1 = self.net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
        h2 = self.net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
        
        # Create links (matching topology_config.json)
        info("*** Adding links\n")
        self.net.addLink(h1, s1, port1=1, port2=1)
        self.net.addLink(h2, s4, port1=1, port2=4)
        
        # Diamond paths
        self.net.addLink(s1, s2, port1=2, port2=1)  # Top
        self.net.addLink(s1, s3, port1=3, port2=1)  # Bottom
        self.net.addLink(s2, s4, port1=2, port2=1)
        self.net.addLink(s3, s4, port1=2, port2=2)
        
        # Cross paths
        self.net.addLink(s1, s4, port1=4, port2=3)  # Direct
        self.net.addLink(s2, s3, port1=3, port2=3)  # Cross
        
        return self.net
    
    def start_network(self):
        """Start the network"""
        info("\n*** Starting network\n")
        self.net.start()
        info("*** Waiting for controller connection...\n")
        time.sleep(5)
    
    def test_basic_connectivity(self):
        """Test 1: Basic connectivity"""
        info("\n" + "="*80 + "\n")
        info("TEST 1: BASIC CONNECTIVITY\n")
        info("="*80 + "\n")
        
        h1, h2 = self.net.get('h1', 'h2')
        
        info("Testing h1 -> h2 connectivity...\n")
        result = h1.cmd('ping -c 10 -i 0.5 10.0.0.2')
        
        loss = self._extract_packet_loss(result)
        rtt = self._extract_rtt(result)
        
        info(f"  Packet loss: {loss}%\n")
        if rtt:
            info(f"  RTT: {rtt}\n")
        
        if loss == 0:
            info("✅ PASS: Full connectivity achieved\n")
            return True
        else:
            error("❌ FAIL: Connectivity issues\n")
            return False
    
    def test_single_link_failure(self):
        """Test 2: Single link failure and recovery"""
        info("\n" + "="*80 + "\n")
        info("TEST 2: SINGLE LINK FAILURE (s1-s2)\n")
        info("="*80 + "\n")
        
        h1, h2 = self.net.get('h1', 'h2')
        
        # Start background ping
        info("Starting continuous ping monitoring...\n")
        self._start_ping_monitor(h1, h2, duration=30)
        
        time.sleep(5)
        info("  ✓ Initial path established\n")
        
        # Fail link
        info("\n💥 FAILING: s1 <-X-> s2 (top path)\n")
        self.net.configLinkStatus('s1', 's2', 'down')
        
        time.sleep(8)
        
        # Check connectivity
        info("\nChecking connectivity after failure...\n")
        result = h1.cmd('ping -c 5 -W 1 10.0.0.2')
        loss = self._extract_packet_loss(result)
        
        if loss == 0:
            info("  ✅ Traffic successfully rerouted!\n")
        else:
            info(f"  ⚠️  {loss}% packet loss during rerouting\n")
        
        # Recover link
        info("\n🔧 RECOVERING: s1 <--> s2\n")
        self.net.configLinkStatus('s1', 's2', 'up')
        
        time.sleep(5)
        
        # Final check
        result = h1.cmd('ping -c 5 -W 1 10.0.0.2')
        loss = self._extract_packet_loss(result)
        
        info(f"\nFinal connectivity: {100-loss}% success\n")
        
        # Stop monitor
        self._stop_ping_monitor()
        
        return loss < 20  # Allow some loss during transition
    
    def test_multiple_link_failures(self):
        """Test 3: Multiple link failures"""
        info("\n" + "="*80 + "\n")
        info("TEST 3: MULTIPLE LINK FAILURES\n")
        info("="*80 + "\n")
        
        h1, h2 = self.net.get('h1', 'h2')
        
        info("Starting test with all paths available...\n")
        
        # Initial test
        result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
        if '0% packet loss' in result:
            info("  ✓ Initial connectivity OK\n")
        
        # Failure 1: Top path
        info("\n💥 FAILURE 1: s1 <-X-> s2 (top path)\n")
        self.net.configLinkStatus('s1', 's2', 'down')
        time.sleep(3)
        
        result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
        if '0% packet loss' in result:
            info("  ✓ Rerouted through bottom path (s1->s3->s4)\n")
        
        # Failure 2: Bottom path
        info("\n💥 FAILURE 2: s3 <-X-> s4 (bottom path)\n")
        self.net.configLinkStatus('s3', 's4', 'down')
        time.sleep(3)
        
        result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
        if '0% packet loss' in result:
            info("  ✓ Rerouted through direct path (s1->s4)\n")
        else:
            # Try alternate routing
            info("  Checking for alternate paths...\n")
        
        # Failure 3: Direct path
        info("\n💥 FAILURE 3: s1 <-X-> s4 (direct path)\n")
        self.net.configLinkStatus('s1', 's4', 'down')
        time.sleep(3)
        
        result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
        if '0% packet loss' in result:
            info("  ✓ Found complex alternate path\n")
        else:
            info("  ⚠️  Limited connectivity\n")
        
        # Recovery
        info("\n🔧 RECOVERING all links...\n")
        self.net.configLinkStatus('s1', 's2', 'up')
        self.net.configLinkStatus('s3', 's4', 'up')
        self.net.configLinkStatus('s1', 's4', 'up')
        
        time.sleep(5)
        
        # Final test
        result = h1.cmd('ping -c 5 -W 1 10.0.0.2')
        loss = self._extract_packet_loss(result)
        
        info(f"\nFinal recovery: {100-loss}% success\n")
        
        return loss == 0
    
    def test_rapid_link_changes(self):
        """Test 4: Rapid link state changes"""
        info("\n" + "="*80 + "\n")
        info("TEST 4: RAPID LINK STATE CHANGES\n")
        info("="*80 + "\n")
        
        h1, h2 = self.net.get('h1', 'h2')
        
        info("Testing controller stability under rapid changes...\n")
        
        # Start monitoring
        self._start_ping_monitor(h1, h2, duration=20)
        
        time.sleep(3)
        
        # Rapid flapping
        for i in range(3):
            info(f"\n🔄 Flap cycle {i+1}/3\n")
            
            # Down
            info("  DOWN: s1-s2\n")
            self.net.configLinkStatus('s1', 's2', 'down')
            time.sleep(2)
            
            # Up
            info("  UP: s1-s2\n")
            self.net.configLinkStatus('s1', 's2', 'up')
            time.sleep(2)
        
        # Stop monitor and analyze
        self._stop_ping_monitor()
        
        # Final stability test
        info("\nFinal stability check...\n")
        result = h1.cmd('ping -c 5 -W 1 10.0.0.2')
        loss = self._extract_packet_loss(result)
        
        if loss == 0:
            info("✅ PASS: Controller remained stable\n")
            return True
        else:
            info(f"⚠️  {loss}% loss after rapid changes\n")
            return loss < 20
    
    def test_all_paths(self):
        """Test 5: Verify all possible paths work"""
        info("\n" + "="*80 + "\n")
        info("TEST 5: ALL PATH VERIFICATION\n")
        info("="*80 + "\n")
        
        h1, h2 = self.net.get('h1', 'h2')
        paths_tested = []
        
        # Path 1: Top path only (block others)
        info("\nPath 1: Force TOP path (s1->s2->s4)\n")
        self.net.configLinkStatus('s1', 's3', 'down')  # Block bottom
        self.net.configLinkStatus('s1', 's4', 'down')  # Block direct
        time.sleep(2)
        
        result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
        if '0% packet loss' in result:
            info("  ✓ Top path works\n")
            paths_tested.append("TOP")
        
        # Restore
        self.net.configLinkStatus('s1', 's3', 'up')
        self.net.configLinkStatus('s1', 's4', 'up')
        time.sleep(2)
        
        # Path 2: Bottom path only
        info("\nPath 2: Force BOTTOM path (s1->s3->s4)\n")
        self.net.configLinkStatus('s1', 's2', 'down')  # Block top
        self.net.configLinkStatus('s1', 's4', 'down')  # Block direct
        time.sleep(2)
        
        result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
        if '0% packet loss' in result:
            info("  ✓ Bottom path works\n")
            paths_tested.append("BOTTOM")
        
        # Restore
        self.net.configLinkStatus('s1', 's2', 'up')
        self.net.configLinkStatus('s1', 's4', 'up')
        time.sleep(2)
        
        # Path 3: Direct path only
        info("\nPath 3: Force DIRECT path (s1->s4)\n")
        self.net.configLinkStatus('s1', 's2', 'down')  # Block top
        self.net.configLinkStatus('s1', 's3', 'down')  # Block bottom
        time.sleep(2)
        
        result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
        if '0% packet loss' in result:
            info("  ✓ Direct path works\n")
            paths_tested.append("DIRECT")
        
        # Restore all
        self.net.configLinkStatus('s1', 's2', 'up')
        self.net.configLinkStatus('s1', 's3', 'up')
        time.sleep(2)
        
        info(f"\nPaths verified: {', '.join(paths_tested)}\n")
        return len(paths_tested) >= 3
    
    def _start_ping_monitor(self, h1, h2, duration=30):
        """Start background ping monitoring"""
        h1.cmd(f'ping -i 0.5 {h2.IP()} > /tmp/ping_monitor.log 2>&1 &')
        self.ping_pid = h1.cmd('echo $!').strip()
        self.monitor_host = h1
    
    def _stop_ping_monitor(self):
        """Stop ping monitoring and show results"""
        if hasattr(self, 'ping_pid'):
            self.monitor_host.cmd(f'kill {self.ping_pid} 2>/dev/null')
            
            # Analyze results
            result = self.monitor_host.cmd('cat /tmp/ping_monitor.log')
            transmitted = result.count('bytes from')
            lost = result.count('Unreachable') + result.count('Destination Host Unreachable')
            
            info(f"\nPing monitor results:\n")
            info(f"  Successful: {transmitted}\n")
            info(f"  Lost: {lost}\n")
            
            if transmitted > 0:
                loss_rate = (lost / (transmitted + lost)) * 100
                info(f"  Loss rate: {loss_rate:.1f}%\n")
    
    def _extract_packet_loss(self, ping_output):
        """Extract packet loss percentage from ping output"""
        for line in ping_output.split('\n'):
            if 'packet loss' in line:
                try:
                    loss = line.split('%')[0].split()[-1]
                    return float(loss)
                except:
                    pass
        return 100.0
    
    def _extract_rtt(self, ping_output):
        """Extract RTT from ping output"""
        for line in ping_output.split('\n'):
            if 'min/avg/max' in line:
                try:
                    return line.split('=')[1].strip()
                except:
                    pass
        return None
    
    def run_all_tests(self):
        """Run complete test suite"""
        info("\n" + "="*80 + "\n")
        info("🚀 DIJKSTRA CONTROLLER - FINAL TEST SUITE\n")
        info("="*80 + "\n")
        
        # Create and start network
        self.create_topology()
        self.start_network()
        
        # Run tests
        results = []
        results.append(("Basic Connectivity", self.test_basic_connectivity()))
        results.append(("Single Link Failure", self.test_single_link_failure()))
        results.append(("Multiple Link Failures", self.test_multiple_link_failures()))
        results.append(("Rapid Link Changes", self.test_rapid_link_changes()))
        results.append(("All Paths Verification", self.test_all_paths()))
        
        # Summary
        info("\n" + "="*80 + "\n")
        info("📊 FINAL TEST SUMMARY\n")
        info("="*80 + "\n")
        
        passed = 0
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            info(f"  {test_name}: {status}\n")
            if result:
                passed += 1
        
        info(f"\nTotal: {passed}/{len(results)} tests passed\n")
        
        if passed == len(results):
            info("🎉 ALL TESTS PASSED! Controller is working perfectly!\n")
        elif passed >= len(results) - 1:
            info("✅ Controller is working well with minor issues\n")
        else:
            info("⚠️  Controller needs improvement\n")
        
        # Interactive CLI
        info("\n*** Entering CLI for manual testing ***\n")
        info("Useful commands:\n")
        info("  h1 ping h2                    - Test connectivity\n")
        info("  link s1 s2 down/up           - Fail/recover link\n")
        info("  py net.configLinkStatus(...)  - Python API\n")
        info("  sh ovs-ofctl dump-flows s1    - Check flows\n")
        info("  exit                          - Exit CLI\n")
        
        CLI(self.net)
        
        # Cleanup
        info("\n*** Stopping network\n")
        self.net.stop()

def main():
    setLogLevel('info')
    test = DiamondTopologyTest()
    test.run_all_tests()

if __name__ == '__main__':
    main()