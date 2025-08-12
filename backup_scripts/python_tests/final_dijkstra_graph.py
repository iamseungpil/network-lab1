#!/usr/bin/env python3
"""
Final Dijkstra Graph Controller - Enhanced for 10-switch graph topology
Simple L2 learning with controlled ARP flooding + Dijkstra routing for loops
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp
import networkx as nx
from collections import defaultdict
import time


class FinalDijkstraGraphController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FinalDijkstraGraphController, self).__init__(*args, **kwargs)
        
        # MAC learning table {dpid: {mac: port}}
        self.mac_to_port = defaultdict(dict)
        
        # Complete host database (all 20 hosts for 10-switch topology)
        self.host_db = {
            '10.0.0.1': ('00:00:00:00:00:01', 1, 1),   # h1 at s1 port 1
            '10.0.0.2': ('00:00:00:00:00:02', 1, 2),   # h2 at s1 port 2
            '10.0.0.3': ('00:00:00:00:00:03', 2, 1),   # h3 at s2 port 1
            '10.0.0.4': ('00:00:00:00:00:04', 2, 2),   # h4 at s2 port 2
            '10.0.0.5': ('00:00:00:00:00:05', 3, 1),   # h5 at s3 port 1
            '10.0.0.6': ('00:00:00:00:00:06', 3, 2),   # h6 at s3 port 2
            '10.0.0.7': ('00:00:00:00:00:07', 4, 1),   # h7 at s4 port 1
            '10.0.0.8': ('00:00:00:00:00:08', 4, 2),   # h8 at s4 port 2
            '10.0.0.9': ('00:00:00:00:00:09', 5, 1),   # h9 at s5 port 1
            '10.0.0.10': ('00:00:00:00:00:0a', 5, 2),  # h10 at s5 port 2
            '10.0.0.11': ('00:00:00:00:00:0b', 6, 1),  # h11 at s6 port 1
            '10.0.0.12': ('00:00:00:00:00:0c', 6, 2),  # h12 at s6 port 2
            '10.0.0.13': ('00:00:00:00:00:0d', 7, 1),  # h13 at s7 port 1
            '10.0.0.14': ('00:00:00:00:00:0e', 7, 2),  # h14 at s7 port 2
            '10.0.0.15': ('00:00:00:00:00:0f', 8, 1),  # h15 at s8 port 1
            '10.0.0.16': ('00:00:00:00:00:10', 8, 2),  # h16 at s8 port 2
            '10.0.0.17': ('00:00:00:00:00:11', 9, 1),  # h17 at s9 port 1
            '10.0.0.18': ('00:00:00:00:00:12', 9, 2),  # h18 at s9 port 2
            '10.0.0.19': ('00:00:00:00:00:13', 10, 1), # h19 at s10 port 1
            '10.0.0.20': ('00:00:00:00:00:14', 10, 2), # h20 at s10 port 2
        }
        
        # Build topology graph for Dijkstra
        self.graph = self._build_10_switch_graph()
        
        # Port mapping for 10-switch graph topology 
        # {dpid: {neighbor_dpid: port}}
        self.port_mapping = self._build_port_mapping()
        
        # ARP proxy table
        self.arp_table = {}
        
        # ARP request rate limiting {(src_ip, dst_ip): timestamp}
        self.arp_timestamps = {}
        
        self.logger.info("=== Final Dijkstra Graph Controller Started ===")
        self.logger.info("Simple L2 learning with controlled ARP flooding")
        if self.graph:
            self.logger.info("10-Switch Graph: %d nodes, %d edges", 
                           self.graph.number_of_nodes(), 
                           self.graph.number_of_edges())
            self.logger.info("Graph edges: %s", list(self.graph.edges))
        self.logger.info("Host database: %d hosts", len(self.host_db))

    def _build_10_switch_graph(self):
        """Build 10-switch graph topology for Dijkstra calculations"""
        try:
            G = nx.Graph()
            
            # Add 10 switches
            for i in range(1, 11):
                G.add_node(i)
            
            # Add edges for graph topology with loops (same as topology file)
            edges = [
                # Ring topology (main 10-switch loop)
                (1, 2, 1), (2, 3, 1), (3, 4, 1), (4, 5, 1), (5, 6, 1),
                (6, 7, 1), (7, 8, 1), (8, 9, 1), (9, 10, 1), (10, 1, 1),
                
                # Cross connections (diagonal paths)
                (1, 6, 2), (2, 7, 2), (3, 8, 2), (4, 9, 2), (5, 10, 2),
                
                # Additional mesh connections  
                (1, 4, 3), (2, 5, 3), (3, 6, 3), (7, 10, 3), (8, 1, 3),
                
                # More crosses
                (2, 9, 4), (3, 10, 4),
            ]
            
            for s1, s2, weight in edges:
                G.add_edge(s1, s2, weight=weight)
            
            return G
        except ImportError:
            self.logger.warning("NetworkX not available, using simple L2")
            return None

    def _build_port_mapping(self):
        """Build static port mapping for 10-switch topology"""
        # Simplified mapping: host ports 1,2, switch ports start from 3
        mapping = {}
        for dpid in range(1, 11):
            mapping[dpid] = {}
            port = 3  # Start from port 3 (ports 1,2 for hosts)
            
            # Add all neighbors from graph
            if self.graph and dpid in self.graph:
                for neighbor in self.graph.neighbors(dpid):
                    mapping[dpid][neighbor] = port
                    port += 1
                    
        return mapping

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        self.logger.info("Switch %s connected", dpid)

        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                         ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=0):
        """Add flow to switch"""
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

    def get_dijkstra_next_hop(self, src_dpid, dst_dpid):
        """Get next hop using Dijkstra algorithm"""
        if not self.graph or src_dpid == dst_dpid:
            return None
            
        try:
            path = nx.shortest_path(self.graph, src_dpid, dst_dpid, weight='weight')
            if len(path) > 1:
                next_hop = path[1]
                port = self.port_mapping.get(src_dpid, {}).get(next_hop)
                self.logger.debug("Dijkstra s%s->s%s: path=%s, next_hop=s%s, port=%s", 
                               src_dpid, dst_dpid, path, next_hop, port)
                return next_hop, port
        except:
            self.logger.warning("No path found from s%s to s%s", src_dpid, dst_dpid)
            
        return None, None

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Handle packet in events"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        dst = eth.dst
        src = eth.src

        # Learn source MAC address
        self.mac_to_port[dpid][src] = in_port

        # Handle ARP with proxy capabilities
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            arp_pkt = pkt.get_protocol(arp.arp)
            if arp_pkt:
                # Update ARP table
                self.arp_table[arp_pkt.src_ip] = arp_pkt.src_mac
                
                if arp_pkt.opcode == arp.ARP_REQUEST:
                    self.logger.info("ARP Request: %s->%s at s%d", 
                                   arp_pkt.src_ip, arp_pkt.dst_ip, dpid)
                    
                    # Rate limit ARP requests
                    current_time = time.time()
                    arp_key = (arp_pkt.src_ip, arp_pkt.dst_ip)
                    
                    if arp_key in self.arp_timestamps:
                        if current_time - self.arp_timestamps[arp_key] < 1:
                            return
                    
                    self.arp_timestamps[arp_key] = current_time
                    
                    # ARP Proxy using host database
                    if arp_pkt.dst_ip in self.host_db:
                        dst_mac, dst_dpid, dst_port = self.host_db[arp_pkt.dst_ip]
                        self.logger.info("ARP Proxy reply for %s", arp_pkt.dst_ip)
                        self.send_arp_reply(datapath, in_port, arp_pkt, dst_mac)
                        return

        # Determine output port
        out_port = None
        
        if dst in self.mac_to_port[dpid]:
            # Direct forwarding (same switch)
            out_port = self.mac_to_port[dpid][dst]
            self.logger.debug("Direct: %s at s%d port %d", dst, dpid, out_port)
        else:
            # Try to route to destination switch using Dijkstra
            dst_dpid = self._find_host_switch(dst)
            if dst_dpid and dst_dpid != dpid:
                next_hop, port = self.get_dijkstra_next_hop(dpid, dst_dpid)
                if port:
                    out_port = port
                    self.logger.info("Cross-switch communication: s%d->s%d (%s->%s)", 
                                   dpid, dst_dpid, src[-5:], dst[-5:])

        # Default to flooding if no specific route found
        if not out_port:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow to avoid packet_in next time (avoid broadcasts)
        if (out_port != ofproto.OFPP_FLOOD and 
            not dst.startswith('ff:ff') and not dst.startswith('01:00')):
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 10, match, actions, msg.buffer_id, 30)
                return
            else:
                self.add_flow(datapath, 10, match, actions, idle_timeout=30)

        # Send packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                 in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def _find_host_switch(self, mac):
        """Find which switch a host is connected to based on MAC"""
        for ip, (host_mac, dpid, port) in self.host_db.items():
            if host_mac == mac:
                return dpid
        return None

    def send_arp_reply(self, datapath, port, arp_req, target_mac):
        """Send ARP reply as proxy"""
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        
        # Build ARP reply
        e = ethernet.ethernet(dst=arp_req.src_mac, src=target_mac,
                             ethertype=ether_types.ETH_TYPE_ARP)
        a = arp.arp(opcode=arp.ARP_REPLY,
                   src_mac=target_mac, src_ip=arp_req.dst_ip,
                   dst_mac=arp_req.src_mac, dst_ip=arp_req.src_ip)
        
        p = packet.Packet()
        p.add_protocol(e)
        p.add_protocol(a)
        p.serialize()
        
        # Send out
        actions = [parser.OFPActionOutput(port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                 buffer_id=ofproto.OFP_NO_BUFFER,
                                 in_port=ofproto.OFPP_CONTROLLER,
                                 actions=actions, data=p.data)
        datapath.send_msg(out)