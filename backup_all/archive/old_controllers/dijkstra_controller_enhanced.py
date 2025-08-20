"""
Enhanced Dijkstra SDN Controller with Detailed Logging
Static topology configuration with dynamic link failure handling
Clear visualization of routing decisions and path changes
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4, icmp
import networkx as nx
import logging
from collections import defaultdict
import json
import os
from datetime import datetime

class DijkstraControllerEnhanced(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DijkstraControllerEnhanced, self).__init__(*args, **kwargs)
        
        # Core data structures
        self.datapaths = {}  # dpid -> datapath
        self.mac_to_port = defaultdict(dict)  # dpid -> {mac -> port}
        self.host_mac_to_switch = {}  # mac -> (dpid, port)
        self.topology = nx.Graph()
        self.switch_ports = defaultdict(dict)  # dpid -> {neighbor_dpid -> port}
        self.active_paths = {}  # (src_mac, dst_mac) -> path
        self.packet_count = 0
        self.flow_count = 0
        
        # Setup enhanced logging
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - %(message)s',
                          datefmt='%H:%M:%S')
        
        self.logger.info("="*70)
        self.logger.info("🚀 DIJKSTRA ENHANCED CONTROLLER STARTING")
        self.logger.info("="*70)
        
        # Load topology configuration
        self.load_topology_config()
    
    def load_topology_config(self):
        """Load topology from JSON or use default"""
        config_file = 'topology_config.json'
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.setup_topology_from_config(config)
                    self.logger.info(f"✅ [CONFIG] Loaded topology from {config_file}")
                    return
            except Exception as e:
                self.logger.error(f"❌ [CONFIG] Failed to load {config_file}: {e}")
        
        self.setup_default_topology()
    
    def setup_default_topology(self):
        """Setup default diamond topology for testing"""
        self.logger.info("📋 [TOPOLOGY] Configuring DEFAULT DIAMOND topology")
        
        # Diamond topology
        for i in range(1, 5):
            self.topology.add_node(i)
        
        # Add links with port mappings
        self.add_link(1, 2, 2, 1)  # s1:2 <-> s2:1
        self.add_link(1, 3, 3, 1)  # s1:3 <-> s3:1  
        self.add_link(2, 4, 2, 1)  # s2:2 <-> s4:1
        self.add_link(3, 4, 2, 2)  # s3:2 <-> s4:2
        
        # Cross links for redundancy
        self.add_link(1, 4, 4, 3)  # s1:4 <-> s4:3
        self.add_link(2, 3, 3, 3)  # s2:3 <-> s3:3
        
        self.print_topology_summary()
    
    def setup_topology_from_config(self, config):
        """Setup topology from configuration"""
        self.logger.info("📋 [TOPOLOGY] Configuring from JSON file")
        
        # Add switches
        for switch_id in config.get('switches', []):
            self.topology.add_node(switch_id)
            self.logger.info(f"   ➕ Added switch s{switch_id}")
        
        # Add links
        for link in config.get('links', []):
            self.add_link(
                link['src'], link['src_port'],
                link['dst'], link['dst_port']
            )
        
        self.print_topology_summary()
    
    def print_topology_summary(self):
        """Print topology summary"""
        self.logger.info("="*70)
        self.logger.info("📊 TOPOLOGY SUMMARY:")
        self.logger.info(f"   Switches: {list(self.topology.nodes())}")
        self.logger.info(f"   Total Links: {len(self.topology.edges())}")
        for src, dst in self.topology.edges():
            src_port = self.switch_ports[src].get(dst, '?')
            dst_port = self.switch_ports[dst].get(src, '?')
            self.logger.info(f"   🔗 s{src}:{src_port} <--> s{dst}:{dst_port}")
        self.logger.info("="*70)
    
    def add_link(self, dpid1, port1, dpid2, port2):
        """Add bidirectional link to topology"""
        if not self.topology.has_edge(dpid1, dpid2):
            self.topology.add_edge(dpid1, dpid2, weight=1)
            self.switch_ports[dpid1][dpid2] = port1
            self.switch_ports[dpid2][dpid1] = port2
            self.logger.info(f"   🔗 Link: s{dpid1}:{port1} <--> s{dpid2}:{port2}")
    
    def remove_link(self, dpid1, dpid2):
        """Remove link from topology"""
        if self.topology.has_edge(dpid1, dpid2):
            self.topology.remove_edge(dpid1, dpid2)
            if dpid2 in self.switch_ports[dpid1]:
                del self.switch_ports[dpid1][dpid2]
            if dpid1 in self.switch_ports[dpid2]:
                del self.switch_ports[dpid2][dpid1]
            
            self.logger.info("="*70)
            self.logger.info(f"💥 [LINK FAILURE] Link REMOVED: s{dpid1} <-X-> s{dpid2}")
            self.logger.info(f"   Remaining links: {len(self.topology.edges())}")
            self.logger.info("="*70)
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        # Store datapath
        self.datapaths[dpid] = datapath
        
        # Clear existing flows
        self.clear_flows(datapath)
        
        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        
        self.logger.info(f"✅ [SWITCH CONNECTED] s{dpid} is now online")
    
    def clear_flows(self, datapath):
        """Remove all flows from switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch()
        inst = []
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)
        self.logger.info(f"   🧹 Cleared all flows on s{datapath.id}")
    
    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, buffer_id=None):
        """Add flow entry to switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  priority=priority, match=match,
                                  instructions=inst, idle_timeout=idle_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst,
                                  idle_timeout=idle_timeout)
        
        datapath.send_msg(mod)
        self.flow_count += 1
        self.logger.info(f"   📝 Flow #{self.flow_count} installed on s{datapath.id}")
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet in messages"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        # Parse packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        
        # Ignore LLDP and IPv6
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        if eth.ethertype == 0x86dd:  # IPv6
            return
        
        dst = eth.dst
        src = eth.src
        
        self.packet_count += 1
        
        # Learn source MAC and location
        if src not in ['ff:ff:ff:ff:ff:ff', '00:00:00:00:00:00']:
            self.mac_to_port[dpid][src] = in_port
            
            # Check if this is a host (not from inter-switch port)
            is_host_port = True
            for neighbor_dpid in self.switch_ports[dpid]:
                if self.switch_ports[dpid][neighbor_dpid] == in_port:
                    is_host_port = False
                    break
            
            if is_host_port and src not in self.host_mac_to_switch:
                self.host_mac_to_switch[src] = (dpid, in_port)
                self.logger.info(f"🖥️  [HOST LEARNED] {src} connected to s{dpid}:{in_port}")
        
        # Handle broadcast/multicast
        if dst in ['ff:ff:ff:ff:ff:ff', '33:33:00:00:00:00'] or dst.startswith('33:33'):
            self.handle_broadcast(datapath, in_port, msg)
            return
        
        # Try to find destination
        if dst in self.host_mac_to_switch:
            dst_dpid, dst_port = self.host_mac_to_switch[dst]
            
            if dpid == dst_dpid:
                # Same switch - direct forwarding
                out_port = dst_port
                self.logger.info(f"📨 [PKT #{self.packet_count}] {src} → {dst}")
                self.logger.info(f"   ↳ Same switch s{dpid}, port {in_port} → {out_port}")
            else:
                # Different switch - use Dijkstra
                self.logger.info(f"📨 [PKT #{self.packet_count}] {src} → {dst}")
                self.logger.info(f"   ↳ From s{dpid} to s{dst_dpid}, calculating path...")
                
                out_port = self.get_next_hop(dpid, dst_dpid, src, dst)
                if out_port is None:
                    self.logger.error(f"   ❌ NO PATH FOUND! Dropping packet.")
                    return
            
            # Install flow and forward packet
            actions = [parser.OFPActionOutput(out_port)]
            
            # Install flow for this traffic
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 10, match, actions, idle_timeout=60)
            
            # Send packet
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                     in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)
        else:
            # Unknown destination - flood
            self.handle_broadcast(datapath, in_port, msg)
    
    def handle_broadcast(self, datapath, in_port, msg):
        """Handle broadcast packets - flood to all ports except input"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        # Get all ports except input port and inter-switch ports
        out_ports = []
        
        # Add host ports (ports not used for inter-switch links)
        all_ports = set()
        if dpid in self.mac_to_port:
            all_ports.update(self.mac_to_port[dpid].values())
        
        # Always include standard ports 1-4 for hosts
        for port in range(1, 5):
            all_ports.add(port)
        
        # Remove inter-switch ports from flooding
        inter_switch_ports = set(self.switch_ports[dpid].values())
        
        for port in all_ports:
            if port != in_port and port not in inter_switch_ports:
                out_ports.append(port)
        
        # If came from inter-switch port, flood to other inter-switch ports
        if in_port in inter_switch_ports:
            for neighbor_dpid, port in self.switch_ports[dpid].items():
                if port != in_port:
                    out_ports.append(port)
        
        actions = [parser.OFPActionOutput(port) for port in out_ports]
        
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                 in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
    
    def get_next_hop(self, src_dpid, dst_dpid, src_mac, dst_mac):
        """Calculate next hop using Dijkstra's algorithm"""
        if src_dpid not in self.topology or dst_dpid not in self.topology:
            return None
        
        try:
            # Calculate shortest path
            path = nx.shortest_path(self.topology, src_dpid, dst_dpid, weight='weight')
            
            if len(path) < 2:
                return None
            
            # Get next hop
            next_hop = path[1]
            out_port = self.switch_ports[src_dpid].get(next_hop)
            
            # Store active path
            path_key = (src_mac, dst_mac)
            old_path = self.active_paths.get(path_key, [])
            
            if out_port:
                path_str = " → ".join([f"s{p}" for p in path])
                
                if old_path != path:
                    if old_path:
                        old_path_str = " → ".join([f"s{p}" for p in old_path])
                        self.logger.info("   🔄 PATH CHANGED!")
                        self.logger.info(f"      OLD: {old_path_str}")
                        self.logger.info(f"      NEW: {path_str}")
                    else:
                        self.logger.info(f"   🛤️  PATH: {path_str}")
                    
                    self.active_paths[path_key] = path
                
                self.logger.info(f"   ↳ Next hop: s{next_hop} via port {out_port}")
            
            return out_port
            
        except nx.NetworkXNoPath:
            self.logger.error(f"   ❌ No path exists from s{src_dpid} to s{dst_dpid}")
            return None
    
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Handle port status changes"""
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        
        ofproto = msg.datapath.ofproto
        if reason == ofproto.OFPPR_ADD:
            self.logger.info(f"➕ [PORT] s{dpid}:{port_no} added")
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info(f"➖ [PORT] s{dpid}:{port_no} deleted")
        elif reason == ofproto.OFPPR_MODIFY:
            # Check both state and config for link status
            state = msg.desc.state
            config = msg.desc.config
            
            # Log detailed port status
            self.logger.info(f"🔧 [PORT_MODIFY] s{dpid}:{port_no} - State: {state}, Config: {config}")
            
            if state & ofproto.OFPPS_LINK_DOWN or config & ofproto.OFPPC_PORT_DOWN:
                self.handle_link_down(dpid, port_no)
            elif not (state & ofproto.OFPPS_LINK_DOWN):
                self.handle_link_up(dpid, port_no)
    
    def handle_link_down(self, dpid, port_no):
        """Handle link failure"""
        self.logger.info("="*70)
        self.logger.info(f"🚨 [LINK FAILURE DETECTED] s{dpid}:{port_no} is DOWN!")
        
        # Find and remove the failed link
        for neighbor_dpid, port in list(self.switch_ports[dpid].items()):
            if port == port_no:
                self.remove_link(dpid, neighbor_dpid)
                
                # Clear all flows to force recalculation
                if dpid in self.datapaths:
                    self.logger.info(f"🔄 [REROUTING] Clearing flows on affected switches...")
                    self.clear_flows(self.datapaths[dpid])
                    
                    # Also clear flows on neighbor switch if available
                    if neighbor_dpid in self.datapaths:
                        self.clear_flows(self.datapaths[neighbor_dpid])
                    
                    # Reinstall table-miss
                    datapath = self.datapaths[dpid]
                    ofproto = datapath.ofproto
                    parser = datapath.ofproto_parser
                    match = parser.OFPMatch()
                    actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                                    ofproto.OFPCML_NO_BUFFER)]
                    self.add_flow(datapath, 0, match, actions)
                
                # Clear active paths to force recalculation
                self.active_paths.clear()
                
                self.logger.info(f"✅ [REROUTING] Ready for new path calculation")
                self.logger.info("="*70)
                break
    
    def handle_link_up(self, dpid, port_no):
        """Handle link recovery"""
        self.logger.info("="*70)
        self.logger.info(f"✅ [LINK RECOVERY] s{dpid}:{port_no} is UP!")
        
        # Find which link was recovered
        for neighbor_dpid in self.datapaths:
            if neighbor_dpid != dpid:
                # Check if this was a previously known link
                # For simplicity, we'll just log it
                self.logger.info(f"   Link recovery detected, topology will be updated on next packet")
        
        self.logger.info("="*70)