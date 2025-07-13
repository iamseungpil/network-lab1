# SDN Lab - RYU + Mininet 실습

## 프로젝트 개요
RYU 컨트롤러와 Mininet을 사용하여 소프트웨어 정의 네트워킹(SDN)의 핵심 개념을 학습하는 실습 프로젝트입니다.

## 주요 특징
- **2개 분할 컨트롤러**: Primary(s1-s5), Secondary(s6-s10)
- **10개 스위치 트리 토폴로지**: 계층적 네트워크 구조
- **20개 호스트**: 각 스위치에 2개씩 연결
- **L2 학습 스위치**: MAC 주소 기반 패킷 포워딩
- **OpenFlow 1.3**: 표준 SDN 프로토콜

## 빠른 시작
```bash
./start_sdn.sh
```

## 네트워크 구조
```
실제 구현된 토폴로지:

                    s1 (root)
                   /         \
                 s2           s3
                / \          /  \
              s4   s5      s6   s7
             / \    |           
           s8   s9  s10         

컨트롤러 할당:
- Primary Controller (127.0.0.1:6633): s1, s2, s3, s4, s5
- Secondary Controller (127.0.0.1:6634): s6, s7, s8, s9, s10

호스트 배치 (각 스위치에 2개씩, 총 20개):
- s1: h1(10.0.0.1), h2(10.0.0.2)
- s2: h3(10.0.0.3), h4(10.0.0.4)  
- s3: h5(10.0.0.5), h6(10.0.0.6)
- s4: h7(10.0.0.7), h8(10.0.0.8)
- s5: h9(10.0.0.9), h10(10.0.0.10)
- s6: h11(10.0.0.11), h12(10.0.0.12)
- s7: h13(10.0.0.13), h14(10.0.0.14)
- s8: h15(10.0.0.15), h16(10.0.0.16)
- s9: h17(10.0.0.17), h18(10.0.0.18)
- s10: h19(10.0.0.19), h20(10.0.0.20)

특징: 
- 하나의 연결된 트리 토폴로지
- 두 개의 분리된 컨트롤러 도메인
- 도메인 간 경계: s3↔s6, s3↔s7 연결
```

## 핵심 학습 목표
1. **SDN 아키텍처**: Control Plane과 Data Plane 분리
2. **OpenFlow 프로토콜**: 컨트롤러-스위치 통신
3. **L2 학습**: MAC 주소 테이블 동적 구성
4. **네트워크 분할**: 컨트롤러 도메인 관리
5. **패킷 처리**: Packet-in/Packet-out 메커니즘

## 테스트 시나리오
- **Same Controller**: h1 → h3 (Primary 내부)
- **Cross Controller**: h1 → h18 (Primary ↔ Secondary)
- **MAC Learning**: 첫 패킷 flooding, 이후 직접 전송
- **Flow Table**: 동적 플로우 규칙 생성

## 실습 과제
- 기본: L2 스위치 동작 분석, 컨트롤러 간 통신 추적
- 고급: 로드 밸런싱, 장애 복구, QoS 구현

## 파일 구성
```
ryu-controller/
├── primary_controller.py    # Primary 컨트롤러 (s1-s5)
└── secondary_controller.py  # Secondary 컨트롤러 (s6-s10)

mininet/
├── topology.py             # Mininet 토폴로지
├── test_connectivity.py    # 연결성 테스트 가이드
└── test_scenarios.py       # 테스트 시나리오 예제

├── sdn_cli.py              # SDN 플로우 규칙 관리 CLI
├── start_sdn.sh            # 실행 스크립트  
├── requirements.txt        # Python 패키지 요구사항
└── lab_assignments.md      # 실습 과제 (선택사항)
```

## 요구사항
- Python 3.9 (권장)
- Conda 또는 Python 가상환경
- RYU Controller 4.34
- Mininet 2.3.0+ 
- Open vSwitch (시스템 패키지)
- sudo 권한 (Mininet 실행용)

## 설치 방법

### 1. Conda 환경 설정
```bash
# Conda 환경 생성 (Python 3.9 권장)
conda create -n sdn-lab python=3.9 -y
conda activate sdn-lab

# 호환성을 위한 setuptools 다운그레이드
pip uninstall setuptools -y
pip install setuptools==67.6.1

# 의존성 설치
pip install -r requirements.txt
```

### 2. 시스템 패키지 설치
```bash
# Mininet 설치 (Ubuntu/Debian)
sudo apt update
sudo apt install mininet -y

# 설치 확인
sudo mn --test pingall
```

### 3. RYU 설치 확인
```bash
# Conda 환경 활성화
conda activate sdn-lab

# RYU 버전 확인
ryu-manager --version
# 출력: ryu-manager 4.34
```

## 중요 참고사항

### Python 버전 호환성
- **Python 3.9**: 완전 지원 ✅
- **Python 3.10+**: eventlet 호환성 문제로 권장하지 않음 ❌
- **setuptools 67.6.1**: RYU 설치를 위해 필수

### 알려진 문제 및 해결방법
1. **RYU 설치 오류**: `AttributeError: module 'setuptools.command.easy_install' has no attribute 'get_script_args'`
   - **해결방법**: `pip install setuptools==67.6.1`

2. **eventlet 오류**: `TypeError: cannot set 'is_timeout' attribute of immutable type 'TimeoutError'`
   - **해결방법**: Python 3.9 사용 및 `eventlet==0.30.2` 설치

3. **Mininet 권한 오류**: `Mininet must run as root`
   - **해결방법**: `sudo` 권한으로 실행

### 2. SDN 환경 시작
```bash
./start_sdn.sh
```

### 3. CLI 인터페이스 사용
```bash
# SDN CLI 시작
python3 sdn_cli.py

# 또는 직접 실행
./sdn_cli.py
```

### 4. 실행 순서
1. **컨트롤러 시작**: Primary(6633), Secondary(6634) 포트
2. **Mininet 시작**: 토폴로지 생성 및 스위치-컨트롤러 연결
3. **CLI 사용**: SDN CLI로 플로우 규칙 관리

## CLI 명령어 가이드

### SDN CLI 주요 명령어
```bash
# 네트워크 상태 조회
sdn> show topology          # 토폴로지 구조 표시
sdn> show switches          # 모든 스위치 상태
sdn> show hosts             # 호스트 할당 정보
sdn> show flows s1          # s1 스위치 플로우 테이블
sdn> status                 # 전체 네트워크 상태

# 플로우 규칙 관리
sdn> add flow s1 00:00:00:00:00:01 00:00:00:00:00:03 output:2
sdn> del flow s1            # s1의 모든 플로우 삭제
sdn> del flow s1 dl_src=00:00:00:00:00:01  # 특정 플로우 삭제
sdn> clear                  # 모든 스위치 플로우 삭제

# 연결성 테스트
sdn> test ping h1 h3        # h1에서 h3로 ping 테스트
sdn> test pingall           # 전체 연결성 테스트

# 도움말
sdn> help                   # 전체 명령어 목록
sdn> help show              # show 명령어 상세 설명
```

### Mininet CLI 병행 사용
```bash
# 전체 연결성 테스트
mininet> pingall

# 컨트롤러 간 통신 테스트  
mininet> h1 ping h12    # Primary → Secondary
mininet> h11 ping h2    # Secondary → Primary

# 네트워크 정보
mininet> dump
mininet> links
```

## 핵심 파일 설명

### ryu-controller/primary_controller.py
- s1-s5 스위치 관리
- L2 학습 스위치 기능
- OpenFlow 1.3 사용

### ryu-controller/secondary_controller.py  
- s6-s10 스위치 관리
- 독립적인 L2 학습 기능

### mininet/topology.py
- 10 스위치, 20 호스트 트리 토폴로지
- 컨트롤러별 스위치 할당
- 자동 IP/MAC 설정

### start_sdn.sh
- 전체 환경 자동 시작
- 컨트롤러 → Mininet 순서 실행
- 종료 시 자동 정리

## 학습 포인트

### 1. SDN 기본 개념
- **Control Plane**: RYU 컨트롤러
- **Data Plane**: Mininet 가상 스위치  
- **OpenFlow**: 컨트롤러-스위치 통신 프로토콜

### 2. L2 학습 스위치
- MAC 주소 학습 과정
- 플로우 테이블 동적 생성
- Packet-in/Packet-out 메커니즘

### 3. 컨트롤러 분할
- 네트워크 세그멘테이션
- 독립적인 제어 도메인
- 확장성 및 장애 격리

## 문제 해결

### 컨트롤러 연결 실패
```bash
# 포트 사용 확인
sudo netstat -tlnp | grep 6633
sudo netstat -tlnp | grep 6634

# 기존 프로세스 정리
sudo pkill -f ryu-manager
sudo mn -c
```

### 권한 문제
```bash
# Mininet 권한 확인
sudo mn --test pingall

# OVS 서비스 상태
sudo systemctl status openvswitch-switch
```

## 로그 위치
- RYU 컨트롤러: `/var/log/ryu/` 또는 실행 터미널
- Mininet: 실행 터미널
- OVS: `sudo ovs-appctl vlog/list`

이 프로젝트를 통해 SDN의 핵심 개념인 **제어 평면과 데이터 평면의 분리**, **중앙집중식 네트워크 제어**, **프로그래머블 네트워킹**을 직관적으로 이해할 수 있습니다.

## CLI 테스트 가이드

### 단계별 테스트 시나리오

#### **1단계: 환경 확인**
```bash
# SDN CLI 시작
python3 sdn_cli.py

# 전체 네트워크 상태 확인
sdn> status
sdn> show topology
sdn> show switches
sdn> show hosts
```

#### **2단계: 초기 플로우 테이블 확인**
```bash
# 각 컨트롤러 도메인의 대표 스위치 확인
sdn> show flows s1          # Primary 컨트롤러 (루트 스위치)
sdn> show flows s6          # Secondary 컨트롤러 (경계 스위치)

# 결과: table-miss 플로우만 존재해야 함
```

#### **3단계: 기본 연결성 테스트**
```bash
# 같은 컨트롤러 내부 통신 (Primary)
sdn> test ping h1 h3        # s1 → s2 경로

# Mininet CLI에서 실제 실행:
mininet> h1 ping -c 1 h3

# 플로우 테이블 변화 확인
sdn> show flows s1          # 새로운 플로우 규칙 생성 확인
sdn> show flows s2
```

#### **4단계: 컨트롤러 간 통신 테스트**
```bash
# Primary → Secondary 도메인 통신
sdn> test ping h1 h11       # s1 → s3 → s6 경로

# Mininet CLI에서 실제 실행:
mininet> h1 ping -c 1 h11

# 경로상 모든 스위치 플로우 확인
sdn> show flows s1          # Primary 시작점
sdn> show flows s3          # 경계 스위치 (Primary)
sdn> show flows s6          # 경계 스위치 (Secondary)
```

#### **5단계: 수동 플로우 규칙 추가**
```bash
# 기존 플로우 삭제
sdn> del flow s1

# 수동으로 플로우 규칙 추가
sdn> add flow s1 00:00:00:00:00:01 00:00:00:00:00:03 output:2

# 추가된 규칙 확인
sdn> show flows s1

# 테스트: 이제 h1→h3 통신이 컨트롤러 개입 없이 진행
mininet> h1 ping -c 1 h3
```

#### **6단계: 전체 연결성 테스트**
```bash
# 모든 호스트 간 연결성 확인
sdn> test pingall

# Mininet CLI에서 실제 실행:
mininet> pingall

# 결과 분석: 어떤 호스트들이 통신 가능한지 확인
```

#### **7단계: 고급 테스트 - 브로드캐스트**
```bash
# 브로드캐스트 테스트 (ARP 등)
mininet> h1 arping -c 1 10.0.0.3

# 모든 스위치의 플로우 테이블 확인
sdn> show flows s1
sdn> show flows s2
sdn> show flows s3
```

### 예상 결과 및 분석

#### **정상 동작 시 기대값**
```bash
# 1. 초기 상태
sdn> show flows s1
# 출력: table-miss flow (priority=0) 만 존재

# 2. 첫 번째 ping 후
sdn> show flows s1
# 출력: 
# - table-miss flow (priority=0)
# - 새로운 플로우 규칙 (priority=1 또는 100)
#   예: dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00:00:03,actions=output:2

# 3. 컨트롤러 상태
sdn> status
# 출력: Primary Controller: Running, Secondary Controller: Running
```

#### **문제 진단 방법**
```bash
# 1. 컨트롤러가 실행되지 않는 경우
sdn> status
# Primary Controller: Stopped 라고 나오면 start_sdn.sh 재실행

# 2. 플로우가 설치되지 않는 경우
sdn> show flows s1
# table-miss flow만 계속 있다면 컨트롤러 로그 확인 필요

# 3. ping이 실패하는 경우
mininet> pingall
# 0% dropped가 아니라면 네트워크 설정 문제
```

### 테스트 체크리스트

#### **✅ 기본 기능 확인**
- [ ] CLI가 정상적으로 시작됨
- [ ] `show topology` 명령어로 네트워크 구조 확인
- [ ] `show switches` 명령어로 10개 스위치 확인  
- [ ] `show hosts` 명령어로 20개 호스트 확인
- [ ] `status` 명령어로 컨트롤러 상태 확인

#### **✅ L2 학습 스위치 동작**
- [ ] 초기에는 table-miss 플로우만 존재
- [ ] 첫 번째 ping 후 새로운 플로우 규칙 생성
- [ ] 양방향 플로우 규칙 설치 (src→dst, dst→src)
- [ ] 두 번째 ping은 하드웨어에서 직접 처리

#### **✅ 컨트롤러 간 통신**
- [ ] 같은 도메인 내부 통신 (h1↔h3) 성공
- [ ] 도메인 간 통신 (h1↔h11) 성공
- [ ] 경계 스위치(s3)에서 적절한 플로우 생성
- [ ] Primary와 Secondary 모두에서 플로우 학습

#### **✅ CLI 플로우 관리**
- [ ] `add flow` 명령어로 수동 플로우 추가 가능
- [ ] `del flow` 명령어로 플로우 삭제 가능
- [ ] `clear` 명령어로 전체 플로우 초기화 가능
- [ ] 수동 추가된 플로우로 정상 통신 가능

### 고급 실험 아이디어

#### **성능 테스트**
```bash
# 대량 트래픽 테스트
mininet> iperf h1 h11

# 동시 다발적 통신
mininet> h1 ping h3 &
mininet> h5 ping h15 &
mininet> h11 ping h2 &
```

#### **장애 시뮬레이션**
```bash
# 특정 스위치 플로우 삭제 후 재학습 관찰
sdn> del flow s3
mininet> h1 ping h11        # 재학습 과정 관찰
sdn> show flows s3          # 플로우 재생성 확인
```

이제 CLI를 체계적으로 테스트할 수 있는 완전한 가이드가 README에 추가되었습니다! 🎯