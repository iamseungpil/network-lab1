"""
Final Dijkstra SDN Controller with Complete Link Failure Handling
Fully functional with dynamic topology changes and automatic rerouting
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4, icmp
from ryu.topology import event as topo_event
from ryu.topology.api import get_all_switch, get_all_link
import networkx as nx
import logging
from collections import defaultdict
import json
import os
from datetime import datetime
import threading
import time

class DijkstraControllerFinal(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {}

    def __init__(self, *args, **kwargs):
        super(DijkstraControllerFinal, self).__init__(*args, **kwargs)
        
        # Core data structures
        self.datapaths = {}  # dpid -> datapath
        self.mac_to_port = defaultdict(dict)  # dpid -> {mac -> port}
        self.host_locations = {}  # mac -> (dpid, port)
        self.topology_graph = nx.Graph()
        self.switch_ports = defaultdict(dict)  # dpid -> {neighbor_dpid -> port}
        self.port_to_switch = defaultdict(dict)  # dpid -> {port -> neighbor_dpid}
        self.active_flows = defaultdict(list)  # dpid -> list of flows
        self.packet_count = 0
        self.topology_discovered = False
        self.failed_links = set()  # Track failed links
        
        # Setup enhanced logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        
        self.logger.info("="*80)
        self.logger.info("🚀 DIJKSTRA FINAL CONTROLLER INITIALIZED")
        self.logger.info("="*80)
        
        # Load static topology configuration
        self.load_topology_config()
    
    def load_topology_config(self):
        """Load topology from JSON configuration file"""
        config_file = 'topology_config.json'
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.setup_static_topology(config)
                    self.logger.info(f"✅ Loaded topology from {config_file}")
                    return
            except Exception as e:
                self.logger.error(f"❌ Failed to load config: {e}")
        
        # Default diamond topology if no config
        self.setup_default_topology()
    
    def setup_default_topology(self):
        """Setup default diamond topology"""
        self.logger.info("📋 Configuring DEFAULT DIAMOND topology")
        
        # Add switches
        for i in range(1, 5):
            self.topology_graph.add_node(i)
        
        # Add links with port mappings
        links = [
            (1, 2, 2, 1),  # s1:2 <-> s2:1
            (1, 3, 3, 1),  # s1:3 <-> s3:1
            (2, 4, 2, 1),  # s2:2 <-> s4:1
            (3, 4, 2, 2),  # s3:2 <-> s4:2
            (1, 4, 4, 3),  # s1:4 <-> s4:3 (direct)
            (2, 3, 3, 3),  # s2:3 <-> s3:3 (cross)
        ]
        
        for dpid1, dpid2, port1, port2 in links:
            self.add_static_link(dpid1, dpid2, port1, port2)
        
        self.print_topology()
    
    def setup_static_topology(self, config):
        """Setup topology from configuration"""
        # Add switches
        for switch_id in config.get('switches', []):
            self.topology_graph.add_node(switch_id)
            self.logger.info(f"  Added switch s{switch_id}")
        
        # Add links
        for link in config.get('links', []):
            self.add_static_link(
                link['src'], link['dst'],
                link['src_port'], link['dst_port']
            )
        
        self.print_topology()
    
    def add_static_link(self, dpid1, dpid2, port1, port2):
        """Add a static link to topology"""
        if not self.topology_graph.has_edge(dpid1, dpid2):
            self.topology_graph.add_edge(dpid1, dpid2, weight=1)
            self.switch_ports[dpid1][dpid2] = port1
            self.switch_ports[dpid2][dpid1] = port2
            self.port_to_switch[dpid1][port1] = dpid2
            self.port_to_switch[dpid2][port2] = dpid1
            self.logger.info(f"  Link: s{dpid1}:{port1} <-> s{dpid2}:{port2}")
    
    def print_topology(self):
        """Print current topology status"""
        self.logger.info("="*80)
        self.logger.info("📊 CURRENT TOPOLOGY:")
        self.logger.info(f"  Switches: {list(self.topology_graph.nodes())}")
        self.logger.info(f"  Active Links: {len(self.topology_graph.edges())}")
        
        for src, dst in self.topology_graph.edges():
            src_port = self.switch_ports[src].get(dst, '?')
            dst_port = self.switch_ports[dst].get(src, '?')
            status = "❌ FAILED" if (src, dst) in self.failed_links or (dst, src) in self.failed_links else "✅ ACTIVE"
            self.logger.info(f"    s{src}:{src_port} <-> s{dst}:{dst_port} {status}")
        
        if self.failed_links:
            self.logger.info(f"  Failed Links: {len(self.failed_links)}")
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
        
        # Check if all switches are connected
        if len(self.datapaths) == len(self.topology_graph.nodes()):
            self.logger.info("🎉 All switches connected!")
            self.topology_discovered = True
    
    def remove_all_flows(self, datapath):
        """Remove all flow entries from a switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Delete all flows
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
        self.logger.info(f"  🧹 Cleared all flows on s{datapath.id}")
    
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
        
        # Ignore LLDP
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
                path = self.calculate_path(dpid, dst_dpid)
                
                if not path or len(path) < 2:
                    self.logger.warning(f"❌ No path from s{dpid} to s{dst_dpid}")
                    return
                
                # Get next hop port
                next_hop = path[1]
                out_port = self.switch_ports[dpid].get(next_hop)
                
                if not out_port:
                    self.logger.warning(f"❌ No port to next hop s{next_hop}")
                    return
                
                path_str = " -> ".join([f"s{s}" for s in path])
                self.logger.info(f"📨 PKT #{self.packet_count}: {src_mac} -> {dst_mac}")
                self.logger.info(f"  Path: {path_str}, Next: s{next_hop} via port {out_port}")
                
                # Install flow for efficiency
                self.install_path_flows(path, src_mac, dst_mac, in_port)
            
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
        if port not in self.port_to_switch.get(dpid, {}):
            # This is a host port
            if mac not in self.host_locations:
                self.host_locations[mac] = (dpid, port)
                self.logger.info(f"🖥️  Learned host {mac} at s{dpid}:{port}")
            elif self.host_locations[mac] != (dpid, port):
                # Host moved
                old_dpid, old_port = self.host_locations[mac]
                self.host_locations[mac] = (dpid, port)
                self.logger.info(f"🔄 Host {mac} moved from s{old_dpid}:{old_port} to s{dpid}:{port}")
        
        # Always remember the port for MAC learning
        self.mac_to_port[dpid][mac] = port
    
    def is_broadcast_multicast(self, mac):
        """Check if MAC is broadcast or multicast"""
        return mac in ['ff:ff:ff:ff:ff:ff', '33:33:00:00:00:00'] or mac.startswith('33:33')
    
    def flood_packet(self, datapath, msg, in_port):
        """Flood packet to all ports except input"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        # Get all active ports
        out_ports = []
        
        # Add all ports except input and inter-switch ports
        for port in range(1, 10):  # Check ports 1-9
            if port != in_port:
                # Check if it's an inter-switch port
                if port not in self.port_to_switch.get(dpid, {}):
                    out_ports.append(port)
        
        # Also flood to inter-switch ports if packet came from host
        if in_port not in self.port_to_switch.get(dpid, {}):
            for neighbor, port in self.switch_ports.get(dpid, {}).items():
                if port != in_port and (dpid, neighbor) not in self.failed_links:
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
    
    def calculate_path(self, src_dpid, dst_dpid):
        """Calculate shortest path using Dijkstra's algorithm"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        # Create a copy of the graph without failed links
        working_graph = self.topology_graph.copy()
        for failed_link in self.failed_links:
            if working_graph.has_edge(failed_link[0], failed_link[1]):
                working_graph.remove_edge(failed_link[0], failed_link[1])
        
        try:
            path = nx.shortest_path(working_graph, src_dpid, dst_dpid, weight='weight')
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def install_path_flows(self, path, src_mac, dst_mac, src_port):
        """Install flow entries along a path"""
        for i in range(len(path) - 1):
            curr_dpid = path[i]
            next_dpid = path[i + 1]
            
            if curr_dpid not in self.datapaths:
                continue
            
            datapath = self.datapaths[curr_dpid]
            parser = datapath.ofproto_parser
            
            # Get output port
            out_port = self.switch_ports[curr_dpid].get(next_dpid)
            if not out_port:
                continue
            
            # Install flow
            match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
            actions = [parser.OFPActionOutput(out_port)]
            
            self.add_flow(datapath, 10, match, actions, idle_timeout=30)
    
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Handle port status changes"""
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        
        ofproto = msg.datapath.ofproto
        
        if reason == ofproto.OFPPR_ADD:
            self.logger.info(f"➕ Port s{dpid}:{port_no} added")
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info(f"➖ Port s{dpid}:{port_no} deleted")
        elif reason == ofproto.OFPPR_MODIFY:
            # Check port state
            state = msg.desc.state
            config = msg.desc.config
            
            is_down = (state & ofproto.OFPPS_LINK_DOWN) or (config & ofproto.OFPPC_PORT_DOWN)
            
            if is_down:
                self.handle_port_down(dpid, port_no)
            else:
                self.handle_port_up(dpid, port_no)
    
    def handle_port_down(self, dpid, port_no):
        """Handle port/link failure"""
        # Find the affected link
        neighbor_dpid = self.port_to_switch.get(dpid, {}).get(port_no)
        
        if neighbor_dpid:
            self.logger.info("="*80)
            self.logger.info(f"🚨 LINK FAILURE DETECTED: s{dpid}:{port_no} <-X-> s{neighbor_dpid}")
            
            # Mark link as failed
            self.failed_links.add((dpid, neighbor_dpid))
            self.failed_links.add((neighbor_dpid, dpid))
            
            # Remove from active topology
            if self.topology_graph.has_edge(dpid, neighbor_dpid):
                self.topology_graph.remove_edge(dpid, neighbor_dpid)
            
            # Clear flows on affected switches to force recalculation
            self.clear_affected_flows(dpid, neighbor_dpid)
            
            self.logger.info(f"✅ Topology updated, flows cleared for rerouting")
            self.print_topology()
    
    def handle_port_up(self, dpid, port_no):
        """Handle port/link recovery"""
        neighbor_dpid = self.port_to_switch.get(dpid, {}).get(port_no)
        
        if neighbor_dpid:
            self.logger.info("="*80)
            self.logger.info(f"✅ LINK RECOVERED: s{dpid}:{port_no} <--> s{neighbor_dpid}")
            
            # Remove from failed links
            self.failed_links.discard((dpid, neighbor_dpid))
            self.failed_links.discard((neighbor_dpid, dpid))
            
            # Restore to topology
            if not self.topology_graph.has_edge(dpid, neighbor_dpid):
                self.topology_graph.add_edge(dpid, neighbor_dpid, weight=1)
            
            # Clear flows to use new paths
            self.clear_affected_flows(dpid, neighbor_dpid)
            
            self.logger.info(f"✅ Link restored, topology updated")
            self.print_topology()
    
    def clear_affected_flows(self, dpid1, dpid2):
        """Clear flows on affected switches"""
        for dpid in [dpid1, dpid2]:
            if dpid in self.datapaths:
                datapath = self.datapaths[dpid]
                self.remove_all_flows(datapath)
                
                # Reinstall table-miss
                ofproto = datapath.ofproto
                parser = datapath.ofproto_parser
                match = parser.OFPMatch()
                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                                ofproto.OFPCML_NO_BUFFER)]
                self.add_flow(datapath, 0, match, actions)
        
        self.logger.info(f"  🧹 Cleared flows on s{dpid1} and s{dpid2}")
    
    @set_ev_cls(ofp_event.EventOFPErrorMsg, MAIN_DISPATCHER)
    def error_msg_handler(self, ev):
        """Handle OpenFlow error messages"""
        msg = ev.msg
        self.logger.error(f"⚠️  OFPErrorMsg: type=0x{msg.type:02x} code=0x{msg.code:02x}")
    
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        """Handle flow statistics reply"""
        dpid = ev.msg.datapath.id
        flows = []
        
        for stat in ev.msg.body:
            flows.append({
                'priority': stat.priority,
                'match': stat.match,
                'packets': stat.packet_count,
                'bytes': stat.byte_count
            })
        
        self.active_flows[dpid] = flows