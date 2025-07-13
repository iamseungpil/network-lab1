#!/usr/bin/env python3
"""
Secondary Controller - 로컬 실행용
스위치 s6-s10 관리하는 RYU L2 학습 스위치
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types


class SecondaryController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SecondaryController, self).__init__(*args, **kwargs)
        
        # 관리할 스위치 DPID (s6-s10)
        self.managed_switches = {6, 7, 8, 9, 10}
        
        # L2 학습 테이블: {dpid: {mac: port}}
        self.mac_to_port = {}
        self.datapaths = {}
        self.global_mac_table = {}  # {mac: (dpid, port)} - 전역 MAC 테이블
        
        # 스위치 간 연결 정보 (토폴로지 맵)
        self.switch_links = {
            6: {3: 3},                # s6: s3(port3)
            7: {3: 3},                # s7: s3(port3)
            8: {4: 3},                # s8: s4(port3)
            9: {4: 3},                # s9: s4(port3)
            10: {5: 3}                # s10: s5(port3)
        }
        
        self.logger.info("Secondary Controller initialized - managing switches s6-s10")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """새로운 스위치가 연결될 때 호출"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # 관리 대상 스위치인지 확인
        if dpid not in self.managed_switches:
            self.logger.info(f"Switch s{dpid} not managed by Secondary Controller")
            return

        # 스위치 등록
        self.datapaths[dpid] = datapath
        self.mac_to_port.setdefault(dpid, {})
        
        self.logger.info(f"Secondary Controller: Switch s{dpid} connected successfully")

        # Table-miss flow entry 설치 (매칭되지 않는 패킷은 컨트롤러로 전송)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        
        self.logger.info(f"Table-miss flow installed on switch s{dpid}")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """플로우 엔트리 추가"""
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
        """패킷이 컨트롤러로 전송될 때 호출 (L2 학습 스위치 로직)"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        # 관리 대상 스위치가 아니면 무시
        if dpid not in self.managed_switches:
            return

        # 패킷 파싱
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # LLDP 패킷 무시 (링크 발견용)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        self.logger.info(f"Secondary: Packet from {src} to {dst} on switch s{dpid} port {in_port}")

        # MAC 주소 학습 (이미 학습된 포트와 다른 경우만 업데이트)
        if src not in self.mac_to_port[dpid]:
            self.mac_to_port[dpid][src] = in_port
            self.global_mac_table[src] = (dpid, in_port)  # 전역 테이블 업데이트
            self.logger.info(f"Secondary: Learned {src} is at s{dpid} port {in_port}")
        elif self.mac_to_port[dpid][src] != in_port:
            # MAC 이동 감지
            self.logger.info(f"Secondary: MAC {src} moved from port {self.mac_to_port[dpid][src]} to port {in_port} on s{dpid}")
            self.mac_to_port[dpid][src] = in_port
            self.global_mac_table[src] = (dpid, in_port)

        # 목적지 MAC 주소에 따른 포워딩 결정
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            self.logger.info(f"Secondary: Forwarding to known location - s{dpid} port {out_port}")
        else:
            # 개선된 크로스 컨트롤러 포워딩 로직
            out_port = self._find_path_to_destination(dpid, dst)
            if out_port is not None:
                self.logger.info(f"Secondary: Forwarding to remote destination via s{dpid} port {out_port}")
            else:
                out_port = ofproto.OFPP_FLOOD
                self.logger.info(f"Secondary: Unknown destination {dst} - flooding on s{dpid}")

        actions = [parser.OFPActionOutput(out_port)]

        # 플로우 설치 (flooding이 아닌 경우에만)
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            self.logger.info(f"Secondary: Flow rule installed on s{dpid}")
            return

        # Packet Out (즉시 패킷 전송)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
        self.logger.info(f"Secondary: Packet sent out on s{dpid}")

    def _get_cross_controller_port(self, dpid, dst_mac):
        """크로스 컨트롤러 포워딩을 위한 포트 결정"""
        # h1-h10은 Primary controller 영역 (MAC: 00:00:00:00:00:01 ~ 00:00:00:00:00:0a)
        if dst_mac >= '00:00:00:00:00:01' and dst_mac <= '00:00:00:00:00:0a':
            # Primary 영역으로 가는 경로 계산
            if dpid == 6 or dpid == 7:  # s6, s7에서 s3을 통해
                return 3  # s6-eth3 -> s3 or s7-eth3 -> s3
            elif dpid == 8 or dpid == 9:  # s8, s9에서 s4를 통해
                return 3  # s8-eth3 -> s4 or s9-eth3 -> s4
            elif dpid == 10:  # s10에서 s5를 통해
                return 3  # s10-eth3 -> s5
        return None
    
    def _find_path_to_destination(self, current_dpid, dst_mac):
        """목적지까지의 최적 경로 찾기"""
        if dst_mac in self.global_mac_table:
            target_dpid, target_port = self.global_mac_table[dst_mac]
            if target_dpid in self.switch_links.get(current_dpid, {}):
                return self.switch_links[current_dpid][target_dpid]
        return self._get_cross_controller_port(current_dpid, dst_mac)

    def get_status(self):
        """컨트롤러 상태 반환"""
        return {
            'controller': 'secondary',
            'managed_switches': list(self.managed_switches),
            'connected_switches': list(self.datapaths.keys()),
            'learned_macs': {f's{dpid}': len(mac_table) 
                           for dpid, mac_table in self.mac_to_port.items()}
        }
