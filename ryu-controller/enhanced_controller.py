#!/usr/bin/env python3
"""
Enhanced SDN Controller for Ring Topology
- Complete STP implementation with proper timing
- Packet flooding prevention
- Clear Dijkstra path recalculation logs
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4, lldp
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link

import networkx as nx
import logging
from collections import defaultdict, deque
import time
from datetime import datetime
import hashlib

class EnhancedRingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'switches': switches.Switches}

    def __init__(self, *args, **kwargs):
        super(EnhancedRingController, self).__init__(*args, **kwargs)
        
        # Core data structures
        self.datapaths = {}
        self.host_locations = {}  # mac -> (dpid, port)
        self.topology_graph = nx.Graph()
        self.switch_to_port = defaultdict(dict)  # dpid -> {neighbor_dpid -> port}
        
        # STP - Spanning Tree Protocol
        self.spanning_tree = None
        self.blocked_ports = set()  # (dpid, port) pairs that are blocked
        self.topology_stable = False
        self.topology_discovery_time = 0
        self.last_topology_change = time.time()
        
        # Flooding prevention
        self.broadcast_cache = {}  # hash -> timestamp
        self.BROADCAST_TIMEOUT = 2.0  # seconds
        self.packet_count = 0
        
        # Path tracking
        self.active_paths = {}  # (src_mac, dst_mac) -> path
        
        # Enhanced logging
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.print_header()
    
    def print_header(self):
        """Print controller startup banner"""
        print("\n" + "="*80)
        print("🚀 ENHANCED SDN CONTROLLER - RING TOPOLOGY OPTIMIZED")
        print("="*80)
        print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
        print("🔍 Features: Complete STP, Flooding Prevention, Clear Path Logs")
        print("="*80 + "\n")
    
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        """Handle datapath state changes"""
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                print(f"🔌 [SWITCH] s{datapath.id} connected")
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                print(f"❌ [SWITCH] s{datapath.id} disconnected")
                del self.datapaths[datapath.id]
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        dpid = datapath.id
        
        self.datapaths[dpid] = datapath
        print(f"✅ [OPENFLOW] Switch s{dpid} ready (OpenFlow {datapath.ofproto.OFP_VERSION})")
        
        # Clear existing flows
        self.remove_all_flows(datapath)
        
        # Install table-miss flow
        self.install_table_miss_flow(datapath)
    
    def remove_all_flows(self, datapath):
        """Remove all flows from switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Remove all flows
        match = parser.OFPMatch()
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=match
        )
        datapath.send_msg(mod)
    
    def install_table_miss_flow(self, datapath):
        """Install table-miss flow entry"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
    
    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, hard_timeout=0):
        """Add flow to switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                idle_timeout=idle_timeout, hard_timeout=hard_timeout,
                                match=match, instructions=inst)
        datapath.send_msg(mod)
    
    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        """Handle switch joining the network"""
        self.last_topology_change = time.time()
        self.topology_stable = False
        print(f"🔗 [TOPOLOGY] Switch entered, topology changed")
    
    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        """Handle new link discovery"""
        src = ev.link.src
        dst = ev.link.dst
        
        # Update topology graph
        self.topology_graph.add_edge(src.dpid, dst.dpid, 
                                     port={src.dpid: src.port_no, dst.dpid: dst.port_no})
        
        # Update switch port mapping
        self.switch_to_port[src.dpid][dst.dpid] = src.port_no
        self.switch_to_port[dst.dpid][src.dpid] = dst.port_no
        
        print(f"🔗 [LINK] Discovered: s{src.dpid}:{src.port_no} ↔ s{dst.dpid}:{dst.port_no}")
        
        self.last_topology_change = time.time()
        self.topology_stable = False
        
        # Schedule STP computation after topology stabilizes
        self.check_topology_stability()
    
    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        """Handle link failure"""
        src = ev.link.src
        dst = ev.link.dst
        
        print(f"\n" + "="*60)
        print(f"💥 [LINK FAILURE DETECTED]")
        print(f"   Failed link: s{src.dpid}:{src.port_no} ↔ s{dst.dpid}:{dst.port_no}")
        print("="*60)
        
        # Remove from topology graph
        if self.topology_graph.has_edge(src.dpid, dst.dpid):
            self.topology_graph.remove_edge(src.dpid, dst.dpid)
            print(f"🗑️  [TOPOLOGY] Removed edge from graph")
        
        # Remove from port mapping
        if dst.dpid in self.switch_to_port[src.dpid]:
            del self.switch_to_port[src.dpid][dst.dpid]
        if src.dpid in self.switch_to_port[dst.dpid]:
            del self.switch_to_port[dst.dpid][src.dpid]
        
        # Clear affected flows
        self.clear_affected_flows(src.dpid, dst.dpid)
        
        # Recompute STP
        self.compute_spanning_tree()
        
        print(f"🔄 [RECOVERY] Topology updated, paths will be recalculated")
        print("="*60 + "\n")
    
    def check_topology_stability(self):
        """Check if topology is stable and compute STP"""
        current_time = time.time()
        
        # Wait 3 seconds after last change for topology to stabilize
        if current_time - self.last_topology_change > 3.0:
            if not self.topology_stable:
                self.topology_stable = True
                self.topology_discovery_time = current_time
                print("\n" + "="*60)
                print("📊 [TOPOLOGY] Network topology stable")
                print(f"   Switches: {self.topology_graph.number_of_nodes()}")
                print(f"   Links: {self.topology_graph.number_of_edges()}")
                
                # Compute spanning tree
                self.compute_spanning_tree()
                print("="*60 + "\n")
    
    def compute_spanning_tree(self):
        """Compute spanning tree to prevent loops"""
        if not self.topology_graph or self.topology_graph.number_of_nodes() < 2:
            return
        
        try:
            # Create minimum spanning tree
            self.spanning_tree = nx.minimum_spanning_tree(self.topology_graph)
            
            # Find edges that should be blocked
            all_edges = set(self.topology_graph.edges())
            tree_edges = set(self.spanning_tree.edges())
            blocked_edges = all_edges - tree_edges
            
            # Clear previous blocked ports
            self.blocked_ports.clear()
            
            print("🌳 [STP] Computing Spanning Tree Protocol")
            print(f"   Active edges: {len(tree_edges)}")
            print(f"   Edges to block: {len(blocked_edges)}")
            
            # Block ports for edges not in spanning tree
            for src_dpid, dst_dpid in blocked_edges:
                # Block on both sides of the link
                if src_dpid in self.switch_to_port and dst_dpid in self.switch_to_port[src_dpid]:
                    port = self.switch_to_port[src_dpid][dst_dpid]
                    self.blocked_ports.add((src_dpid, port))
                    print(f"   🚫 Blocking s{src_dpid}:{port} (to s{dst_dpid})")
                    
                if dst_dpid in self.switch_to_port and src_dpid in self.switch_to_port[dst_dpid]:
                    port = self.switch_to_port[dst_dpid][src_dpid]
                    self.blocked_ports.add((dst_dpid, port))
                    print(f"   🚫 Blocking s{dst_dpid}:{port} (to s{src_dpid})")
            
            if self.blocked_ports:
                print(f"✅ [STP] Loop prevention active: {len(self.blocked_ports)} ports blocked")
            else:
                print("⚠️  [STP] No loops detected in topology")
                
        except Exception as e:
            print(f"❌ [STP] Error computing spanning tree: {e}")
    
    def clear_affected_flows(self, src_dpid, dst_dpid):
        """Clear flows affected by topology change"""
        # Clear flows on affected switches
        for dpid in [src_dpid, dst_dpid]:
            if dpid in self.datapaths:
                datapath = self.datapaths[dpid]
                self.remove_all_flows(datapath)
                self.install_table_miss_flow(datapath)
                print(f"🧹 [FLOW] Cleared flows on s{dpid}")
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet-in events"""
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        
        # Parse packet
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        
        if not eth_pkt:
            return
        
        # Ignore LLDP packets
        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        
        src_mac = eth_pkt.src
        dst_mac = eth_pkt.dst
        
        self.packet_count += 1
        
        # Learn source location
        self.learn_host_location(dpid, src_mac, in_port)
        
        # Check if port is blocked by STP
        if (dpid, in_port) in self.blocked_ports:
            print(f"🚫 [STP] Dropped packet on blocked port s{dpid}:{in_port}")
            return
        
        # Handle broadcast/multicast
        if self.is_broadcast_multicast(dst_mac):
            if self.should_flood_broadcast(msg, dpid, in_port):
                self.flood_packet(datapath, msg, in_port)
            return
        
        # Find destination and route
        if dst_mac in self.host_locations:
            self.route_packet(datapath, msg, src_mac, dst_mac, in_port)
        else:
            # Unknown destination - flood
            self.flood_packet(datapath, msg, in_port)
    
    def learn_host_location(self, dpid, mac, port):
        """Learn host location"""
        if mac in ['ff:ff:ff:ff:ff:ff', '00:00:00:00:00:00']:
            return
        
        # Check if this is likely a host port (not inter-switch)
        is_host_port = port not in self.switch_to_port.get(dpid, {}).values()
        
        if is_host_port:
            if mac not in self.host_locations:
                self.host_locations[mac] = (dpid, port)
                print(f"📍 [HOST] Learned {mac} at s{dpid}:{port}")
            elif self.host_locations[mac] != (dpid, port):
                old_dpid, old_port = self.host_locations[mac]
                self.host_locations[mac] = (dpid, port)
                print(f"📍 [HOST] Moved {mac}: s{old_dpid}:{old_port} → s{dpid}:{port}")
    
    def should_flood_broadcast(self, msg, dpid, in_port):
        """Check if broadcast should be flooded"""
        # Create packet hash
        pkt_data = msg.data[:64]  # Use first 64 bytes for hash
        pkt_hash = hashlib.md5(pkt_data).hexdigest()
        
        current_time = time.time()
        
        # Clean old entries
        expired = [h for h, t in self.broadcast_cache.items() 
                   if current_time - t > self.BROADCAST_TIMEOUT]
        for h in expired:
            del self.broadcast_cache[h]
        
        # Check if we've seen this broadcast recently
        if pkt_hash in self.broadcast_cache:
            return False  # Already flooded
        
        # Mark as seen
        self.broadcast_cache[pkt_hash] = current_time
        return True
    
    def route_packet(self, datapath, msg, src_mac, dst_mac, in_port):
        """Route packet to destination"""
        dpid = datapath.id
        dst_dpid, dst_port = self.host_locations[dst_mac]
        
        if dpid == dst_dpid:
            # Same switch - direct delivery
            out_port = dst_port
            print(f"➡️  [LOCAL] s{dpid}: {src_mac} → {dst_mac} via port {out_port}")
        else:
            # Different switch - compute path
            print(f"\n🧮 [DIJKSTRA] Computing path from s{dpid} to s{dst_dpid}")
            print(f"   Source: {src_mac} at s{dpid}:{in_port}")
            print(f"   Destination: {dst_mac} at s{dst_dpid}:{dst_port}")
            
            path = self.calculate_shortest_path(dpid, dst_dpid)
            
            if not path or len(path) < 2:
                print(f"   ❌ No path found!")
                return
            
            # Get next hop
            next_hop = path[1]
            out_port = self.switch_to_port[dpid].get(next_hop)
            
            if not out_port:
                print(f"   ❌ No port to next hop s{next_hop}")
                return
            
            # Check if port is blocked by STP
            if (dpid, out_port) in self.blocked_ports:
                print(f"   🚫 Next hop port is blocked by STP, path invalid")
                return
            
            # Log the selected path
            path_str = " → ".join([f"s{s}" for s in path])
            print(f"   ✅ PATH SELECTED: {path_str}")
            print(f"   📊 Total hops: {len(path)-1}")
            print(f"   ➡️  Next hop: s{next_hop} via port {out_port}")
            
            # Install flow for efficiency
            self.install_path_flow(datapath, src_mac, dst_mac, out_port)
            print(f"   💾 Flow installed for future packets\n")
        
        # Forward packet
        self.forward_packet(datapath, msg, out_port, in_port)
    
    def calculate_shortest_path(self, src_dpid, dst_dpid):
        """Calculate shortest path using Dijkstra algorithm"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        try:
            # Use spanning tree for path calculation (no blocked edges)
            if self.spanning_tree and self.spanning_tree.has_node(src_dpid) and self.spanning_tree.has_node(dst_dpid):
                path = nx.shortest_path(self.spanning_tree, src_dpid, dst_dpid)
            else:
                # Fallback to full graph
                path = nx.shortest_path(self.topology_graph, src_dpid, dst_dpid)
            
            return path
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            print(f"   ❌ Path calculation error: {e}")
            return None
    
    def install_path_flow(self, datapath, src_mac, dst_mac, out_port):
        """Install flow for the path"""
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch(eth_src=src_mac, eth_dst=dst_mac)
        actions = [parser.OFPActionOutput(out_port)]
        
        # Install with timeout for dynamic networks
        self.add_flow(datapath, 100, match, actions, idle_timeout=30, hard_timeout=300)
    
    def forward_packet(self, datapath, msg, out_port, in_port):
        """Forward packet to specified port"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        actions = [parser.OFPActionOutput(out_port)]
        data = None
        
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        datapath.send_msg(out)
    
    def flood_packet(self, datapath, msg, in_port):
        """Flood packet with loop prevention"""
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Get all ports
        all_ports = [p.port_no for p in datapath.ports.values() 
                     if p.port_no != ofproto.OFPP_CONTROLLER and p.port_no != ofproto.OFPP_LOCAL]
        
        # Remove blocked STP ports
        available_ports = [p for p in all_ports if (dpid, p) not in self.blocked_ports]
        
        # Remove input port (split-horizon)
        flood_ports = [p for p in available_ports if p != in_port]
        
        if flood_ports:
            actions = [parser.OFPActionOutput(p) for p in flood_ports]
            data = None
            
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=data
            )
            datapath.send_msg(out)
            
            print(f"💧 [FLOOD] s{dpid}: flooded to ports {flood_ports} (STP-safe)")
    
    def is_broadcast_multicast(self, mac):
        """Check if MAC is broadcast or multicast"""
        # Broadcast
        if mac == 'ff:ff:ff:ff:ff:ff':
            return True
        # IPv4 multicast
        if mac[0:6] == '01:00:5e':
            return True
        # IPv6 multicast  
        if mac[0:4] == '33:33':
            return True
        return False
    
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Handle port status changes"""
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        reason = msg.reason
        port_no = msg.desc.port_no
        
        ofproto = dp.ofproto
        
        if reason == ofproto.OFPPR_ADD:
            print(f"➕ [PORT] s{dpid}:{port_no} added")
        elif reason == ofproto.OFPPR_DELETE:
            print(f"➖ [PORT] s{dpid}:{port_no} deleted")
        elif reason == ofproto.OFPPR_MODIFY:
            if msg.desc.state & ofproto.OFPPS_LINK_DOWN:
                print(f"🔻 [PORT] s{dpid}:{port_no} link DOWN")
            else:
                print(f"🔺 [PORT] s{dpid}:{port_no} link UP")
        
        # Check topology stability after port change
        self.last_topology_change = time.time()
        self.topology_stable = False