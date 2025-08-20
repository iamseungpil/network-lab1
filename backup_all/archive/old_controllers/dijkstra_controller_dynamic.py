"""
Dynamic Dijkstra SDN Controller with LLDP Topology Discovery
Automatically discovers real network topology using --observe-links
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4, icmp

# Import topology discovery modules
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link, get_host

import networkx as nx
import logging
from collections import defaultdict
import time

class DijkstraControllerDynamic(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'switches': switches.Switches,
    }

    def __init__(self, *args, **kwargs):
        super(DijkstraControllerDynamic, self).__init__(*args, **kwargs)
        
        # Core data structures
        self.switches_context = kwargs['switches']
        self.datapaths = {}  # dpid -> datapath
        self.mac_to_port = defaultdict(dict)  # dpid -> {mac -> port}
        self.host_locations = {}  # mac -> (dpid, port)
        self.topology_graph = nx.Graph()
        self.switch_to_port = defaultdict(dict)  # dpid -> {neighbor_dpid -> port}
        self.packet_count = 0
        self.topology_discovered = False
        
        # Enhanced logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        
        self.logger.info("="*80)
        self.logger.info("🚀 DYNAMIC DIJKSTRA CONTROLLER WITH LLDP DISCOVERY")
        self.logger.info("="*80)
    
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
        self.remove_all_flows(datapath)
        
        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        
        self.logger.info(f"✅ Switch s{dpid} connected")
        
        # Update topology after switch connection
        self.discover_topology()
    
    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        """Handle switch enter event from topology discovery"""
        switch = ev.switch
        self.logger.info(f"🔍 [TOPOLOGY] Switch s{switch.dp.id} entered")
        self.discover_topology()
    
    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        """Handle switch leave event"""
        switch = ev.switch
        self.logger.info(f"🔍 [TOPOLOGY] Switch s{switch.dp.id} left")
        self.discover_topology()
    
    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        """Handle link add event from topology discovery"""
        link = ev.link
        src_dpid = link.src.dpid
        dst_dpid = link.dst.dpid
        src_port = link.src.port_no
        dst_port = link.dst.port_no
        
        self.logger.info(f"🔗 [TOPOLOGY] Link added: s{src_dpid}:{src_port} <-> s{dst_dpid}:{dst_port}")
        self.discover_topology()
    
    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        """Handle link delete event"""
        link = ev.link
        src_dpid = link.src.dpid
        dst_dpid = link.dst.dpid
        
        self.logger.info(f"💥 [TOPOLOGY] Link deleted: s{src_dpid} <-X-> s{dst_dpid}")
        
        # Clear flows on affected switches
        if src_dpid in self.datapaths:
            self.remove_all_flows(self.datapaths[src_dpid])
            self.install_table_miss(self.datapaths[src_dpid])
        if dst_dpid in self.datapaths:
            self.remove_all_flows(self.datapaths[dst_dpid])
            self.install_table_miss(self.datapaths[dst_dpid])
        
        self.discover_topology()
    
    def discover_topology(self):
        """Discover current network topology using Ryu API"""
        # Get all switches
        switch_list = get_switch(self.switches_context, None)
        switches = [switch.dp.id for switch in switch_list]
        
        # Get all links
        links_list = get_link(self.switches_context, None)
        
        # Rebuild topology graph
        self.topology_graph.clear()
        self.switch_to_port.clear()
        
        # Add switches to graph
        for dpid in switches:
            self.topology_graph.add_node(dpid)
        
        # Add links to graph
        for link in links_list:
            src_dpid = link.src.dpid
            dst_dpid = link.dst.dpid
            src_port = link.src.port_no
            dst_port = link.dst.port_no
            
            if not self.topology_graph.has_edge(src_dpid, dst_dpid):
                self.topology_graph.add_edge(src_dpid, dst_dpid, weight=1)
                self.switch_to_port[src_dpid][dst_dpid] = src_port
                self.switch_to_port[dst_dpid][src_dpid] = dst_port
        
        if len(switches) > 0:
            self.print_topology(switches, links_list)
            if len(links_list) > 0:
                self.topology_discovered = True
    
    def print_topology(self, switches, links):
        """Print discovered topology"""
        self.logger.info("="*80)
        self.logger.info("📊 DISCOVERED TOPOLOGY:")
        self.logger.info(f"   Switches: {switches}")
        self.logger.info(f"   Links: {len(links)} discovered")
        
        for link in links:
            src_dpid = link.src.dpid
            dst_dpid = link.dst.dpid
            src_port = link.src.port_no
            dst_port = link.dst.port_no
            self.logger.info(f"     s{src_dpid}:{src_port} <-> s{dst_dpid}:{dst_port}")
        
        self.logger.info("="*80)
    
    def remove_all_flows(self, datapath):
        """Remove all flow entries from a switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch()
        instructions = []
        flow_mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=match,
            instructions=instructions
        )
        datapath.send_msg(flow_mod)
    
    def install_table_miss(self, datapath):
        """Install table-miss flow entry"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
    
    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, hard_timeout=0):
        """Install a flow entry on a switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout
        )
        
        datapath.send_msg(mod)
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle incoming packets"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        # Parse packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        
        # Ignore LLDP packets (handled by topology discovery)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        
        # Ignore IPv6
        if eth.ethertype == 0x86dd:
            return
        
        dst_mac = eth.dst
        src_mac = eth.src
        
        self.packet_count += 1
        
        # Learn source MAC location
        self.learn_host_location(dpid, src_mac, in_port)
        
        # Handle broadcast/multicast
        if self.is_broadcast_multicast(dst_mac):
            self.flood_packet(datapath, msg, in_port)
            return
        
        # Find destination
        if dst_mac in self.host_locations:
            dst_dpid, dst_port = self.host_locations[dst_mac]
            
            if dpid == dst_dpid:
                # Same switch - direct forward
                out_port = dst_port
                self.logger.info(f"📨 PKT #{self.packet_count}: {src_mac} -> {dst_mac} (same switch s{dpid})")
            else:
                # Different switch - calculate path
                if not self.topology_discovered:
                    self.logger.warning(f"⚠️  Topology not yet discovered, dropping packet")
                    return
                
                path = self.calculate_shortest_path(dpid, dst_dpid)
                
                if not path or len(path) < 2:
                    self.logger.warning(f"❌ No path from s{dpid} to s{dst_dpid}")
                    return
                
                # Get next hop port
                next_hop = path[1]
                out_port = self.switch_to_port[dpid].get(next_hop)
                
                if not out_port:
                    self.logger.warning(f"❌ No port to next hop s{next_hop}")
                    return
                
                path_str = " -> ".join([f"s{s}" for s in path])
                self.logger.info(f"📨 PKT #{self.packet_count}: {src_mac} -> {dst_mac}")
                self.logger.info(f"  🛤️  Path: {path_str}, Next: s{next_hop} via port {out_port}")
                
                # Install flow for this path
                self.install_path_flow(dpid, src_mac, dst_mac, out_port)
            
            # Forward packet
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
        else:
            # Unknown destination - flood
            self.flood_packet(datapath, msg, in_port)
    
    def learn_host_location(self, dpid, mac, port):
        """Learn and track host locations"""
        if mac in ['ff:ff:ff:ff:ff:ff', '00:00:00:00:00:00']:
            return
        
        # Check if this is a host port (not inter-switch)
        is_host_port = True
        for neighbor_dpid in self.switch_to_port.get(dpid, {}):
            if self.switch_to_port[dpid][neighbor_dpid] == port:
                is_host_port = False
                break
        
        if is_host_port:
            if mac not in self.host_locations:
                self.host_locations[mac] = (dpid, port)
                self.logger.info(f"🖥️  Learned host {mac} at s{dpid}:{port}")
            elif self.host_locations[mac] != (dpid, port):
                # Host moved
                old_dpid, old_port = self.host_locations[mac]
                self.host_locations[mac] = (dpid, port)
                self.logger.info(f"🔄 Host {mac} moved from s{old_dpid}:{old_port} to s{dpid}:{port}")
        
        # Always update MAC table
        self.mac_to_port[dpid][mac] = port
    
    def is_broadcast_multicast(self, mac):
        """Check if MAC is broadcast or multicast"""
        return mac in ['ff:ff:ff:ff:ff:ff', '33:33:00:00:00:00'] or mac.startswith('33:33')
    
    def flood_packet(self, datapath, msg, in_port):
        """Flood packet to all ports except input"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        # Get all active ports except input and inter-switch ports
        out_ports = []
        
        # Add host ports (1-10, typically)
        for port in range(1, 11):
            if (port != in_port and 
                port not in self.switch_to_port.get(dpid, {}).values()):
                out_ports.append(port)
        
        # If packet came from host, also flood to inter-switch ports
        if in_port not in self.switch_to_port.get(dpid, {}).values():
            for neighbor_dpid, port in self.switch_to_port.get(dpid, {}).items():
                if port != in_port:
                    out_ports.append(port)
        
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
    
    def calculate_shortest_path(self, src_dpid, dst_dpid):
        """Calculate shortest path using Dijkstra's algorithm"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        try:
            path = nx.shortest_path(self.topology_graph, src_dpid, dst_dpid, weight='weight')
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def install_path_flow(self, dpid, src_mac, dst_mac, out_port):
        """Install flow entry for this path"""
        if dpid not in self.datapaths:
            return
        
        datapath = self.datapaths[dpid]
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
        actions = [parser.OFPActionOutput(out_port)]
        
        self.add_flow(datapath, 10, match, actions, idle_timeout=30)