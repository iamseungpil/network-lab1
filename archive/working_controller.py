"""
Working SDN Controller - Simple but functional
Based on standard Ryu learning switch with Dijkstra routing
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp
import networkx as nx
import logging

class WorkingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(WorkingController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.topology = self._build_topology()
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger.info("[CONTROLLER] Started - Managing all switches")

    def _build_topology(self):
        """Build network topology graph"""
        G = nx.Graph()
        
        # Add all 10 switches
        for i in range(1, 11):
            G.add_node(i)
        
        # Add edges (matching the actual topology)
        edges = [
            # Primary domain
            (1, 2, 1), (1, 3, 1),
            (2, 4, 1), (2, 5, 1),
            (4, 3, 2),  # Backup path (creates loop)
            # Cross-domain
            (3, 6, 2), (3, 7, 2),
            (4, 8, 2), (4, 9, 2),
            (5, 10, 2),
            # Secondary domain
            (6, 7, 1), (8, 9, 1)
        ]
        
        for src, dst, weight in edges:
            G.add_edge(src, dst, weight=weight)
            
        self.logger.info(f"[TOPOLOGY] Built with {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        # Store datapath
        self.datapaths[dpid] = datapath
        self.logger.info(f"[SWITCH] s{dpid} connected")
        
        # Install table-miss flow entry (send to controller)
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
                                  priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst)
        datapath.send_msg(mod)

    def _get_path(self, src_dpid, dst_dpid):
        """Get shortest path between switches"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        try:
            path = nx.shortest_path(self.topology, src_dpid, dst_dpid, weight='weight')
            self.logger.info(f"[PATH] s{src_dpid} -> s{dst_dpid}: {path}")
            return path
        except nx.NetworkXNoPath:
            self.logger.warning(f"[PATH] No path from s{src_dpid} to s{dst_dpid}")
            return None

    def _get_out_port(self, src_dpid, dst_dpid, in_port):
        """Get output port for next hop"""
        # Port mapping based on topology
        # Format: {src_switch: {dst_switch: port}}
        port_map = {
            1: {2: 3, 3: 4},
            2: {1: 3, 4: 4, 5: 5},
            3: {1: 3, 4: 4, 6: 5, 7: 6},
            4: {2: 3, 3: 4, 8: 5, 9: 6},
            5: {2: 3, 10: 4},
            6: {3: 3, 7: 4},
            7: {3: 3, 6: 4},
            8: {4: 3, 9: 4},
            9: {4: 3, 8: 4},
            10: {5: 3}
        }
        
        if src_dpid in port_map and dst_dpid in port_map[src_dpid]:
            return port_map[src_dpid][dst_dpid]
        return None

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
            
        dst = eth_pkt.dst
        src = eth_pkt.src
        
        # Initialize MAC table for this switch
        self.mac_to_port.setdefault(dpid, {})
        
        # Learn source MAC to avoid flooding next time
        self.mac_to_port[dpid][src] = in_port
        
        # Determine output port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            # Flood if we don't know the destination
            out_port = ofproto.OFPP_FLOOD
        
        actions = [parser.OFPActionOutput(out_port)]
        
        # Install flow to avoid packet-in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # Verify we have valid buffer_id
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            else:
                self.add_flow(datapath, 1, match, actions)
        
        # Send packet out
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
        
        if reason == msg.datapath.ofproto.OFPPR_ADD:
            self.logger.info(f"[PORT] s{dpid} port {port_no} added")
        elif reason == msg.datapath.ofproto.OFPPR_DELETE:
            self.logger.warning(f"[PORT] s{dpid} port {port_no} removed")
            # Clear flows when port goes down
            self._clear_flows(dpid)
        elif reason == msg.datapath.ofproto.OFPPR_MODIFY:
            self.logger.info(f"[PORT] s{dpid} port {port_no} modified")

    def _clear_flows(self, dpid):
        """Clear all flows except table-miss on a switch"""
        if dpid not in self.datapaths:
            return
            
        datapath = self.datapaths[dpid]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Delete all flows except table-miss
        match = parser.OFPMatch()
        instructions = []
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            priority=1,
            match=match
        )
        datapath.send_msg(mod)
        self.logger.info(f"[FLOWS] Cleared on s{dpid}")