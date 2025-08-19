"""
Final Dijkstra Controller with automatic topology learning
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.topology import event
from ryu.topology.api import get_all_switch, get_all_link
import networkx as nx
import logging
from collections import defaultdict

class FinalDijkstraController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FinalDijkstraController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.mac_to_dpid = {}
        self.topology = nx.Graph()
        self.switch_ports = defaultdict(dict)
        self.host_mac_to_switch = {}
        
        # Logging setup
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)7s] %(message)s',
            datefmt='%H:%M:%S'
        )
        
        self.logger.info("="*60)
        self.logger.info("  FINAL DIJKSTRA CONTROLLER WITH AUTO-TOPOLOGY")
        self.logger.info("="*60)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        self.datapaths[dpid] = datapath
        self.topology.add_node(dpid)
        self.logger.info(f"✅ Switch s{dpid} connected")
        
        # Install table-miss flow
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Add flow to switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  priority=priority, match=match,
                                  instructions=inst, idle_timeout=30)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst, idle_timeout=30)
        datapath.send_msg(mod)

    def discover_topology(self, src_dpid, dst_dpid, src_port, dst_port):
        """Discover and add link to topology"""
        if not self.topology.has_edge(src_dpid, dst_dpid):
            self.topology.add_edge(src_dpid, dst_dpid, weight=1)
            self.switch_ports[src_dpid][dst_dpid] = src_port
            self.switch_ports[dst_dpid][src_dpid] = dst_port
            self.logger.info(f"🔗 Discovered link: s{src_dpid}:{src_port} <-> s{dst_dpid}:{dst_port}")
            
            # Log topology stats
            nodes = self.topology.number_of_nodes()
            edges = self.topology.number_of_edges()
            self.logger.info(f"   Topology: {nodes} switches, {edges} links")

    def get_path(self, src, dst):
        """Calculate shortest path"""
        if src == dst:
            return [src]
        
        if src not in self.topology or dst not in self.topology:
            return None
        
        try:
            path = nx.shortest_path(self.topology, src, dst, weight='weight')
            path_str = " → ".join([f"s{d}" for d in path])
            self.logger.info(f"📍 Path: {path_str} ({len(path)-1} hops)")
            return path
        except nx.NetworkXNoPath:
            self.logger.warning(f"❌ No path from s{src} to s{dst}")
            return None

    def install_path(self, path, src_mac, dst_mac):
        """Install flows along path"""
        self.logger.info(f"📝 Installing flows: {src_mac} -> {dst_mac}")
        
        for i in range(len(path) - 1):
            curr = path[i]
            next = path[i + 1]
            
            if curr not in self.datapaths:
                continue
            
            out_port = self.switch_ports[curr].get(next)
            if not out_port:
                continue
            
            datapath = self.datapaths[curr]
            parser = datapath.ofproto_parser
            
            # Install flow
            match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 10, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet in"""
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
        
        dst = eth_pkt.dst
        src = eth_pkt.src
        
        # Learn MAC location
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port
        
        # Learn host location (assuming hosts have specific MAC pattern)
        if src not in self.host_mac_to_switch:
            self.host_mac_to_switch[src] = dpid
            self.mac_to_dpid[src] = dpid
        
        # Try to discover inter-switch links
        if src in self.mac_to_dpid and self.mac_to_dpid[src] != dpid:
            # Packet from another switch - discover link
            src_dpid = self.mac_to_dpid[src]
            if src_dpid in self.mac_to_port and src in self.mac_to_port[src_dpid]:
                src_port = self.mac_to_port[src_dpid][src]
                self.discover_topology(src_dpid, dpid, src_port, in_port)
        
        # Determine output
        if dst[:5] in ['33:33', 'ff:ff', '01:00']:
            out_port = ofproto.OFPP_FLOOD
        elif dst in self.mac_to_dpid:
            dst_dpid = self.mac_to_dpid[dst]
            
            if dpid == dst_dpid:
                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                else:
                    out_port = ofproto.OFPP_FLOOD
            else:
                # Calculate path
                path = self.get_path(dpid, dst_dpid)
                if path and len(path) > 1:
                    next_dpid = path[1]
                    out_port = self.switch_ports[dpid].get(next_dpid, ofproto.OFPP_FLOOD)
                    
                    if out_port != ofproto.OFPP_FLOOD:
                        self.install_path(path, src, dst)
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
            self.logger.info(f"✅ Port UP: s{dpid}:{port_no}")
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.warning(f"❌ Port DOWN: s{dpid}:{port_no}")
            self.handle_link_failure(dpid, port_no)

    def handle_link_failure(self, dpid, port_no):
        """Handle link failure"""
        self.logger.warning(f"⚠️ LINK FAILURE at s{dpid}:{port_no}")
        
        # Find and remove failed link
        for neighbor in list(self.switch_ports[dpid].keys()):
            if self.switch_ports[dpid][neighbor] == port_no:
                if self.topology.has_edge(dpid, neighbor):
                    self.topology.remove_edge(dpid, neighbor)
                    del self.switch_ports[dpid][neighbor]
                    if dpid in self.switch_ports[neighbor]:
                        del self.switch_ports[neighbor][dpid]
                    
                    self.logger.error(f"💥 Removed link: s{dpid} <-> s{neighbor}")
                    
                    # Clear flows
                    self.clear_all_flows()
                break

    def clear_all_flows(self):
        """Clear all flows for rerouting"""
        self.logger.info("🔄 Clearing flows for rerouting...")
        
        for dpid, datapath in self.datapaths.items():
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            
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