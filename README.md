# SDN Multi-Controller Lab with Cross-Controller Communication

크로스 컨트롤러 통신을 지원하는 다중 컨트롤러 SDN 환경입니다.

## 개요

이 프로젝트는 10개의 OpenFlow 스위치와 20개의 호스트를 사용하여 두 개의 독립적인 RYU 컨트롤러가 서로 다른 네트워크 영역을 관리하는 SDN 환경을 구현합니다. **Enhanced Controllers**를 통해 크로스 컨트롤러 통신을 지원합니다.

### 네트워크 구성
- **Primary Controller (포트 6700)**: 스위치 s1-s5 관리
- **Secondary Controller (포트 6800)**: 스위치 s6-s10 관리
- **호스트**: 각 스위치에 2개씩 총 20개 (h1-h20)
- **토폴로지**: 트리 구조 (s1이 루트)
- **크로스 컨트롤러 통신**: 지원 ✅

## 빠른 시작

```bash
# 1. 환경 설정 (최초 1회)
conda create -n sdn-lab python=3.9 -y
conda activate sdn-lab
pip install setuptools==57.5.0
pip install -r requirements.txt
sudo apt-get install -y mininet openvswitch-switch

# 2. SDN 환경 실행
chmod +x start_sdn.sh stop_sdn.sh
./start_sdn.sh
```

## 네트워크 토폴로지

```
                    s1 (Primary)
                   /         \
                 s2           s3
                / \          /  \
              s4   s5      s6   s7  ← 컨트롤러 경계
             / \    |       (Secondary)
           s8   s9  s10         

컨트롤러 할당:
- Primary Controller (포트 6700): s1, s2, s3, s4, s5
- Secondary Controller (포트 6800): s6, s7, s8, s9, s10

크로스 컨트롤러 게이트웨이:
- s3 ↔ s6, s7 (Primary ↔ Secondary)
- s4 ↔ s8, s9 (Primary ↔ Secondary)
- s5 ↔ s10 (Primary ↔ Secondary)
```

## 사용 방법

### Mininet CLI 명령어

```bash
# 기본 연결성 테스트 (같은 컨트롤러 내)
h1 ping -c 3 h2    # Primary 내부 통신
h11 ping -c 3 h12  # Secondary 내부 통신

# 크로스 컨트롤러 통신 (ARP 설정 필요)
h1 arp -s 10.0.0.11 00:00:00:00:00:0b
h11 arp -s 10.0.0.1 00:00:00:00:00:01
h1 ping -c 3 h11   # Primary ↔ Secondary 통신 ✅

# 네트워크 정보 확인
net          # 토폴로지 확인
dump         # 노드 정보
links        # 링크 정보

# 플로우 테이블 확인
sh ovs-ofctl -O OpenFlow13 dump-flows s1
sh ovs-ofctl -O OpenFlow13 dump-flows s3  # 게이트웨이 스위치
sh ovs-ofctl -O OpenFlow13 dump-flows s6

# 전체 연결성 테스트
pingall      # 모든 호스트 간 통신 테스트
```

### 호스트 정보

| 호스트 | IP 주소 | MAC 주소 | 스위치 | 컨트롤러 |
|--------|---------|----------|--------|----------|
| h1-h2 | 10.0.0.1-2 | 00:00:00:00:00:01-02 | s1 | Primary |
| h3-h4 | 10.0.0.3-4 | 00:00:00:00:00:03-04 | s2 | Primary |
| h5-h6 | 10.0.0.5-6 | 00:00:00:00:00:05-06 | s3 | Primary |
| h7-h8 | 10.0.0.7-8 | 00:00:00:00:00:07-08 | s4 | Primary |
| h9-h10 | 10.0.0.9-10 | 00:00:00:00:00:09-0a | s5 | Primary |
| h11-h12 | 10.0.0.11-12 | 00:00:00:00:00:0b-0c | s6 | Secondary |
| h13-h14 | 10.0.0.13-14 | 00:00:00:00:00:0d-0e | s7 | Secondary |
| h15-h16 | 10.0.0.15-16 | 00:00:00:00:00:0f-10 | s8 | Secondary |
| h17-h18 | 10.0.0.17-18 | 00:00:00:00:00:11-12 | s9 | Secondary |
| h19-h20 | 10.0.0.19-20 | 00:00:00:00:00:13-14 | s10 | Secondary |

## 크로스 컨트롤러 통신

### 구현 방식
1. **Enhanced Controllers**: 각 컨트롤러가 상대방 영역의 호스트 정보를 사전 정의
2. **게이트웨이 라우팅**: 
   - Primary → Secondary: s3(→s6,s7), s4(→s8,s9), s5(→s10)
   - Secondary → Primary: 모든 Secondary 스위치는 포트 3으로 연결
3. **플로우 룰 자동 설치**: 패킷 수신 시 경로 계산 후 플로우 룰 설치

### 테스트 예제

```bash
# 크로스 컨트롤러 통신 테스트 시나리오

# 1. h1 (s1, Primary) → h11 (s6, Secondary)
h1 arp -s 10.0.0.11 00:00:00:00:00:0b
h11 arp -s 10.0.0.1 00:00:00:00:00:01
h1 ping -c 5 h11

# 2. h5 (s3, Primary) → h15 (s8, Secondary)
h5 arp -s 10.0.0.15 00:00:00:00:00:0f
h15 arp -s 10.0.0.5 00:00:00:00:00:05
h5 ping -c 5 h15

# 3. h10 (s5, Primary) → h20 (s10, Secondary)
h10 arp -s 10.0.0.20 00:00:00:00:00:14
h20 arp -s 10.0.0.10 00:00:00:00:00:0a
h10 ping -c 5 h20
```

### 제한사항 및 개선 방안
- **현재 제한**: ARP 브로드캐스트가 컨트롤러 경계를 넘지 않음
- **해결 방법**: 수동 ARP 설정 또는 ARP 프록시 구현
- **프로덕션 환경**: 컨트롤러 간 REST API 통신으로 MAC 테이블 공유

## 파일 구조

```
network-lab1/
├── README.md                      # 이 파일
├── requirements.txt               # Python 의존성
├── start_sdn.sh                  # SDN 환경 시작 스크립트
├── stop_sdn.sh                   # SDN 환경 종료 스크립트
├── lab_assignments.md            # 실습 과제
├── ryu-controller/
│   ├── enhanced_primary.py       # Primary Controller (크로스 통신 지원)
│   └── enhanced_secondary.py     # Secondary Controller (크로스 통신 지원)
└── mininet/
    ├── topology.py               # Mininet 토폴로지 정의
    ├── test_connectivity.py      # 연결성 테스트 스크립트
    └── test_scenarios.py         # 시나리오 테스트 스크립트
```

## 설치 및 환경 설정

### 필수 요구사항
- Ubuntu 20.04 이상
- Python 3.9 (권장)
- Conda (Miniforge 권장)
- sudo 권한

### 상세 설치 과정

```bash
# 1. Conda 환경 생성
conda create -n sdn-lab python=3.9 -y
conda activate sdn-lab

# 2. Python 패키지 설치
pip install setuptools==57.5.0  # RYU와 호환되는 버전
pip install -r requirements.txt

# 3. 시스템 패키지 설치
sudo apt-get update
sudo apt-get install -y mininet openvswitch-switch

# 4. 설치 확인
ryu-manager --version  # ryu-manager 4.34
sudo mn --test pingall # Mininet 동작 확인
```

## 문제 해결

### 1. eventlet 오류
```bash
# eventlet 버전 문제 해결
pip install eventlet==0.30.2
```

### 2. setuptools 오류
```bash
# RYU 설치 시 setuptools 호환성 문제
pip install setuptools==57.5.0
```

### 3. Mininet 모듈 없음
```bash
# 시스템 레벨 Mininet 설치 필요
sudo apt-get install -y mininet
```

### 4. 크로스 컨트롤러 통신 실패
```bash
# ARP 엔트리 수동 추가
h1 arp -s <target_ip> <target_mac>

# 플로우 테이블 확인
sh ovs-ofctl -O OpenFlow13 dump-flows <switch>

# 컨트롤러 로그 확인
# Primary/Secondary Controller 터미널에서 로그 확인
```

## 고급 테스트

### 성능 테스트
```bash
# 대역폭 측정
iperf h1 h11

# 다중 경로 테스트
h1 ping h11 &
h5 ping h15 &
h10 ping h20 &
```

### 플로우 분석
```bash
# 특정 스위치의 플로우 통계
sh ovs-ofctl -O OpenFlow13 dump-flows s3

# 플로우 카운터 확인
sh ovs-ofctl -O OpenFlow13 dump-flows s1 | grep n_packets

# 모든 스위치 플로우 확인
for i in {1..10}; do 
    echo "=== Switch s$i ==="
    sh ovs-ofctl -O OpenFlow13 dump-flows s$i
done
```

## 종료

```bash
# Mininet CLI에서
exit

# 또는 별도 터미널에서
./stop_sdn.sh

# 수동 정리 (필요시)
sudo pkill -f ryu-manager
sudo mn -c
```

## 학습 목표

1. **Multi-Controller SDN**: 분산 컨트롤러 아키텍처 이해
2. **Cross-Controller Communication**: 컨트롤러 간 통신 구현
3. **L2 Learning Switch**: MAC 주소 학습 및 포워딩
4. **OpenFlow 1.3**: 플로우 룰 설치 및 관리
5. **Network Segmentation**: 네트워크 도메인 분리 및 관리

## 라이선스

교육 목적으로 자유롭게 사용 가능합니다.