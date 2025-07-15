#!/usr/bin/env python3
"""
Gateway-based Secondary Controller
게이트웨이 기반 Secondary Controller - 간결하고 효율적인 구현
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types


class GatewaySecondaryController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(GatewaySecondaryController, self).__init__(*args, **kwargs)
        
        # 관리할 스위치 DPID (s6-s10)
        self.managed_switches = {6, 7, 8, 9, 10}
        
        # L2 학습 테이블: {dpid: {mac: port}}
        self.mac_to_port = {}
        self.datapaths = {}
        self.global_mac_table = {}  # {mac: (dpid, port)} - 전역 MAC 테이블
        
        # 스위치 간 연결 정보 (토폴로지 맵)
        self.switch_links = {
            6: {3: 3},           # s6: s3(port3)
            7: {3: 3},           # s7: s3(port3)
            8: {4: 3},           # s8: s4(port3)
            9: {4: 3},           # s9: s4(port3)
            10: {5: 3}           # s10: s5(port3)
        }
        
        # 게이트웨이 방식: Primary 도메인으로의 게이트웨이 포트
        self.primary_gateway = {
            'port': 3,  # 모든 Secondary 스위치는 포트 3으로 Primary와 연결
            'switches': [6, 7, 8, 9, 10]  # 모든 Secondary 스위치가 게이트웨이 역할
        }
        
        self.logger.info("Gateway Secondary Controller initialized - managing switches s6-s10")

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

        # Table-miss flow entry 설치
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
        """패킷이 컨트롤러로 전송될 때 호출"""
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

        # LLDP 패킷 무시
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        # 브로드캐스트/멀티캐스트 처리 (로그 생략)
        if dst == 'ff:ff:ff:ff:ff:ff' or dst.startswith('33:33:'):
            out_port = ofproto.OFPP_FLOOD
            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                    in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)
            return

        # 유니캐스트 패킷만 로그 출력
        self.logger.info(f"[SECONDARY-PACKET] {src} → {dst} on s{dpid}:{in_port}")

        # MAC 주소 학습
        if src not in self.mac_to_port[dpid]:
            self.mac_to_port[dpid][src] = in_port
            self.global_mac_table[src] = (dpid, in_port)
            self.logger.info(f"[SECONDARY-LEARN] {src} learned at s{dpid}:{in_port}")

        # 목적지 MAC 주소에 따른 포워딩 결정
        if dst in self.mac_to_port[dpid]:
            # 같은 스위치 내 로컬 전달
            out_port = self.mac_to_port[dpid][dst]
            # 로컬 전달은 로그 생략
        elif dst in self.global_mac_table:
            # 다른 Secondary 스위치로 전달
            target_dpid, target_port = self.global_mac_table[dst]
            out_port = self._find_next_hop(dpid, target_dpid)
            self.logger.info(f"[SECONDARY-ROUTE] s{dpid} → s{target_dpid} via port {out_port}")
        elif self._is_primary_domain(dst):
            # Primary 도메인 → 게이트웨이로 전달
            out_port = self._get_gateway_port_to_primary(dpid)
            self.logger.info(f"[SECONDARY-GATEWAY] s{dpid} → Primary via gateway port {out_port}")
        else:
            # 알 수 없는 목적지 - 플러딩 (로그 생략)
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # 플로우 설치 (flooding이 아닌 경우에만)
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            self.logger.info(f"[SECONDARY-FLOW] s{dpid}: {src}→{dst} installed (port {out_port})")
            return

        # Packet Out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def _is_primary_domain(self, mac):
        """MAC 주소를 보고 Primary 도메인인지 판단"""
        try:
            # MAC 주소 마지막 바이트를 추출
            mac_int = int(mac.replace(':', ''), 16) & 0xFF
            # Primary 도메인: 0x01~0x0a (h1~h10)
            return 0x01 <= mac_int <= 0x0a
        except ValueError:
            return False

    def _find_next_hop(self, current_dpid, target_dpid):
        """목표 스위치로 가는 다음 홉 찾기"""
        if current_dpid == target_dpid:
            return None
            
        # Secondary 영역은 트리 구조가 단순함
        # 모든 Secondary 스위치는 Primary를 통해 서로 통신
        return self.primary_gateway['port']

    def _get_gateway_port_to_primary(self, dpid):
        """Primary 도메인으로 가는 게이트웨이 포트 찾기"""
        # 모든 Secondary 스위치는 포트 3을 통해 Primary로 연결됨
        return self.primary_gateway['port']

    def get_status(self):
        """컨트롤러 상태 반환"""
        return {
            'controller': 'gateway_secondary',
            'managed_switches': list(self.managed_switches),
            'connected_switches': list(self.datapaths.keys()),
            'learned_macs': {f's{dpid}': len(mac_table) 
                           for dpid, mac_table in self.mac_to_port.items()},
            'gateway_port': self.primary_gateway['port'],
            'gateway_switches': self.primary_gateway['switches']
        }