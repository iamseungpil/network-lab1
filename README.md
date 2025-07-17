# SDN Multi-Controller Lab with Gateway-based Cross-Controller Communication

게이트웨이 기반 크로스 컨트롤러 통신을 지원하는 다중 컨트롤러 SDN 환경입니다.

## 🚀 완전한 설치 가이드

### 1단계: VirtualBox 설치 및 Ubuntu VM 생성

#### VirtualBox 설치 (Windows/macOS/Linux)

**Windows:**
```bash
# 1. VirtualBox 공식 사이트에서 다운로드
https://www.virtualbox.org/wiki/Downloads
# - "Windows hosts" 링크 클릭
# - VirtualBox-7.0.x-Win.exe 다운로드 및 실행
# - 기본 설정으로 설치 진행

# 2. VirtualBox Extension Pack 다운로드 (선택사항)
# - 같은 페이지에서 "VirtualBox Extension Pack" 다운로드
# - VirtualBox에서 파일 > 환경설정 > 확장 > 패키지 추가
```

**macOS:**
```bash
# 1. Homebrew 이용 (권장)
brew install --cask virtualbox

# 2. 또는 공식 사이트에서 직접 다운로드
https://www.virtualbox.org/wiki/Downloads
# - "OS X hosts" 링크 클릭
# - VirtualBox-7.0.x-OSX.dmg 다운로드 및 설치

# 3. 시스템 환경설정에서 보안 권한 허용 필요
# 시스템 환경설정 > 보안 및 개인정보 보호 > 일반
# "확인되지 않은 개발자의 앱 허용" 체크
```

**Linux (Ubuntu/Debian):**
```bash
# 1. 공식 저장소 추가
wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | sudo apt-key add -
echo "deb [arch=amd64] http://download.virtualbox.org/virtualbox/debian $(lsb_release -cs) contrib" | sudo tee /etc/apt/sources.list.d/virtualbox.list

# 2. VirtualBox 설치
sudo apt update
sudo apt install virtualbox-7.0

# 3. 사용자를 vboxusers 그룹에 추가
sudo usermod -a -G vboxusers $USER
newgrp vboxusers
```

#### Ubuntu VM 생성

```bash
# 1. Ubuntu ISO 다운로드
# https://ubuntu.com/download/desktop
# - Ubuntu 22.04 LTS Desktop 다운로드 (권장)
# - 또는 Ubuntu 20.04 LTS Desktop

# 2. VirtualBox에서 새 가상머신 생성
# VirtualBox 실행 > 새로 만들기(N) 클릭

이름: SDN-Lab
종류: Linux
버전: Ubuntu (64-bit)

메모리: 4096 MB (4GB) 이상 권장
하드디스크: 새 가상 하드디스크 만들기
파일 위치: 기본값 사용
파일 크기: 25 GB 이상 권장
하드디스크 파일 종류: VDI (VirtualBox 디스크 이미지)
물리적 하드디스크에 저장: 동적 할당 (권장)

# 3. VM 설정 조정 (VM 선택 후 설정 클릭)
일반 > 고급:
  - 클립보드 공유: 양방향
  - 드래그 앤 드롭: 양방향

시스템 > 프로세서:
  - 프로세서 개수: 2개 이상 (가능한 경우)
  - PAE/NX 사용: 체크

저장소:
  - 컨트롤러: IDE > 빈 CD 선택
  - 디스크 아이콘 클릭 > "가상 광학 디스크 파일 선택"
  - 다운로드한 Ubuntu ISO 파일 선택

네트워크:
  - 어댑터 1: NAT (기본값)
  - 고급 > 어댑터 종류: Intel PRO/1000 MT Desktop

# 4. Ubuntu 설치
# 시작 버튼 클릭하여 VM 부팅
# Ubuntu 설치 진행:
#   - 한국어 선택
#   - 일반 설치 선택
#   - 디스크를 지우고 Ubuntu 설치
#   - 사용자 계정 생성 (예: ubuntu)
#   - 설치 완료 후 재부팅

# 5. Guest Additions 설치 (중요!)
# Ubuntu 부팅 후 터미널에서:
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential dkms linux-headers-$(uname -r)

# VirtualBox 메뉴: 장치 > Guest Additions CD 이미지 삽입
# 자동 실행 또는 수동으로:
sudo mount /dev/cdrom /mnt
sudo /mnt/VBoxLinuxAdditions.run
sudo reboot

# 6. 기본 패키지 설치
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim build-essential net-tools
```

#### VM 성능 최적화 팁

```bash
# 1. 스왑 파일 크기 증가 (메모리가 부족한 경우)
sudo swapoff -a
sudo dd if=/dev/zero of=/swapfile bs=1G count=2
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 2. 불필요한 서비스 비활성화
sudo systemctl disable snapd
sudo systemctl disable cups
sudo systemctl disable bluetooth

# 3. 화면 해상도 조정
# 설정 > 디스플레이에서 해상도 조정
# Guest Additions 설치 후 자동 조정 가능
```

### 2단계: Conda 설치

#### Miniforge 설치 (권장)
```bash
# Ubuntu VM에서 터미널 열기 (Ctrl+Alt+T)

# Miniforge 다운로드 및 설치
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
chmod +x Miniforge3-Linux-x86_64.sh
./Miniforge3-Linux-x86_64.sh

# 설치 중 옵션:
# - 라이선스 동의: yes
# - 설치 경로: /home/ubuntu/miniforge3 (기본값, Enter)
# - conda init 실행: yes (중요!)

# 터미널 재시작 또는
source ~/.bashrc

# conda 프롬프트 확인 (터미널 앞에 (base) 표시됨)
# 설치 확인
conda --version
python --version
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

이 프로젝트는 10개의 OpenFlow 스위치와 20개의 호스트를 사용하여 두 개의 독립적인 RYU 컨트롤러가 서로 다른 네트워크 영역을 관리하는 SDN 환경을 구현합니다. **Gateway-based Controllers**를 통해 효율적인 크로스 컨트롤러 통신을 지원합니다.

### 네트워크 구성
- **Primary Controller (포트 6700)**: 스위치 s1-s5 관리
- **Secondary Controller (포트 6800)**: 스위치 s6-s10 관리
- **호스트**: 각 스위치에 2개씩 총 20개 (h1-h20)
- **토폴로지**: 트리 구조 (s1이 루트)
- **Gateway-based 크로스 컨트롤러 통신**: 지원 ✅

## ⚡ 빠른 시작 (환경 설정 완료 후)

```bash
# Conda 환경 활성화
conda activate sdn-lab

# SDN 환경 실행
./start_sdn.sh

# 성공 시 자동 테스트 없이 바로 Mininet CLI 진입:
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

Gateway-based 크로스 컨트롤러 통신:
- s3 ↔ s6, s7 (Primary ↔ Secondary)
- s4 ↔ s8, s9 (Primary ↔ Secondary)
- s5 ↔ s10 (Primary ↔ Secondary)
```

## Gateway-based 크로스 컨트롤러 통신

### 구현 방식
1. **MAC 주소 기반 도메인 판단**:
   - Primary 도메인: MAC 주소 0x01-0x0a (h1-h10)
   - Secondary 도메인: MAC 주소 0x0b-0x14 (h11-h20)

2. **간소화된 게이트웨이 라우팅**:
   - Primary → Secondary: 기본 게이트웨이 s3 사용
   - Secondary → Primary: 모든 Secondary 스위치는 포트 3으로 연결

3. **효율적인 패킷 처리**:
   - 사전 정의된 호스트 테이블 대신 실시간 MAC 주소 분석
   - 동적 플로우 룰 설치

## 사용 방법

### Mininet CLI 명령어

```bash
# 기본 연결성 테스트 (같은 컨트롤러 내)
h1 ping -c 3 h2    # Primary 내부 통신
h11 ping -c 3 h12  # Secondary 내부 통신

# Gateway-based 크로스 컨트롤러 통신 (ARP 설정 필요)
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

### 2단계: Gateway-based 크로스 컨트롤러 통신 테스트

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

### 3단계: 컨트롤러 로그 모니터링

#### 로그에서 확인할 내용
```
Gateway-based 로그 예시:
[PRIMARY-PACKET] 00:00:00:00:00:01 → 00:00:00:00:00:0b on s1:1
[PRIMARY-LEARN] 00:00:00:00:00:01 learned at s1:1
[PRIMARY-GATEWAY] s1 → Secondary via gateway port 4
[PRIMARY-FLOW] s1: 00:00:00:00:00:01→00:00:00:00:00:0b installed (port 4)
```

### 4단계: Flow 테이블 분석

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

### 5단계: 전체 연결성 테스트

```bash
# 전체 연결성 테스트
mininet> pingall       # 전체 연결성 확인
```

## 파일 구조

```
network-lab1/
├── README.md                      # 이 파일
├── requirements.txt               # Python 의존성
├── start_sdn.sh                  # SDN 환경 시작 스크립트
├── stop_sdn.sh                   # SDN 환경 종료 스크립트
├── lab_assignments.md            # 실습 과제
├── ryu-controller/
│   ├── gateway_primary.py        # Gateway Primary Controller
│   └── gateway_secondary.py      # Gateway Secondary Controller
└── mininet/
    └── topology.py               # Mininet 토폴로지 정의
```

## Gateway-based 구현의 장점

1. **간소화된 라우팅**: MAC 주소 기반 도메인 판단으로 복잡한 호스트 테이블 불필요
2. **효율적인 패킷 처리**: 실시간 MAC 주소 분석으로 동적 라우팅
3. **확장성**: 새로운 호스트 추가 시 별도 설정 불필요
4. **유지보수성**: 코드 구조가 간단하고 이해하기 쉬움

## 설치 및 환경 설정

### 필수 요구사항

#### 호스트 시스템
- **Windows 10/11, macOS 10.14+, 또는 Linux**
- **메모리**: 8GB 이상 (VM에 4GB 할당)
- **디스크 공간**: 30GB 이상 여유 공간
- **프로세서**: Intel/AMD 64-bit, 가상화 지원

#### 가상머신 (Ubuntu)
- **Ubuntu 22.04 LTS 또는 20.04 LTS**
- **메모리**: 4GB 이상 (VM 설정)
- **디스크**: 25GB 이상 (VM 하드디스크)
- **Python 3.9** (권장)
- **Conda** (Miniforge 권장)
- **sudo 권한**

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

## 학습 목표

1. **Gateway-based Multi-Controller SDN**: 게이트웨이 기반 분산 컨트롤러 아키텍처
2. **MAC 주소 기반 도메인 라우팅**: 효율적인 크로스 컨트롤러 통신
3. **동적 플로우 룰 관리**: 실시간 패킷 분석 및 라우팅
4. **OpenFlow 1.3**: 플로우 룰 설치 및 관리
5. **Network Segmentation**: 네트워크 도메인 분리 및 관리

## 라이선스

교육 목적으로 자유롭게 사용 가능합니다.