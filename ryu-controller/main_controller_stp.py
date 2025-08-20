#!/usr/bin/env python3
"""
Main Dijkstra SDN Controller with Broadcast Storm Prevention
Implements simple loop prevention for Ring topology
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4

# Topology discovery
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link

import networkx as nx
import logging
from collections import defaultdict, deque
import time
from datetime import datetime
import hashlib

class MainDijkstraControllerSTP(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'switches': switches.Switches}

    def __init__(self, *args, **kwargs):
        super(MainDijkstraControllerSTP, self).__init__(*args, **kwargs)
        
        # Core data structures
        self.switches_context = kwargs['switches']
        self.datapaths = {}
        self.host_locations = {}  # mac -> (dpid, port)
        self.topology_graph = nx.Graph()
        self.switch_to_port = defaultdict(dict)  # dpid -> {neighbor_dpid -> port}
        self.packet_count = 0
        self.flow_count = 0
        
        # Broadcast storm prevention
        self.broadcast_cache = deque(maxlen=1000)  # Store recent broadcast packet hashes
        self.broadcast_timestamps = {}  # hash -> timestamp
        self.BROADCAST_TIMEOUT = 2  # seconds
        
        # Spanning Tree (simple implementation)
        self.blocked_ports = set()  # (dpid, port) pairs that are blocked
        self.spanning_tree = None
        
        # Path tracking for change detection
        self.active_paths = {}  # (src_mac, dst_mac) -> path
        self.path_stats = defaultdict(int)  # path_string -> count
        
        # Enhanced logging
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        
        self.print_header()
    
    def print_header(self):
        """Print controller startup banner"""
        print("\n" + "="*80)
        print("🚀 DIJKSTRA SDN CONTROLLER WITH BROADCAST STORM PREVENTION")
        print("="*80)
        print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
        print("🔍 Features: Loop Prevention, Broadcast Cache, Simple STP")
        print("="*80 + "\n")
    
    def compute_spanning_tree(self):
        """Compute a spanning tree to prevent loops"""
        if not self.topology_graph or self.topology_graph.number_of_nodes() < 2:
            return
        
        try:
            # Create minimum spanning tree
            self.spanning_tree = nx.minimum_spanning_tree(self.topology_graph)
            
            # Find edges that should be blocked (not in spanning tree)
            all_edges = set(self.topology_graph.edges())
            tree_edges = set(self.spanning_tree.edges())
            
            # Clear previous blocked ports
            self.blocked_ports.clear()
            
            # Block ports for edges not in spanning tree
            for edge in all_edges - tree_edges:
                src_dpid, dst_dpid = edge
                # Block the port on the higher numbered switch
                if src_dpid > dst_dpid:
                    src_dpid, dst_dpid = dst_dpid, src_dpid
                
                if dst_dpid in self.switch_to_port and src_dpid in self.switch_to_port[dst_dpid]:
                    port = self.switch_to_port[dst_dpid][src_dpid]
                    self.blocked_ports.add((dst_dpid, port))
                    print(f"🚫 [STP] Blocking port {port} on s{dst_dpid} to prevent loop")
            
            print(f"🌳 [STP] Spanning tree computed: {len(tree_edges)} active links, {len(self.blocked_ports)} blocked ports")
            if self.blocked_ports:
                blocked_list = [f"s{dpid}:{port}" for dpid, port in sorted(self.blocked_ports)]
                print(f"   └── Blocked ports: {', '.join(blocked_list)}")
            
        except Exception as e:
            print(f"⚠️ [STP] Error computing spanning tree: {e}")
    
    def is_broadcast_duplicate(self, dpid, in_port, eth_src, eth_dst):
        """Check if this broadcast packet was recently seen"""
        # Create unique hash for this packet
        packet_hash = hashlib.md5(
            f"{dpid}{in_port}{eth_src}{eth_dst}{time.time()//0.1}".encode()
        ).hexdigest()
        
        # Clean old entries
        current_time = time.time()
        expired_hashes = [h for h, t in self.broadcast_timestamps.items() 
                         if current_time - t > self.BROADCAST_TIMEOUT]
        for h in expired_hashes:
            del self.broadcast_timestamps[h]
        
        # Check if we've seen this packet recently
        if packet_hash in self.broadcast_cache:
            return True
        
        # Add to cache
        self.broadcast_cache.append(packet_hash)
        self.broadcast_timestamps[packet_hash] = current_time
        return False
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection with detailed logging"""
        datapath = ev.msg.datapath
        dpid = datapath.id
        
        # Store datapath
        self.datapaths[dpid] = datapath
        
        print(f"🔌 [OPENFLOW] Switch s{dpid} connected")
        
        # Clear existing flows
        self.remove_all_flows(datapath)
        
        # Install table-miss flow
        self.install_table_miss_flow(datapath)
        
        print(f"✅ [OPENFLOW] Switch s{dpid} configured and ready")
        
        # Trigger topology discovery
        self.discover_topology()
    
    def remove_all_flows(self, datapath):
        """Remove all flows with logging"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch()
        flow_mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=match,
            instructions=[]
        )
        datapath.send_msg(flow_mod)
        print(f"🧹 [OPENFLOW] Cleared all flows on s{datapath.id}")
    
    def install_table_miss_flow(self, datapath):
        """Install table-miss flow with logging"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, 
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions, "TABLE_MISS")
    
    def add_flow(self, datapath, priority, match, actions, flow_type="NORMAL", timeout=0):
        """Install flow with detailed logging"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Use shorter timeout for dynamic flows to detect failures faster
        if flow_type == "PATH_FLOW":
            timeout = 10  # Reduced from 30 to 10 seconds
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=timeout,
            hard_timeout=timeout * 2 if timeout > 0 else 0
        )
        datapath.send_msg(mod)
        
        self.flow_count += 1
        print(f"📝 [FLOW #{self.flow_count}] Installed on s{datapath.id} - Type: {flow_type}")
    
    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        """Handle link discovery with detailed logging"""
        link = ev.link
        src_dpid = link.src.dpid
        dst_dpid = link.dst.dpid
        src_port = link.src.port_no
        dst_port = link.dst.port_no
        
        print(f"🔗 [TOPOLOGY] Link discovered: s{src_dpid}:{src_port} ↔ s{dst_dpid}:{dst_port}")
        self.discover_topology()
    
    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        """Handle link failure with detailed logging"""
        link = ev.link
        src_dpid = link.src.dpid
        dst_dpid = link.dst.dpid
        
        print(f"\n{'='*60}")
        print(f"💥 [LINK FAILURE] s{src_dpid} ↔ s{dst_dpid}")
        print(f"{'='*60}\n")
        
        # Remove the failed link from topology
        if self.topology_graph.has_edge(src_dpid, dst_dpid):
            self.topology_graph.remove_edge(src_dpid, dst_dpid)
        
        # Clear flows on all switches
        for dpid in self.datapaths:
            self.remove_all_flows(self.datapaths[dpid])
            self.install_table_miss_flow(self.datapaths[dpid])
        
        # Clear path tracking to detect new routes
        old_paths = len(self.active_paths)
        self.active_paths.clear()
        print(f"   └── 🗑️  Cleared {old_paths} tracked paths for recomputation")
        
        # Recompute spanning tree
        self.discover_topology()
        
        print(f"✅ [RECOVERY] Ready for rerouting")
    
    def discover_topology(self):
        """Discover and log current topology"""
        switch_list = get_switch(self.switches_context, None)
        switches = [switch.dp.id for switch in switch_list]
        
        links_list = get_link(self.switches_context, None)
        
        # Rebuild topology
        self.topology_graph.clear()
        self.switch_to_port.clear()
        
        for dpid in switches:
            self.topology_graph.add_node(dpid)
        
        for link in links_list:
            src_dpid = link.src.dpid
            dst_dpid = link.dst.dpid
            src_port = link.src.port_no
            dst_port = link.dst.port_no
            
            if not self.topology_graph.has_edge(src_dpid, dst_dpid):
                self.topology_graph.add_edge(src_dpid, dst_dpid, weight=1)
                self.switch_to_port[src_dpid][dst_dpid] = src_port
                self.switch_to_port[dst_dpid][src_dpid] = dst_port
        
        # Compute spanning tree
        if len(switches) > 1:
            self.compute_spanning_tree()
        
        # Log topology status
        if switches and links_list:
            print(f"\n📊 [TOPOLOGY] Network Status:")
            print(f"   └── Switches: {len(switches)} active")
            print(f"   └── Links: {len(links_list)} discovered")
            print(f"   └── Graph connectivity: {'Connected' if nx.is_connected(self.topology_graph) else 'Disconnected'}")
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packets with broadcast storm prevention"""
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        # Parse packet first to check type
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        
        # Skip LLDP and IPv6 silently (even on blocked ports)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP or eth.ethertype == 0x86dd:
            return
        
        # Check if port is blocked by STP (only log for non-LLDP packets)
        if (dpid, in_port) in self.blocked_ports:
            # Only log occasionally to reduce spam
            if self.packet_count % 100 == 0:  # Log every 100th blocked packet
                print(f"🚫 [STP] Dropped packets on blocked port s{dpid}:{in_port} (suppressing logs)")
            return
        
        src_mac = eth.src
        dst_mac = eth.dst
        self.packet_count += 1
        
        print(f"\n📦 [PACKET #{self.packet_count}] Received on s{dpid}:{in_port}")
        print(f"   └── SRC: {src_mac} → DST: {dst_mac}")
        
        # Learn host location
        self.learn_host_location(dpid, src_mac, in_port)
        
        # Handle broadcast/multicast with storm prevention
        if self.is_broadcast_multicast(dst_mac):
            # Check for duplicate broadcast
            if self.is_broadcast_duplicate(dpid, in_port, src_mac, dst_mac):
                print(f"   └── 🛑 [STORM] Dropped duplicate broadcast")
                return
            
            print(f"   └── 📡 Broadcast/Multicast: flooding packet (STP-filtered)")
            self.flood_packet_stp(datapath, msg, in_port)
            return
        
        # Find destination
        if dst_mac in self.host_locations:
            dst_dpid, dst_port = self.host_locations[dst_mac]
            
            if dpid == dst_dpid:
                # Same switch
                out_port = dst_port
                print(f"   └── 🎯 Same switch routing: port {out_port}")
                # Track even same-switch "paths"
                self.track_path_change(src_mac, dst_mac, [dpid])
            else:
                # Calculate path using Dijkstra
                path = self.calculate_shortest_path(dpid, dst_dpid)
                
                if not path or len(path) < 2:
                    print(f"   └── ❌ No path found from s{dpid} to s{dst_dpid}")
                    return
                
                next_hop = path[1]
                out_port = self.switch_to_port[dpid].get(next_hop)
                
                if not out_port:
                    print(f"   └── ❌ No port to next hop s{next_hop}")
                    return
                
                # Track and log path changes
                path_changed = self.track_path_change(src_mac, dst_mac, path)
                
                path_str = " → ".join([f"s{s}" for s in path])
                print(f"   └── 🛤️  Using DIJKSTRA PATH: {path_str}")
                print(f"   └── 🎯 Next hop: s{next_hop} via port {out_port}")
                print(f"   └── 📊 Path length: {len(path)-1} hops")
                
                if path_changed:
                    print(f"   └── 🔄 PATH CHANGED from previous route")
                
                # Install flow for efficiency
                self.install_path_flow(datapath, src_mac, dst_mac, out_port)
            
            # Forward packet
            self.forward_packet(datapath, msg, out_port, in_port)
            
        else:
            print(f"   └── ❓ Unknown destination: controlled flooding")
            self.flood_packet_stp(datapath, msg, in_port)
    
    def learn_host_location(self, dpid, mac, port):
        """Learn host location"""
        if mac in ['ff:ff:ff:ff:ff:ff', '00:00:00:00:00:00']:
            return
        
        # Smart detection for host ports
        inter_switch_ports = self.switch_to_port.get(dpid, {}).values()
        is_likely_host_port = port == 1 or port not in inter_switch_ports
        
        if mac not in self.host_locations and is_likely_host_port:
            self.host_locations[mac] = (dpid, port)
            print(f"🖥️  [HOST] Learned {mac} at s{dpid}:{port}")
    
    def calculate_shortest_path(self, src_dpid, dst_dpid):
        """Calculate shortest path using Dijkstra algorithm"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        try:
            path = nx.shortest_path(self.topology_graph, src_dpid, dst_dpid, weight='weight')
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def install_path_flow(self, datapath, src_mac, dst_mac, out_port):
        """Install flow entry for learned path"""
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
        actions = [parser.OFPActionOutput(out_port)]
        
        self.add_flow(datapath, 10, match, actions, "PATH_FLOW", timeout=10)
    
    def forward_packet(self, datapath, msg, out_port, in_port):
        """Forward packet to specific port"""
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
        
        print(f"   └── ✅ Packet forwarded via port {out_port}")
    
    def flood_packet_stp(self, datapath, msg, in_port):
        """Flood packet only on spanning tree ports (not blocked)"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        # Get all active ports from switch
        out_ports = []
        
        for port_no in datapath.ports:
            # Skip input port, local port, and invalid ports
            if (port_no != in_port and 
                port_no != ofproto.OFPP_LOCAL and
                port_no < ofproto.OFPP_MAX):
                
                # Skip blocked ports (STP)
                if (dpid, port_no) not in self.blocked_ports:
                    out_ports.append(port_no)
        
        if out_ports:
            actions = [parser.OFPActionOutput(port) for port in out_ports]
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
            
            print(f"   └── 📡 Flooded to STP-allowed ports: {sorted(out_ports)}")
        else:
            print(f"   └── ⚠️  No ports available for flooding")
    
    def track_path_change(self, src_mac, dst_mac, path):
        """Track path changes and return True if path changed"""
        flow_key = (src_mac, dst_mac)
        path_str = " → ".join([f"s{s}" for s in path])
        
        # Check if we had a previous path
        if flow_key in self.active_paths:
            old_path = self.active_paths[flow_key]
            old_path_str = " → ".join([f"s{s}" for s in old_path])
            
            if old_path != path:
                # Path changed!
                print(f"   └── ⚠️  PATH CHANGE DETECTED:")
                print(f"       OLD: {old_path_str} ({len(old_path)-1} hops)")
                print(f"       NEW: {path_str} ({len(path)-1} hops)")
                
                # Update path
                self.active_paths[flow_key] = path
                self.path_stats[path_str] += 1
                return True
        else:
            # First time seeing this flow
            self.active_paths[flow_key] = path
            self.path_stats[path_str] += 1
            print(f"   └── 🆕 New flow discovered: {src_mac} → {dst_mac}")
        
        return False
    
    def is_broadcast_multicast(self, mac):
        """Check if MAC is broadcast or multicast"""
        return mac in ['ff:ff:ff:ff:ff:ff'] or mac.startswith('33:33') or mac.startswith('01:00:5e')
    
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Handle port status changes for link failure detection"""
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        ofproto = msg.datapath.ofproto
        dpid = msg.datapath.id
        
        if reason == ofproto.OFPPR_ADD:
            print(f"➕ [PORT] Port {port_no} added on s{dpid}")
        elif reason == ofproto.OFPPR_DELETE:
            print(f"➖ [PORT] Port {port_no} deleted on s{dpid}")
        elif reason == ofproto.OFPPR_MODIFY:
            state = msg.desc.state
            if state & ofproto.OFPPS_LINK_DOWN:
                print(f"🔴 [PORT] Port {port_no} LINK_DOWN on s{dpid}")
            else:
                print(f"🟢 [PORT] Port {port_no} UP on s{dpid}")
        
        # Clear paths when port status changes to force recalculation
        if reason == ofproto.OFPPR_MODIFY:
            self.active_paths.clear()
            print(f"   └── 🔄 Cleared all paths for recalculation")