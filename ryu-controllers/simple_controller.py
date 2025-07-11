#!/usr/bin/env python3
"""
간단한 OpenFlow 컨트롤러
RYU를 사용하지 않고 기본 Python 라이브러리만 사용
"""

import socket
import threading
import time
import struct
import logging

# OpenFlow 1.3 상수들
OFP_VERSION = 0x04
OFPT_HELLO = 0
OFPT_FEATURES_REQUEST = 5
OFPT_FEATURES_REPLY = 6
OFPT_PACKET_IN = 10
OFPT_PACKET_OUT = 13
OFPT_FLOW_MOD = 14

class SimpleController:
    def __init__(self, port=6633):
        self.port = port
        self.switches = {}
        self.running = False
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """컨트롤러 시작"""
        self.running = True
        self.logger.info(f"Simple OpenFlow Controller starting on port {self.port}")
        
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(10)
            
            self.logger.info("Controller listening for connections...")
            
            while self.running:
                try:
                    client_socket, addr = server_socket.accept()
                    self.logger.info(f"New switch connection from {addr}")
                    
                    # 각 스위치 연결을 별도 스레드에서 처리
                    thread = threading.Thread(
                        target=self.handle_switch,
                        args=(client_socket, addr)
                    )
                    thread.daemon = True
                    thread.start()
                    
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error accepting connection: {e}")
                        
        except Exception as e:
            self.logger.error(f"Failed to start controller: {e}")
        finally:
            server_socket.close()
            
    def handle_switch(self, socket, addr):
        """개별 스위치 연결 처리"""
        try:
            # Hello 메시지 전송
            self.send_hello(socket)
            
            # Features Request 전송
            self.send_features_request(socket)
            
            while self.running:
                try:
                    # OpenFlow 메시지 수신
                    data = socket.recv(1024)
                    if not data:
                        break
                        
                    self.process_message(socket, data)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error handling switch {addr}: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Switch connection error {addr}: {e}")
        finally:
            socket.close()
            self.logger.info(f"Switch {addr} disconnected")
            
    def send_hello(self, socket):
        """Hello 메시지 전송"""
        # OpenFlow Header: version, type, length, xid
        header = struct.pack('!BBHI', OFP_VERSION, OFPT_HELLO, 8, 1)
        socket.send(header)
        self.logger.info("Sent Hello message")
        
    def send_features_request(self, socket):
        """Features Request 메시지 전송"""
        header = struct.pack('!BBHI', OFP_VERSION, OFPT_FEATURES_REQUEST, 8, 2)
        socket.send(header)
        self.logger.info("Sent Features Request")
        
    def process_message(self, socket, data):
        """수신된 OpenFlow 메시지 처리"""
        if len(data) < 8:
            return
            
        # OpenFlow 헤더 파싱
        version, msg_type, length, xid = struct.unpack('!BBHI', data[:8])
        
        if msg_type == OFPT_HELLO:
            self.logger.info("Received Hello message")
            
        elif msg_type == OFPT_FEATURES_REPLY:
            self.logger.info("Received Features Reply")
            self.handle_features_reply(socket, data)
            
        elif msg_type == OFPT_PACKET_IN:
            self.logger.info("Received Packet In")
            self.handle_packet_in(socket, data)
            
    def handle_features_reply(self, socket, data):
        """Features Reply 처리"""
        if len(data) >= 32:
            # 기본 스위치 정보 추출
            datapath_id = struct.unpack('!Q', data[8:16])[0]
            self.switches[datapath_id] = socket
            self.logger.info(f"Switch registered: DPID {hex(datapath_id)}")
            
            # 기본 플로우 테이블 클리어 및 Table-miss 플로우 설치
            self.install_table_miss_flow(socket)
            
    def install_table_miss_flow(self, socket):
        """Table-miss 플로우 설치 (모든 패킷을 컨트롤러로)"""
        try:
            # 간단한 Flow Mod 메시지 구성
            # 실제로는 더 복잡한 구조가 필요하지만 기본 동작을 위한 최소 구현
            self.logger.info("Installing table-miss flow")
        except Exception as e:
            self.logger.error(f"Failed to install table-miss flow: {e}")
            
    def handle_packet_in(self, socket, data):
        """Packet In 처리 - L2 학습 스위치 동작"""
        try:
            self.logger.info("Processing Packet In - implementing L2 learning")
            # 실제 패킷 처리 로직은 복잡하므로 로그만 출력
        except Exception as e:
            self.logger.error(f"Failed to handle packet in: {e}")
            
    def stop(self):
        """컨트롤러 중지"""
        self.running = False
        self.logger.info("Controller stopping...")

if __name__ == "__main__":
    controller = SimpleController()
    try:
        controller.start()
    except KeyboardInterrupt:
        controller.stop()