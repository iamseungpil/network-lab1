#!/usr/bin/env python
"""
Dual Controller Topology - 10 switches, 20 hosts
Primary Controller: s1-s5 (h1-h10)
Secondary Controller: s6-s10 (h11-h20)
"""

from mininet.topo import Topo

class DualControllerTopo(Topo):
    """Dual controller topology with cross-domain connectivity"""
    
    def build(self):
        # Create 10 switches
        switches = []
        for i in range(1, 11):  # s1-s10
            switch = self.addSwitch(f's{i}', protocols='OpenFlow13')
            switches.append(switch)
        
        # Add 20 hosts (2 per switch)
        host_id = 1
        for i, switch in enumerate(switches, 1):
            for j in range(2):
                host = self.addHost(f'h{host_id}', 
                                  ip=f'10.0.0.{host_id}/24',
                                  mac=f'00:00:00:00:00:{host_id:02x}')
                self.addLink(host, switch)
                host_id += 1
        
        # Primary domain topology (s1-s5)
        self.addLink(switches[0], switches[1])  # s1-s2
        self.addLink(switches[0], switches[2])  # s1-s3
        self.addLink(switches[1], switches[3])  # s2-s4
        self.addLink(switches[1], switches[4])  # s2-s5
        
        # Cross-domain links (Primary to Secondary)
        self.addLink(switches[2], switches[5])  # s3-s6 (gateway)
        self.addLink(switches[2], switches[6])  # s3-s7 (gateway)
        self.addLink(switches[3], switches[7])  # s4-s8 (gateway)
        self.addLink(switches[3], switches[8])  # s4-s9 (gateway)
        self.addLink(switches[4], switches[9])  # s5-s10 (gateway)
        
        # Secondary domain internal links (s6-s10)
        self.addLink(switches[5], switches[6])  # s6-s7
        self.addLink(switches[7], switches[8])  # s8-s9

# Register topology  
topos = {'dualcontroller': DualControllerTopo}

def create_networkx_graph():
    """Create corresponding NetworkX graph for Dijkstra calculations"""
    try:
        import networkx as nx
        G = nx.Graph()
        
        # Add nodes (switches)
        for i in range(1, 11):  # s1-s10
            G.add_node(i)
        
        # Add edges with weights (matching the topology above)
        edges = [
            # Primary domain (s1-s5)
            (1, 2, 1), (1, 3, 1), (2, 4, 1), (2, 5, 1),
            # Cross-domain links
            (3, 6, 2), (3, 7, 2), (4, 8, 2), (4, 9, 2), (5, 10, 2),
            # Secondary domain internal
            (6, 7, 1), (8, 9, 1)
        ]
        
        for s1, s2, weight in edges:
            G.add_edge(s1, s2, weight=weight)
        
        return G
    except ImportError:
        print("NetworkX not available - using topology without graph calculations")
        return None

if __name__ == '__main__':
    from mininet.net import Mininet
    from mininet.node import RemoteController
    from mininet.cli import CLI
    from mininet.log import setLogLevel
    
    setLogLevel('info')
    
    topo = DualControllerTopo()
    
    # Create network with dual controllers
    net = Mininet(topo=topo, controller=None, autoSetMacs=True)
    
    # Add controllers
    c1 = net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, ip='127.0.0.1', port=6634)
    
    net.start()
    
    # Assign controllers to switches
    switches = [net.get(f's{i}') for i in range(1, 11)]
    for i in range(5):  # s1-s5 to primary
        switches[i].start([c1])
    for i in range(5, 10):  # s6-s10 to secondary
        switches[i].start([c2])
    
    print("*** Dual controller network topology created")
    print("*** 10 switches, 20 hosts")
    print("*** Primary: s1-s5 (h1-h10), Secondary: s6-s10 (h11-h20)")
    
    # Test graph
    G = create_networkx_graph()
    if G:
        print(f"*** NetworkX graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        
        try:
            import networkx as nx
            # Test path within primary domain
            path = nx.shortest_path(G, 1, 5, weight='weight')
            cost = nx.shortest_path_length(G, 1, 5, weight='weight')
            print(f"*** Primary domain path s1->s5: {path} (cost={cost})")
            
            # Test cross-domain path
            path = nx.shortest_path(G, 1, 10, weight='weight')  
            cost = nx.shortest_path_length(G, 1, 10, weight='weight')
            print(f"*** Cross-domain path s1->s10: {path} (cost={cost})")
        except Exception as e:
            print(f"*** Error calculating paths: {e}")
    else:
        print("*** NetworkX not available")
    
    CLI(net)
    net.stop()