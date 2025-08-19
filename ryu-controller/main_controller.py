#!/usr/bin/env python3
"""
Main Dijkstra SDN Controller with Detailed Logging
Shows OpenFlow operations, failure detection, and routing decisions
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
from collections import defaultdict
import time
from datetime import datetime

class MainDijkstraController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'switches': switches.Switches}

    def __init__(self, *args, **kwargs):
        super(MainDijkstraController, self).__init__(*args, **kwargs)
        
        # Core data structures
        self.switches_context = kwargs['switches']
        self.datapaths = {}
        self.host_locations = {}  # mac -> (dpid, port)
        self.topology_graph = nx.Graph()
        self.switch_to_port = defaultdict(dict)  # dpid -> {neighbor_dpid -> port}
        self.packet_count = 0
        self.flow_count = 0
        
        # Enhanced logging
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        
        self.print_header()
    
    def print_header(self):
        """Print controller startup banner"""
        print("\n" + "="*80)
        print("🚀 DIJKSTRA SDN CONTROLLER - DETAILED LOGGING MODE")
        print("="*80)
        print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
        print("🔍 Monitoring: OpenFlow events, topology changes, routing decisions")
        print("="*80 + "\n")
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection with detailed logging"""
        datapath = ev.msg.datapath
        dpid = datapath.id
        
        # Store datapath
        self.datapaths[dpid] = datapath
        
        print(f"🔌 [OPENFLOW] Switch s{dpid} connected")
        print(f"   └── Datapath ID: {dpid:016x}")
        print(f"   └── OpenFlow Version: {datapath.ofproto.OFP_VERSION}")
        
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
        print(f"📝 [OPENFLOW] Flow #{self.flow_count} installed on s{datapath.id}")
        print(f"   └── Type: {flow_type}, Priority: {priority}, Timeout: {timeout}s")
        if hasattr(match, 'get') and 'eth_dst' in str(match):
            print(f"   └── Match: {match}")
    
    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        """Handle switch discovery"""
        switch = ev.switch
        print(f"🔍 [TOPOLOGY] Switch s{switch.dp.id} discovered by LLDP")
        self.discover_topology()
    
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
        src_port = link.src.port_no
        dst_port = link.dst.port_no
        
        print(f"\n" + "="*60)
        print(f"💥 [LINK FAILURE DETECTED]")
        print(f"   Failed link: s{src_dpid}:{src_port} ↔ s{dst_dpid}:{dst_port}")
        print("="*60)
        
        # Remove the failed link from topology
        if self.topology_graph.has_edge(src_dpid, dst_dpid):
            self.topology_graph.remove_edge(src_dpid, dst_dpid)
            print(f"   └── 🗑️  Removed edge from topology graph")
        
        # Clear specific port mappings
        if src_dpid in self.switch_to_port and dst_dpid in self.switch_to_port[src_dpid]:
            del self.switch_to_port[src_dpid][dst_dpid]
        if dst_dpid in self.switch_to_port and src_dpid in self.switch_to_port[dst_dpid]:
            del self.switch_to_port[dst_dpid][src_dpid]
        
        print(f"   └── 🧹 Clearing flows on affected switches...")
        
        # Clear flows on ALL switches to ensure complete relearning
        for dpid in self.datapaths:
            self.remove_all_flows(self.datapaths[dpid])
            self.install_table_miss_flow(self.datapaths[dpid])
        
        # Don't clear ALL host locations, just mark them for revalidation
        print(f"   └── 📍 Keeping {len(self.host_locations)} host locations")
        
        # Update topology
        self.discover_topology()
        
        print(f"✅ [RECOVERY] Ready for rerouting")
        print(f"   └── Remaining links: {self.topology_graph.number_of_edges()}")
        print("="*60 + "\n")
    
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
        
        # Log topology status
        if switches and links_list:
            print(f"\n📊 [TOPOLOGY] Network Status:")
            print(f"   └── Switches: {len(switches)} active")
            print(f"   └── Links: {len(links_list)} discovered")
            print(f"   └── Graph connectivity: {'Connected' if nx.is_connected(self.topology_graph) else 'Disconnected'}")
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packets with detailed routing logic logging"""
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        # Parse packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        
        # Skip LLDP and IPv6
        if eth.ethertype == ether_types.ETH_TYPE_LLDP or eth.ethertype == 0x86dd:
            return
        
        src_mac = eth.src
        dst_mac = eth.dst
        self.packet_count += 1
        
        print(f"\n📦 [PACKET #{self.packet_count}] Received on s{dpid}:{in_port}")
        print(f"   └── SRC: {src_mac} → DST: {dst_mac}")
        
        # Learn host location
        self.learn_host_location(dpid, src_mac, in_port)
        
        # Handle broadcast/multicast
        if self.is_broadcast_multicast(dst_mac):
            print(f"   └── 📡 Broadcast/Multicast: flooding packet")
            self.flood_packet(datapath, msg, in_port)
            return
        
        # Find destination
        if dst_mac in self.host_locations:
            dst_dpid, dst_port = self.host_locations[dst_mac]
            
            if dpid == dst_dpid:
                # Same switch
                out_port = dst_port
                print(f"   └── 🎯 Same switch routing: port {out_port}")
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
                
                path_str = " → ".join([f"s{s}" for s in path])
                print(f"   └── 🛤️  Using DIJKSTRA PATH: {path_str}")
                print(f"   └── 🎯 Next hop: s{next_hop} via port {out_port}")
                print(f"   └── 📊 Path length: {len(path)-1} hops")
                
                # Install flow for efficiency
                self.install_path_flow(datapath, src_mac, dst_mac, out_port)
            
            # Forward packet
            self.forward_packet(datapath, msg, out_port, in_port)
            
        else:
            print(f"   └── ❓ Unknown destination: flooding packet")
            self.flood_packet(datapath, msg, in_port)
    
    def learn_host_location(self, dpid, mac, port):
        """Learn host location with enhanced logging"""
        if mac in ['ff:ff:ff:ff:ff:ff', '00:00:00:00:00:00']:
            return
        
        # Smart detection: 
        # - Port 1 is always for hosts in our topologies
        # - Higher ports (>= 2) are typically inter-switch
        # - But we learn anyway if we haven't seen this MAC before
        inter_switch_ports = self.switch_to_port.get(dpid, {}).values()
        is_likely_host_port = port == 1 or port not in inter_switch_ports
        
        print(f"   └── 🔍 [DEBUG] Learning MAC {mac} on s{dpid}:{port}")
        print(f"   └── 🔍 [DEBUG] Inter-switch ports for s{dpid}: {list(inter_switch_ports)}")
        print(f"   └── 🔍 [DEBUG] Likely host port: {is_likely_host_port}")
        
        # Always learn if we haven't seen this MAC before
        if mac not in self.host_locations:
            if is_likely_host_port or port == 1:
                self.host_locations[mac] = (dpid, port)
                print(f"🖥️  [HOST] ✅ Learned new host {mac} at s{dpid}:{port}")
        elif self.host_locations[mac][0] == dpid and self.host_locations[mac][1] != port:
            # Host moved to different port on same switch
            if is_likely_host_port:
                old_port = self.host_locations[mac][1]
                self.host_locations[mac] = (dpid, port)
                print(f"🔄 [HOST] {mac} moved on s{dpid}: port {old_port} → {port}")
        elif self.host_locations[mac][0] != dpid:
            # Host appears on different switch - only update if it's a likely host port
            if is_likely_host_port:
                old_dpid, old_port = self.host_locations[mac]
                self.host_locations[mac] = (dpid, port)
                print(f"🔄 [HOST] {mac} moved: s{old_dpid}:{old_port} → s{dpid}:{port}")
    
    def calculate_shortest_path(self, src_dpid, dst_dpid):
        """Calculate shortest path using Dijkstra algorithm"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        try:
            # Check if both nodes exist in graph
            if not self.topology_graph.has_node(src_dpid) or not self.topology_graph.has_node(dst_dpid):
                print(f"   └── ⚠️  Node not in graph: s{src_dpid} or s{dst_dpid}")
                return None
            
            # Calculate shortest path
            path = nx.shortest_path(self.topology_graph, src_dpid, dst_dpid, weight='weight')
            
            # Log the calculated path
            if len(path) > 2:  # Only log multi-hop paths
                path_str = " → ".join([f"s{s}" for s in path])
                print(f"   └── 🛤️  DIJKSTRA PATH CALCULATED: {path_str}")
                
            return path
        except nx.NetworkXNoPath:
            print(f"   └── ❌ NO PATH exists from s{src_dpid} to s{dst_dpid}")
            print(f"       Graph has {self.topology_graph.number_of_edges()} edges")
            return None
        except nx.NodeNotFound as e:
            print(f"   └── ❌ Node not found: {e}")
            return None
    
    def install_path_flow(self, datapath, src_mac, dst_mac, out_port):
        """Install flow entry for learned path"""
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
        actions = [parser.OFPActionOutput(out_port)]
        
        self.add_flow(datapath, 10, match, actions, "PATH_FLOW", timeout=30)
    
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
    
    def flood_packet(self, datapath, msg, in_port):
        """Flood packet to all ports except input"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        # Get all active ports from switch
        out_ports = []
        
        # Get ports from datapath (actual switch ports)
        for port_no in datapath.ports:
            # Skip invalid ports
            if (port_no != in_port and 
                port_no != ofproto.OFPP_LOCAL and
                port_no < ofproto.OFPP_MAX):
                out_ports.append(port_no)
        
        print(f"   └── 🔍 Available ports on s{dpid}: {sorted(datapath.ports.keys())}")
        print(f"   └── 🔍 Inter-switch ports: {list(self.switch_to_port.get(dpid, {}).values())}")
        
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
            
            print(f"   └── 📡 Flooded to ports: {sorted(out_ports)}")
        else:
            print(f"   └── ⚠️  No ports available for flooding")
    
    def is_broadcast_multicast(self, mac):
        """Check if MAC is broadcast or multicast"""
        return mac in ['ff:ff:ff:ff:ff:ff'] or mac.startswith('33:33')
    
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Handle port status changes for link failure detection"""
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        ofproto = msg.datapath.ofproto
        dpid = msg.datapath.id
        
        print(f"\n{'='*60}")
        
        if reason == ofproto.OFPPR_ADD:
            print(f"➕ [PORT EVENT] Port {port_no} ADDED on s{dpid}")
        elif reason == ofproto.OFPPR_DELETE:
            print(f"➖ [PORT EVENT] Port {port_no} DELETED on s{dpid}")
            self.handle_port_down(dpid, port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            # Check port state
            state = msg.desc.state
            if state & ofproto.OFPPS_LINK_DOWN:
                print(f"🔴 [PORT EVENT] Port {port_no} LINK_DOWN on s{dpid}")
                self.handle_port_down(dpid, port_no)
            elif state & ofproto.OFPPS_BLOCKED:
                print(f"🚫 [PORT EVENT] Port {port_no} BLOCKED on s{dpid}")
                self.handle_port_down(dpid, port_no)
            else:
                print(f"🟢 [PORT EVENT] Port {port_no} UP on s{dpid}")
                self.handle_port_up(dpid, port_no)
        
        print(f"{'='*60}\n")
    
    def handle_port_down(self, dpid, port_no):
        """Handle port/link failure"""
        print(f"💥 [LINK FAILURE] Detected on s{dpid}:{port_no}")
        
        # Clear all flows on this switch to force relearning
        if dpid in self.datapaths:
            self.remove_all_flows(self.datapaths[dpid])
            self.install_table_miss_flow(self.datapaths[dpid])
            
        # Clear host locations that were on this port
        hosts_to_remove = []
        for mac, (host_dpid, host_port) in self.host_locations.items():
            if host_dpid == dpid and host_port == port_no:
                hosts_to_remove.append(mac)
        
        for mac in hosts_to_remove:
            del self.host_locations[mac]
            print(f"   └── 🗑️  Removed host {mac} from s{dpid}:{port_no}")
    
    def handle_port_up(self, dpid, port_no):
        """Handle port/link recovery"""
        print(f"✅ [LINK RECOVERY] Detected on s{dpid}:{port_no}")
        
        # Clear flows to force path recalculation
        if dpid in self.datapaths:
            self.remove_all_flows(self.datapaths[dpid])
            self.install_table_miss_flow(self.datapaths[dpid])
            
        # Also clear flows on all neighboring switches
        for neighbor_dpid in self.switch_to_port.get(dpid, {}).keys():
            if neighbor_dpid in self.datapaths:
                self.remove_all_flows(self.datapaths[neighbor_dpid])
                self.install_table_miss_flow(self.datapaths[neighbor_dpid])
                print(f"   └── 🧹 Also cleared flows on neighbor s{neighbor_dpid}")
    
    @set_ev_cls(ofp_event.EventOFPErrorMsg, MAIN_DISPATCHER)
    def error_msg_handler(self, ev):
        """Handle OpenFlow error messages"""
        msg = ev.msg
        print(f"⚠️  [OPENFLOW ERROR] Type: 0x{msg.type:02x}, Code: 0x{msg.code:02x}")
        print(f"   └── Datapath: s{ev.msg.datapath.id}")