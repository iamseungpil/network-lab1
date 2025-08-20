"""
Fixed Primary Controller - Actually works!
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
import networkx as nx
import logging

class PrimaryFixed(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PrimaryFixed, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.my_switches = {1, 2, 3, 4, 5}  # Primary domain
        self.topology = self._build_topology()
        
        logging.basicConfig(level=logging.INFO)
        self.logger.info("[PRIMARY-FIXED] Controller started")

    def _build_topology(self):
        """Build topology with loop"""
        G = nx.Graph()
        
        # Primary domain topology
        edges = [
            (1, 2, 1), (1, 3, 1),
            (2, 4, 1), (2, 5, 1),
            (4, 3, 2),  # Backup path
        ]
        
        for src, dst, weight in edges:
            G.add_edge(src, dst, weight=weight)
            
        return G

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        if dpid not in self.my_switches:
            return
            
        self.datapaths[dpid] = datapath
        self.logger.info(f"[PRIMARY-FIXED] Switch s{dpid} connected")
        
        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        if dpid not in self.my_switches:
            return
            
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]
        
        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return
            
        dst = eth_pkt.dst
        src = eth_pkt.src
        
        # Learn MAC address
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port
        
        # Find output port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            self.logger.info(f"[PRIMARY-FIXED] s{dpid}: {src} -> {dst} via port {out_port}")
        else:
            out_port = ofproto.OFPP_FLOOD
            self.logger.info(f"[PRIMARY-FIXED] s{dpid}: Flooding for {dst}")
        
        actions = [parser.OFPActionOutput(out_port)]
        
        # Install flow
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
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
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto
        
        if dpid not in self.my_switches:
            return
            
        if reason == ofproto.OFPPR_ADD:
            self.logger.info(f"[PRIMARY-FIXED][PORT] s{dpid} port {port_no} added")
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.warning(f"[PRIMARY-FIXED][PORT] s{dpid} port {port_no} deleted")
            # Clear MAC table entries for this port
            if dpid in self.mac_to_port:
                to_delete = []
                for mac, port in self.mac_to_port[dpid].items():
                    if port == port_no:
                        to_delete.append(mac)
                for mac in to_delete:
                    del self.mac_to_port[dpid][mac]
                    self.logger.info(f"[PRIMARY-FIXED] Removed MAC {mac} from s{dpid}")
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info(f"[PRIMARY-FIXED][PORT] s{dpid} port {port_no} modified")