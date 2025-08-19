"""
Dijkstra SDN Controller - Single controller with Dijkstra routing
Handles link failures and rerouting
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

class DijkstraController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DijkstraController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.mac_to_dpid = {}  # Track which switch each MAC is connected to
        self.topology = nx.Graph()
        self.switch_ports = defaultdict(dict)  # Track port connections
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - %(message)s',
                          datefmt='%H:%M:%S')
        self.logger.info("[DIJKSTRA] Controller started")
        
        # Manually configure initial topology
        self.setup_initial_topology()
    
    def setup_initial_topology(self):
        """Manually configure the initial network topology"""
        self.logger.info("[SETUP] Configuring initial topology...")
        
        # Diamond topology with loop
        # s1 -- s2
        # |  X  |
        # s3 -- s4
        # Plus additional switches s5, s6
        
        # Core diamond links
        self.add_link(1, 3, 3, 3)  # s1 <-> s3 (direct link)
        self.add_link(1, 4, 2, 3)  # s1 <-> s2
        self.add_link(2, 4, 4, 3)  # s2 <-> s4  
        self.add_link(3, 4, 4, 4)  # s3 <-> s4
        
        # Additional paths for redundancy
        self.add_link(1, 5, 5, 3)  # s1 <-> s5
        self.add_link(5, 4, 3, 5)  # s5 <-> s3
        self.add_link(4, 5, 5, 5)  # s4 <-> s5
        self.add_link(3, 6, 6, 3)  # s3 <-> s6
        
        edges = list(self.topology.edges())
        self.logger.info(f"[SETUP] Initial topology configured: {edges}")

    def add_link(self, dpid1, port1, dpid2, port2):
        """Add a link to topology"""
        if not self.topology.has_edge(dpid1, dpid2):
            self.topology.add_edge(dpid1, dpid2, weight=1)
            self.switch_ports[dpid1][dpid2] = port1
            self.switch_ports[dpid2][dpid1] = port2
            self.logger.info(f"[TOPOLOGY] Added link: s{dpid1}:{port1} <-> s{dpid2}:{port2}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        # Store datapath
        self.datapaths[dpid] = datapath
        self.topology.add_node(dpid)
        self.logger.info(f"[SWITCH] s{dpid} connected")
        
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
                                  instructions=inst, idle_timeout=60)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst, idle_timeout=60)
        datapath.send_msg(mod)

    def get_path(self, src_dpid, dst_dpid):
        """Calculate shortest path using Dijkstra"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        if src_dpid not in self.topology or dst_dpid not in self.topology:
            self.logger.warning(f"[PATH] s{src_dpid} or s{dst_dpid} not in topology")
            return None
            
        try:
            # Show current topology state
            edges = list(self.topology.edges())
            self.logger.info(f"[TOPOLOGY] Current links: {edges}")
            
            path = nx.shortest_path(self.topology, src_dpid, dst_dpid, weight='weight')
            path_str = " -> ".join([f"s{dpid}" for dpid in path])
            self.logger.info(f"[DIJKSTRA] ✓ Shortest path: {path_str} (hops: {len(path)-1})")
            return path
        except nx.NetworkXNoPath:
            self.logger.error(f"[DIJKSTRA] ✗ NO PATH available from s{src_dpid} to s{dst_dpid}")
            return None

    def get_out_port(self, current_dpid, next_dpid):
        """Get output port for next hop"""
        if next_dpid in self.switch_ports[current_dpid]:
            return self.switch_ports[current_dpid][next_dpid]
        return None

    def install_path(self, path, src_mac, dst_mac):
        """Install flow rules along the entire path"""
        self.logger.info(f"[FLOW_INSTALL] Installing flows for {src_mac} -> {dst_mac}")
        
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
            
            # Install flow for this MAC pair
            match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 10, match, actions)
            
            self.logger.info(f"[FLOW_INSTALL] s{curr_dpid}: {src_mac}->{dst_mac} via port {out_port} to s{next_dpid}")
            
            # Also install reverse flow for bidirectional communication
            match = parser.OFPMatch(eth_dst=src_mac, eth_src=dst_mac)
            if i > 0:
                prev_dpid = path[i - 1]
                in_port = self.get_out_port(curr_dpid, prev_dpid)
                if in_port:
                    actions = [parser.OFPActionOutput(in_port)]
                    self.add_flow(datapath, 10, match, actions)
                    self.logger.info(f"[FLOW_INSTALL] s{curr_dpid}: {dst_mac}->{src_mac} via port {in_port} (reverse)")

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
        
        # Ignore LLDP
        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return
            
        dst_mac = eth_pkt.dst
        src_mac = eth_pkt.src
        
        # Learn MAC location
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port
        self.mac_to_dpid[src_mac] = dpid
        
        # Determine output port
        if dst_mac in self.mac_to_dpid:
            dst_dpid = self.mac_to_dpid[dst_mac]
            
            if dpid == dst_dpid:
                # Same switch
                if dst_mac in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst_mac]
                    self.logger.info(f"[PACKET_IN] Same switch routing: s{dpid} -> port {out_port}")
                else:
                    out_port = ofproto.OFPP_FLOOD
            else:
                # Different switch - use Dijkstra
                self.logger.warning(f"[PACKET_IN] 📨 s{dpid} received packet {src_mac}->{dst_mac}, need path to s{dst_dpid}")
                path = self.get_path(dpid, dst_dpid)
                if path and len(path) > 1:
                    next_dpid = path[1]
                    out_port = self.get_out_port(dpid, next_dpid)
                    if out_port:
                        self.logger.info(f"[PACKET_IN] ✓ Routing via port {out_port} to s{next_dpid}")
                        # Install flows for the entire path
                        self.install_path(path, src_mac, dst_mac)
                    else:
                        out_port = ofproto.OFPP_FLOOD
                        self.logger.warning(f"[PACKET_IN] ✗ No port found to s{next_dpid}, flooding")
                else:
                    out_port = ofproto.OFPP_FLOOD
                    self.logger.error(f"[PACKET_IN] ✗ NO PATH found from s{dpid} to s{dst_dpid}, flooding")
        else:
            # Unknown destination - flood
            out_port = ofproto.OFPP_FLOOD
            self.logger.info(f"[PACKET_IN] Unknown destination {dst_mac}, flooding")
        
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
        """Handle port status changes (link failures)"""
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto
        
        if reason == ofproto.OFPPR_ADD:
            self.logger.info(f"[OPENFLOW] 🔗 PORT_STATUS: s{dpid}:{port_no} UP")
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.error(f"[OPENFLOW] ❌ PORT_STATUS: s{dpid}:{port_no} DOWN - Link failure detected!")
            # Remove link from topology
            self.handle_link_failure(dpid, port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info(f"[OPENFLOW] 🔧 PORT_STATUS: s{dpid}:{port_no} modified")

    def handle_link_failure(self, dpid, port_no):
        """Handle link failure by updating topology"""
        self.logger.warning(f"[REROUTING] 🔍 Analyzing link failure on s{dpid}:{port_no}")
        
        # Find which switch was connected to this port
        for other_dpid in list(self.switch_ports[dpid].keys()):
            if self.switch_ports[dpid][other_dpid] == port_no:
                # Remove the link
                if self.topology.has_edge(dpid, other_dpid):
                    self.logger.error(f"[REROUTING] 💥 Removing failed link: s{dpid} <-> s{other_dpid}")
                    
                    self.topology.remove_edge(dpid, other_dpid)
                    del self.switch_ports[dpid][other_dpid]
                    if dpid in self.switch_ports[other_dpid]:
                        del self.switch_ports[other_dpid][dpid]
                    
                    remaining_edges = list(self.topology.edges())
                    self.logger.warning(f"[TOPOLOGY] Updated topology: {remaining_edges}")
                    
                    # Clear all flows to trigger rerouting
                    self.clear_flows_all()
                break

    def clear_flows_all(self):
        """Clear flows on all switches for rerouting"""
        self.logger.warning("[REROUTING] 🧹 Clearing all flows to force path recalculation")
        for dpid, datapath in self.datapaths.items():
            self.logger.info(f"[REROUTING] Clearing flows on s{dpid}")
            self.clear_flows(datapath)
        self.logger.info("[REROUTING] ✓ All flows cleared - next PACKET_IN will trigger Dijkstra")

    def clear_flows(self, datapath):
        """Clear all flows except table-miss"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Delete all flows with priority > 0
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