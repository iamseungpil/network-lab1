# SDN Multi-Controller Lab with Cross-Controller Communication

크로스 컨트롤러 통신을 지원하는 다중 컨트롤러 SDN 환경입니다.

## 🚀 완전한 설치 가이드

### 1단계: Ubuntu VM 설치

#### VirtualBox/VMware 사용
```bash
# Ubuntu 20.04 LTS 이상 권장
# 최소 사양:
#   - RAM: 4GB 이상
#   - 디스크: 20GB 이상
#   - CPU: 2코어 이상
#   - 네트워크: NAT 또는 Bridge 모드

# Ubuntu 설치 후 필수 패키지
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim build-essential
```

#### AWS EC2/클라우드 사용
```bash
# Ubuntu 20.04 LTS AMI 선택
# 인스턴스 타입: t3.medium 이상 권장
# 보안 그룹: SSH(22) 포트 오픈

# 접속 후
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim
```

### 2단계: Conda 설치

#### Miniforge 설치 (권장)
```bash
# Miniforge 다운로드 및 설치
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
chmod +x Miniforge3-Linux-x86_64.sh
./Miniforge3-Linux-x86_64.sh

# 설치 중 옵션:
# - 설치 경로: /home/ubuntu/miniforge3 (기본값)
# - conda init 실행: yes

# 터미널 재시작 또는
source ~/.bashrc

# 설치 확인
conda --version
```

#### 기존 Anaconda/Miniconda가 있는 경우
```bash
# 기존 conda 환경 확인
conda info
conda env list

# 충돌 방지를 위해 base 환경 비활성화 (선택사항)
conda config --set auto_activate_base false
```

### 3단계: 프로젝트 클론 및 환경 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd network-lab1

# Conda 환경 생성
conda create -n sdn-lab python=3.9 -y
conda activate sdn-lab

# Python 패키지 설치
pip install setuptools==57.5.0  # RYU 호환성을 위한 중요한 단계
pip install eventlet==0.30.2    # eventlet 버전 고정
pip install -r requirements.txt

# 시스템 패키지 설치
sudo apt-get update
sudo apt-get install -y mininet openvswitch-switch

# 설치 확인
ryu-manager --version    # ryu-manager 4.34 확인
sudo mn --test pingall   # Mininet 동작 확인 (간단한 테스트)
```

### 4단계: 권한 설정

```bash
# 실행 권한 부여
chmod +x start_sdn.sh stop_sdn.sh

# sudo 권한 확인 (Mininet 실행에 필요)
sudo -v

# 사용자를 docker 그룹에 추가 (Docker 사용 시)
sudo usermod -aG docker $USER
newgrp docker  # 또는 로그아웃 후 재로그인
```

### 5단계: 환경 테스트

```bash
# 모든 구성 요소 테스트
./start_sdn.sh

# 성공 시 Mininet CLI가 나타남:
# mininet>

# 기본 연결성 테스트
mininet> net
mininet> pingall
mininet> exit
```

## 개요

이 프로젝트는 10개의 OpenFlow 스위치와 20개의 호스트를 사용하여 두 개의 독립적인 RYU 컨트롤러가 서로 다른 네트워크 영역을 관리하는 SDN 환경을 구현합니다. **Enhanced Controllers**를 통해 크로스 컨트롤러 통신을 지원합니다.

### 네트워크 구성
- **Primary Controller (포트 6700)**: 스위치 s1-s5 관리
- **Secondary Controller (포트 6800)**: 스위치 s6-s10 관리
- **호스트**: 각 스위치에 2개씩 총 20개 (h1-h20)
- **토폴로지**: 트리 구조 (s1이 루트)
- **크로스 컨트롤러 통신**: 지원 ✅

## ⚡ 빠른 시작 (환경 설정 완료 후)

```bash
# Conda 환경 활성화
conda activate sdn-lab

# SDN 환경 실행
./start_sdn.sh

# 성공 시 Mininet CLI 진입:
# mininet> 
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

## 🧪 테스트 방법

### 1단계: 기본 연결성 테스트

```bash
# SDN 환경 시작
./start_sdn.sh

# Mininet CLI에서 기본 테스트
mininet> net          # 네트워크 토폴로지 확인
mininet> nodes        # 노드 목록 확인
mininet> links        # 링크 상태 확인
mininet> dump         # 모든 노드 정보

# 같은 컨트롤러 내 통신 테스트 (ARP 설정 불필요)
mininet> h1 ping -c 3 h2    # Primary 내부 (s1)
mininet> h3 ping -c 3 h4    # Primary 내부 (s2)
mininet> h11 ping -c 3 h12  # Secondary 내부 (s6)
mininet> h13 ping -c 3 h14  # Secondary 내부 (s7)
```

### 2단계: 크로스 컨트롤러 통신 테스트

#### 테스트 시나리오 A: h1(Primary) ↔ h11(Secondary)
```bash
# ARP 테이블 수동 설정
mininet> h1 arp -s 10.0.0.11 00:00:00:00:00:0b
mininet> h11 arp -s 10.0.0.1 00:00:00:00:00:01

# 양방향 통신 테스트
mininet> h1 ping -c 5 h11     # Primary → Secondary
mininet> h11 ping -c 5 h1     # Secondary → Primary

# 기대 결과: 5 packets transmitted, 5 received, 0% packet loss
```

#### 테스트 시나리오 B: h5(Primary-s3) ↔ h15(Secondary-s8)
```bash
# 게이트웨이 스위치 테스트 (s3 ↔ s8)
mininet> h5 arp -s 10.0.0.15 00:00:00:00:00:0f
mininet> h15 arp -s 10.0.0.5 00:00:00:00:00:05
mininet> h5 ping -c 5 h15
mininet> h15 ping -c 5 h5
```

#### 테스트 시나리오 C: h10(Primary-s5) ↔ h20(Secondary-s10)
```bash
# 최단 경로 테스트 (s5 ↔ s10 직접 연결)
mininet> h10 arp -s 10.0.0.20 00:00:00:00:00:14
mininet> h20 arp -s 10.0.0.10 00:00:00:00:00:0a
mininet> h10 ping -c 5 h20
mininet> h20 ping -c 5 h10
```

### 3단계: 성능 및 Flow 분석

#### 대역폭 테스트
```bash
# iperf를 이용한 대역폭 측정
mininet> iperf h1 h11         # 크로스 컨트롤러 대역폭
mininet> iperf h1 h2          # 같은 컨트롤러 대역폭 (비교용)

# 기대 결과: 10Mbps 정도 (가상 환경)
```

#### Flow 테이블 분석
```bash
# OpenFlow 룰 확인
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s3  # 게이트웨이
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s6

# Flow 통계 확인
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1 | grep n_packets

# 모든 스위치 Flow 확인
mininet> sh for i in {1..10}; do echo "=== s$i ==="; ovs-ofctl -O OpenFlow13 dump-flows s$i; done
```

### 4단계: 컨트롤러 로그 모니터링

#### 별도 터미널에서 로그 확인
```bash
# 새 터미널 열기
tmux attach-session -t sdn-lab

# 또는 tmux 창 분할
Ctrl+b "    # 수평 분할
Ctrl+b %    # 수직 분할

# Primary Controller 로그 모니터링
# [PRIMARY-PACKET], [PRIMARY-CROSS], [PRIMARY-FLOW] 태그 확인

# Secondary Controller 로그 모니터링  
# [SECONDARY-PACKET], [SECONDARY-CROSS], [SECONDARY-FLOW] 태그 확인
```

#### 로그에서 확인할 내용
```
로그 예시:
[PRIMARY-PACKET] 00:00:00:00:00:01 → 00:00:00:00:00:0b on s1:1
[PRIMARY-LEARN] 00:00:00:00:00:01 learned at s1:1
[PRIMARY-CROSS] s1 → Secondary via port 4 (to 00:00:00:00:00:0b)
[PRIMARY-FLOW] s1: 00:00:00:00:00:01→00:00:00:00:00:0b installed (port 4)
```

### 5단계: 고급 테스트

#### 다중 연결 테스트
```bash
# 여러 호스트 동시 통신
mininet> h1 ping h11 &
mininet> h5 ping h15 &  
mininet> h10 ping h20 &
mininet> jobs          # 백그라운드 작업 확인
```

#### 전체 연결성 테스트
```bash
# 모든 ARP 설정 후 전체 테스트
mininet> h1 arp -s 10.0.0.11 00:00:00:00:00:0b
mininet> h1 arp -s 10.0.0.15 00:00:00:00:00:0f
mininet> h1 arp -s 10.0.0.20 00:00:00:00:00:14
# ... (모든 크로스 컨트롤러 ARP 설정)

mininet> pingall       # 전체 연결성 확인
```

### 6단계: 문제 해결

#### 연결 실패 시 점검사항
```bash
# 1. 컨트롤러 상태 확인
ps aux | grep ryu-manager

# 2. 스위치 연결 상태 확인
sudo ovs-vsctl show

# 3. 포트 상태 확인
sudo ovs-ofctl -O OpenFlow13 show s1

# 4. ARP 테이블 확인
mininet> h1 arp -a

# 5. 라우팅 테이블 확인
mininet> h1 route -n
```

### 테스트 시나리오 요약

| 테스트 | 소스 | 목적지 | 경로 | 목적 |
|--------|------|--------|------|------|
| 기본 | h1 | h2 | s1 내부 | Primary 내부 통신 |
| 게이트웨이 | h1 | h11 | s1→s3→s6 | 크로스 컨트롤러 |
| 직접연결 | h10 | h20 | s5→s10 | 최단 경로 |
| 성능 | h1 | h11 | iperf | 대역폭 측정 |
| 전체 | all | all | pingall | 전체 연결성 |

### 제한사항 및 개선 방안
- **현재 제한**: ARP 브로드캐스트가 컨트롤러 경계를 넘지 않음
- **해결 방법**: 수동 ARP 설정 또는 ARP 프록시 구현
- **프로덕션 환경**: 컨트롤러 간 REST API 통신으로 MAC 테이블 공유

### 🎯 테스트 성공 기준

✅ **성공 시 기대 결과:**
- 같은 컨트롤러 내 통신: 100% 성공
- 크로스 컨트롤러 통신: ARP 설정 후 100% 성공  
- Flow 룰 자동 설치: 로그에서 `[CONTROLLER-FLOW]` 확인
- 컨트롤러 로그: 패킷 경로 추적 가능

❌ **실패 시 점검사항:**
- 컨트롤러 프로세스 동작 여부
- ARP 테이블 설정 여부
- OpenFlow 연결 상태
- 네트워크 토폴로지 일치 여부

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

## 🛑 환경 종료

### 정상 종료
```bash
# Mininet CLI에서
mininet> exit

# 또는 별도 터미널에서
./stop_sdn.sh
```

### 강제 종료 (문제 발생 시)
```bash
# 모든 관련 프로세스 종료
sudo pkill -f ryu-manager
sudo mn -c
sudo pkill -f python3

# 네트워크 인터페이스 정리
sudo ip link | grep ovs | awk '{print $2}' | sed 's/:$//' | xargs -I {} sudo ip link delete {}

# OVS 브리지 정리
sudo ovs-vsctl list-br | xargs -I {} sudo ovs-vsctl del-br {}
```

### tmux 세션 관리
```bash
# 세션 목록 확인
tmux list-sessions

# SDN 세션 종료
tmux kill-session -t sdn-lab

# 모든 tmux 세션 종료
tmux kill-server
```

## 학습 목표

1. **Multi-Controller SDN**: 분산 컨트롤러 아키텍처 이해
2. **Cross-Controller Communication**: 컨트롤러 간 통신 구현
3. **L2 Learning Switch**: MAC 주소 학습 및 포워딩
4. **OpenFlow 1.3**: 플로우 룰 설치 및 관리
5. **Network Segmentation**: 네트워크 도메인 분리 및 관리

## 라이선스

교육 목적으로 자유롭게 사용 가능합니다.