"""
Enhanced Dijkstra SDN Controller for 10 switches
With detailed logging and path visualization
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp
import networkx as nx
import logging
from collections import defaultdict
from datetime import datetime

class DijkstraController10(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DijkstraController10, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.mac_to_dpid = {}
        self.topology = nx.Graph()
        self.switch_ports = defaultdict(dict)
        self.active_paths = {}  # Track active paths for visualization
        self.path_counter = 0  # Count path calculations
        
        # Enhanced logging with colors
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger.info("="*70)
        self.logger.info(" DIJKSTRA CONTROLLER FOR 10-SWITCH TOPOLOGY STARTED")
        self.logger.info("="*70)
        
        # Initialize 10-switch topology
        self.setup_initial_topology()

    def setup_initial_topology(self):
        """Configure a complex 10-switch mesh topology"""
        self.logger.info("\n" + "="*70)
        self.logger.info(" INITIALIZING 10-SWITCH MESH TOPOLOGY")
        self.logger.info("="*70)
        
        # Topology design:
        #     1 --- 2 --- 3
        #     |  X  |  X  |
        #     4 --- 5 --- 6
        #     |  X  |  X  |
        #     7 --- 8 --- 9
        #           |
        #          10
        
        # Row 1 connections
        self.add_link(1, 2, 2, 2)  # s1:2 <-> s2:2
        self.add_link(2, 3, 3, 3)  # s2:3 <-> s3:3
        
        # Row 2 connections
        self.add_link(4, 2, 5, 2)  # s4:2 <-> s5:2
        self.add_link(5, 3, 6, 2)  # s5:3 <-> s6:2
        
        # Row 3 connections
        self.add_link(7, 2, 8, 2)  # s7:2 <-> s8:2
        self.add_link(8, 3, 9, 2)  # s8:3 <-> s9:2
        
        # Vertical connections
        self.add_link(1, 3, 4, 3)  # s1:3 <-> s4:3
        self.add_link(2, 4, 5, 4)  # s2:4 <-> s5:4
        self.add_link(3, 4, 6, 3)  # s3:4 <-> s6:3
        self.add_link(4, 4, 7, 3)  # s4:4 <-> s7:3
        self.add_link(5, 5, 8, 4)  # s5:5 <-> s8:4
        self.add_link(6, 4, 9, 3)  # s6:4 <-> s9:3
        
        # Diagonal connections for redundancy
        self.add_link(1, 4, 5, 6)  # s1:4 <-> s5:6
        self.add_link(2, 5, 4, 5)  # s2:5 <-> s4:5
        self.add_link(2, 6, 6, 5)  # s2:6 <-> s6:5
        self.add_link(3, 5, 5, 7)  # s3:5 <-> s5:7
        self.add_link(4, 6, 8, 5)  # s4:6 <-> s8:5
        self.add_link(5, 8, 7, 4)  # s5:8 <-> s7:4
        self.add_link(5, 9, 9, 4)  # s5:9 <-> s9:4
        self.add_link(6, 6, 8, 6)  # s6:6 <-> s8:6
        
        # Connect s10 to central switch s8
        self.add_link(8, 10, 10, 2)  # s8:10 <-> s10:2
        
        self.print_topology_summary()

    def print_topology_summary(self):
        """Print a summary of the topology"""
        edges = list(self.topology.edges())
        self.logger.info(f"\n📊 TOPOLOGY SUMMARY:")
        self.logger.info(f"   Total Switches: {self.topology.number_of_nodes()}")
        self.logger.info(f"   Total Links: {self.topology.number_of_edges()}")
        self.logger.info(f"   Network Diameter: {nx.diameter(self.topology) if nx.is_connected(self.topology) else 'Not connected'}")
        
        # Print connectivity matrix
        self.logger.info("\n🔗 CONNECTIVITY MATRIX:")
        for node in sorted(self.topology.nodes()):
            neighbors = sorted(list(self.topology.neighbors(node)))
            self.logger.info(f"   s{node} connected to: {['s'+str(n) for n in neighbors]}")

    def add_link(self, dpid1, port1, dpid2, port2):
        """Add a bidirectional link to topology"""
        if not self.topology.has_edge(dpid1, dpid2):
            self.topology.add_edge(dpid1, dpid2, weight=1)
            self.switch_ports[dpid1][dpid2] = port1
            self.switch_ports[dpid2][dpid1] = port2
            self.logger.info(f"   ➕ Link added: s{dpid1}:{port1} <----> s{dpid2}:{port2}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        self.datapaths[dpid] = datapath
        self.logger.info(f"\n✅ [SWITCH ONLINE] s{dpid} connected to controller")
        
        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Add flow entry to switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  priority=priority, match=match, 
                                  instructions=inst, idle_timeout=60, hard_timeout=120)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst, 
                                  idle_timeout=60, hard_timeout=120)
        datapath.send_msg(mod)

    def get_path(self, src_dpid, dst_dpid):
        """Calculate shortest path using Dijkstra with detailed logging"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        if src_dpid not in self.topology or dst_dpid not in self.topology:
            self.logger.error(f"   ❌ [PATH ERROR] s{src_dpid} or s{dst_dpid} not in topology")
            return None
            
        try:
            self.path_counter += 1
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f" 🧮 DIJKSTRA CALCULATION #{self.path_counter}")
            self.logger.info(f"{'='*60}")
            
            # Calculate primary path
            path = nx.shortest_path(self.topology, src_dpid, dst_dpid, weight='weight')
            path_str = " → ".join([f"s{dpid}" for dpid in path])
            
            self.logger.info(f"   📍 Source: s{src_dpid}")
            self.logger.info(f"   🎯 Destination: s{dst_dpid}")
            self.logger.info(f"   📏 Shortest Path Length: {len(path)-1} hops")
            self.logger.info(f"   🛤️  PATH: {path_str}")
            
            # Check for alternative paths
            try:
                all_paths = list(nx.all_shortest_paths(self.topology, src_dpid, dst_dpid, weight='weight'))
                if len(all_paths) > 1:
                    self.logger.info(f"   🔄 Alternative paths available: {len(all_paths)} total")
                    for i, alt_path in enumerate(all_paths[1:], 1):
                        if i <= 2:  # Show max 2 alternatives
                            alt_str = " → ".join([f"s{dpid}" for dpid in alt_path])
                            self.logger.info(f"      Alt {i}: {alt_str}")
            except:
                pass
            
            return path
            
        except nx.NetworkXNoPath:
            self.logger.error(f"\n   ❌ [NO PATH] Cannot reach s{dst_dpid} from s{src_dpid}")
            self.logger.error(f"      Network might be partitioned!")
            return None

    def get_out_port(self, current_dpid, next_dpid):
        """Get output port for next hop"""
        if next_dpid in self.switch_ports[current_dpid]:
            return self.switch_ports[current_dpid][next_dpid]
        return None

    def install_path(self, path, src_mac, dst_mac):
        """Install flow rules along path with detailed logging"""
        self.logger.info(f"\n   📝 [FLOW INSTALLATION]")
        self.logger.info(f"      Installing flows for {src_mac} → {dst_mac}")
        
        flow_count = 0
        for i in range(len(path) - 1):
            curr_dpid = path[i]
            next_dpid = path[i + 1]
            
            if curr_dpid not in self.datapaths:
                continue
                
            out_port = self.get_out_port(curr_dpid, next_dpid)
            if not out_port:
                continue
                
            datapath = self.datapaths[curr_dpid]
            parser = datapath.ofproto_parser
            
            # Forward flow
            match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 10, match, actions)
            flow_count += 1
            
            self.logger.info(f"      ✓ s{curr_dpid}: Forward to port {out_port} → s{next_dpid}")
            
            # Reverse flow
            if i > 0:
                prev_dpid = path[i - 1]
                in_port = self.get_out_port(curr_dpid, prev_dpid)
                if in_port:
                    match = parser.OFPMatch(eth_dst=src_mac, eth_src=dst_mac)
                    actions = [parser.OFPActionOutput(in_port)]
                    self.add_flow(datapath, 10, match, actions)
                    flow_count += 1
        
        self.logger.info(f"      📊 Total flows installed: {flow_count}")
        
        # Store active path for monitoring
        path_key = f"{src_mac}->{dst_mac}"
        self.active_paths[path_key] = path

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet-in messages"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]
        
        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return
            
        dst_mac = eth_pkt.dst
        src_mac = eth_pkt.src
        
        # Learn MAC location
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port
        self.mac_to_dpid[src_mac] = dpid
        
        # Suppress multicast/broadcast logging
        if dst_mac[:8] in ['33:33:00', 'ff:ff:ff', '01:00:5e']:
            out_port = ofproto.OFPP_FLOOD
        elif dst_mac in self.mac_to_dpid:
            dst_dpid = self.mac_to_dpid[dst_mac]
            
            if dpid == dst_dpid:
                # Same switch
                if dst_mac in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst_mac]
                else:
                    out_port = ofproto.OFPP_FLOOD
            else:
                # Different switch - calculate path
                self.logger.info(f"\n📨 [PACKET_IN] s{dpid} received packet")
                self.logger.info(f"   From: {src_mac} (s{dpid})")
                self.logger.info(f"   To: {dst_mac} (s{dst_dpid})")
                
                path = self.get_path(dpid, dst_dpid)
                if path and len(path) > 1:
                    next_dpid = path[1]
                    out_port = self.get_out_port(dpid, next_dpid)
                    if out_port:
                        self.install_path(path, src_mac, dst_mac)
                    else:
                        out_port = ofproto.OFPP_FLOOD
                else:
                    out_port = ofproto.OFPP_FLOOD
        else:
            out_port = ofproto.OFPP_FLOOD
        
        # Send packet out
        actions = [parser.OFPActionOutput(out_port)]
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
            
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Handle port status changes"""
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto
        
        if reason == ofproto.OFPPR_ADD:
            self.logger.info(f"\n✅ [PORT UP] s{dpid}:{port_no} is UP")
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.error(f"\n🔴 [PORT DOWN] s{dpid}:{port_no} is DOWN - Link failure detected!")
            self.handle_link_failure(dpid, port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info(f"\n🔧 [PORT MODIFIED] s{dpid}:{port_no} modified")

    def handle_link_failure(self, dpid, port_no):
        """Handle link failure with detailed logging"""
        self.logger.warning(f"\n{'='*60}")
        self.logger.warning(f" ⚠️  LINK FAILURE DETECTED")
        self.logger.warning(f"{'='*60}")
        
        # Find affected link
        for other_dpid in list(self.switch_ports[dpid].keys()):
            if self.switch_ports[dpid][other_dpid] == port_no:
                if self.topology.has_edge(dpid, other_dpid):
                    self.logger.error(f"   🔗 Failed Link: s{dpid} <-X-> s{other_dpid}")
                    
                    # Check affected paths before removal
                    affected_paths = []
                    for path_key, path in self.active_paths.items():
                        for i in range(len(path)-1):
                            if (path[i] == dpid and path[i+1] == other_dpid) or \
                               (path[i] == other_dpid and path[i+1] == dpid):
                                affected_paths.append(path_key)
                                break
                    
                    if affected_paths:
                        self.logger.warning(f"   ⚡ Affected paths: {len(affected_paths)}")
                        for path_key in affected_paths[:3]:  # Show max 3
                            self.logger.warning(f"      - {path_key}")
                    
                    # Remove link from topology
                    self.topology.remove_edge(dpid, other_dpid)
                    del self.switch_ports[dpid][other_dpid]
                    if dpid in self.switch_ports[other_dpid]:
                        del self.switch_ports[other_dpid][dpid]
                    
                    # Check if network is still connected
                    if nx.is_connected(self.topology):
                        self.logger.info(f"   ✅ Network still connected")
                        components = 1
                    else:
                        components = nx.number_connected_components(self.topology)
                        self.logger.error(f"   ⚠️  Network PARTITIONED into {components} segments!")
                    
                    self.logger.info(f"   📊 Remaining links: {self.topology.number_of_edges()}")
                    
                    # Clear flows to trigger rerouting
                    self.clear_flows_all()
                break

    def clear_flows_all(self):
        """Clear all flows for rerouting"""
        self.logger.warning(f"\n   🔄 [REROUTING] Clearing all flows...")
        cleared = 0
        for dpid, datapath in self.datapaths.items():
            self.clear_flows(datapath)
            cleared += 1
        self.logger.info(f"   ✅ Cleared flows on {cleared} switches")
        self.logger.info(f"   📍 Next packet will trigger new path calculation")
        
        # Clear active paths
        self.active_paths.clear()

    def clear_flows(self, datapath):
        """Clear flows on a switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Delete all flows except table-miss
        match = parser.OFPMatch()
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            priority=1,
            match=match
        )
        datapath.send_msg(mod)