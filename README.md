# 🌐 SDN Dijkstra Routing Demo

OpenFlow 기반 Software-Defined Networking (SDN) 환경에서 Dijkstra 알고리즘을 사용한 동적 라우팅 구현 프로젝트입니다.

## 📋 목차
- [개요](#개요)
- [주요 기능](#주요-기능)
- [시스템 요구사항](#시스템-요구사항)
- [설치 및 실행](#설치-및-실행)
  - [Ubuntu/Linux 환경](#ubuntulinux-환경)
  - [Windows 환경 (Docker)](#windows-환경-docker)
- [토폴로지 종류](#토폴로지-종류)
- [테스트 시나리오](#테스트-시나리오)
- [프로젝트 구조](#프로젝트-구조)

## 🎯 개요

이 프로젝트는 SDN 환경에서 Dijkstra 최단 경로 알고리즘을 구현하여 네트워크 토폴로지를 자동으로 학습하고, 링크 장애 시 동적으로 재라우팅하는 시스템을 구현합니다.

### 핵심 기술 스택
- **Controller**: Ryu SDN Framework
- **Network Emulation**: Mininet
- **Protocol**: OpenFlow 1.3
- **Algorithm**: Dijkstra Shortest Path with STP (Spanning Tree Protocol)
- **Language**: Python 3

## ✨ 주요 기능

1. **자동 토폴로지 탐색**: LLDP를 통한 네트워크 구조 자동 학습
2. **최단 경로 계산**: Dijkstra 알고리즘 기반 최적 경로 설정
3. **동적 재라우팅**: 링크 장애 감지 및 자동 경로 재설정
4. **루프 방지**: STP 구현으로 브로드캐스트 스톰 방지
5. **실시간 모니터링**: 패킷 처리 및 경로 변경 로깅

## 💻 시스템 요구사항

### 공통 요구사항
- Python 3.8 이상
- Git
- 4GB 이상 RAM
- 10GB 이상 디스크 공간

### 플랫폼별 요구사항

#### Ubuntu/Linux
- Ubuntu 20.04 LTS 이상
- Mininet 2.3.0+
- Open vSwitch
- Conda/Miniconda (권장)

#### Windows
- Windows 10/11 (WSL2 권장)
- Docker Desktop
- Git Bash

## 🚀 설치 및 실행

### 🐧 Ubuntu/Linux 환경

#### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/sdn-dijkstra-routing.git
cd sdn-dijkstra-routing
```

#### 2. 의존성 설치 및 실행 (자동)
```bash
# 모든 설정이 자동으로 진행됩니다
./start_sdn_demo.sh

# 특정 토폴로지 선택
./start_sdn_demo.sh ring    # 10-switch ring topology
./start_sdn_demo.sh diamond # Diamond topology
./start_sdn_demo.sh graph   # Graph topology
```

#### 3. 수동 설치 (선택사항)
```bash
# Conda 환경 생성
conda create -n sdn-lab python=3.10 -y
conda activate sdn-lab

# 패키지 설치
pip install -r requirements.txt

# Mininet 설치
sudo apt-get update
sudo apt-get install mininet openvswitch-switch
```

### 🪟 Windows 환경 (Docker)

Windows 환경에서는 Docker를 사용하여 실행합니다.

#### 1. 사전 준비
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치
- Docker Desktop 실행 및 WSL2 백엔드 활성화

#### 2. Docker 브랜치 체크아웃
```bash
git clone https://github.com/yourusername/sdn-dijkstra-routing.git
cd sdn-dijkstra-routing
git checkout docker-windows  # Docker 버전 브랜치로 전환
```

#### 3. 실행 (Git Bash에서)
```bash
# Docker 이미지 빌드 및 자동 실행
./start_sdn_docker.sh start

# 특정 토폴로지 실행
./start_sdn_docker.sh run ring    # Ring topology
./start_sdn_docker.sh run diamond # Diamond topology
./start_sdn_docker.sh run graph   # Graph topology

# tmux 세션 재연결
./start_sdn_docker.sh attach

# 컨테이너 정지
./start_sdn_docker.sh stop
```

#### 4. PowerShell 사용 (선택사항)
```powershell
# PowerShell (관리자 권한)
.\start_sdn_docker.ps1 start
.\start_sdn_docker.ps1 run ring
.\start_sdn_docker.ps1 stop
```

## 🗺️ 토폴로지 종류

### 1. Diamond Topology (기본)
```
    h1 --- s1
          /  \
         s2  s3
          \  /
    h4 --- s4
```
- 4개 스위치, 2개 호스트
- 다중 경로 테스트에 적합

### 2. Ring Topology
```
    s1 --- s2 --- s3
    |              |
    s10    ...    s4
    |              |
    s9 --- s8 --- s5
           |
          s6-s7
```
- 10개 스위치 링 구조
- STP 및 재라우팅 테스트에 최적

### 3. Graph Topology
```
       h1
        |
    s1--s2--s3
    |  X  X  |
    s4--s5--s6
        |
       h2
```
- 6개 스위치 메시 구조
- 복잡한 경로 계산 테스트

## 🧪 테스트 시나리오

### tmux 세션 조작
- `Ctrl+B + ↑/↓`: 컨트롤러와 Mininet 창 전환
- `Ctrl+B + z`: 현재 창 확대/축소
- `Ctrl+B + d`: tmux 세션 분리 (백그라운드 실행)
- `Ctrl+B + [`: 스크롤 모드 (q로 종료)

### Mininet CLI 명령어

#### 1. 기본 연결 테스트
```bash
mininet> pingall
mininet> h1 ping h4
```

#### 2. 링크 장애 시뮬레이션
```bash
mininet> link s1 s2 down  # 링크 비활성화
mininet> h1 ping h4       # 재라우팅 확인
mininet> link s1 s2 up    # 링크 복구
```

#### 3. 대역폭 테스트
```bash
mininet> iperf h1 h4
```

#### 4. 경로 추적
```bash
mininet> h1 traceroute h4
```

## 📁 프로젝트 구조

```
sdn-dijkstra-routing/
├── ryu-controller/
│   ├── main_controller_stp.py    # 메인 컨트롤러 (STP + Dijkstra)
│   ├── simple_controller.py      # 기본 L2 스위치
│   └── dijkstra_controller.py    # Dijkstra only
├── mininet/
│   ├── diamond_topology.py       # Diamond 토폴로지
│   ├── ring_topology.py          # Ring 토폴로지
│   └── graph_topology.py         # Graph 토폴로지
├── start_sdn_demo.sh             # Linux/Ubuntu 실행 스크립트
├── start_sdn_docker.sh           # Windows Docker 실행 스크립트 (docker-windows 브랜치)
├── start_sdn_docker.ps1          # Windows PowerShell 스크립트 (docker-windows 브랜치)
├── Dockerfile                    # Docker 이미지 정의 (docker-windows 브랜치)
├── requirements.txt              # Python 패키지 목록
└── README.md                     # 프로젝트 문서

```

## 🌿 브랜치 구조

- `main`: Ubuntu/Linux 네이티브 환경용 (기본)
- `docker-windows`: Windows Docker 환경용

### 브랜치 전환
```bash
# Linux 버전 사용
git checkout main

# Windows Docker 버전 사용
git checkout docker-windows
```

## 🔍 컨트롤러 로그 분석

컨트롤러 로그에서 확인할 수 있는 주요 이벤트:

1. **스위치 연결**: `Switch connected: dpid=0000000000000001`
2. **토폴로지 발견**: `Link discovered: 0000000000000001 -> 0000000000000002`
3. **경로 계산**: `Shortest path from 00:00:00:00:00:01 to 00:00:00:00:00:04: [1, 2, 4]`
4. **링크 장애 감지**: `Link deleted: 0000000000000001 -> 0000000000000002`
5. **재라우팅**: `Recalculating paths due to topology change`

## 🐛 문제 해결

### Linux 환경
```bash
# Mininet 정리
sudo mn -c

# 프로세스 종료
sudo pkill -f ryu-manager
sudo pkill -f ovs

# 권한 문제
sudo chown -R $USER:$USER .
```

### Windows Docker 환경
```bash
# Docker 재시작
./start_sdn_docker.sh stop
./start_sdn_docker.sh rebuild
./start_sdn_docker.sh start

# 컨테이너 로그 확인
docker logs sdn-lab

# 컨테이너 직접 접속
./start_sdn_docker.sh connect
```

## 📚 참고 자료

- [Ryu SDN Framework](https://ryu-sdn.org/)
- [Mininet](http://mininet.org/)
- [OpenFlow 1.3 Specification](https://www.opennetworking.org/software-defined-standards/specifications/)
- [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/)

## 📜 라이선스

MIT License

## 🤝 기여

프로젝트 개선을 위한 Pull Request와 Issue를 환영합니다!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 👨‍💻 작성자

- Your Name - [@yourusername](https://github.com/yourusername)

## 🙏 감사의 말

- SDN/OpenFlow 커뮤니티
- Ryu 프레임워크 개발팀
- Mininet 프로젝트 팀
