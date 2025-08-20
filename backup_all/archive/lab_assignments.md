# SDN Lab1: Mininet + RYU 구현

## 과제 개요

**목표**: RYU 컨트롤러와 Mininet을 사용하여 SDN 모델을 구축하고, 플로우 정보를 수정하여 데이터 라우팅을 제어할 수 있는 시스템 구현

**과제 요구사항**:
- 10개 라우터(스위치)와 2개 컨트롤러를 가진 소규모 네트워크
- 쉬운 설정을 위한 스크립트/코드  
- 플로우 규칙 설정을 위한 간단한 명령행 인터페이스

## 현재 구현 상세

### 1. 네트워크 아키텍처

#### **토폴로지 구조**
```
                    s1 (root)
                   /         \
                 s2           s3
                / \          /  \
              s4   s5      s6   s7
             / \    |           
           s8   s9  s10         
```

#### **컨트롤러 도메인 분할**
- **Primary Controller** (127.0.0.1:6633): s1, s2, s3, s4, s5 관리
- **Secondary Controller** (127.0.0.1:6634): s6, s7, s8, s9, s10 관리

#### **호스트 배치** (총 20개 호스트)
- 각 스위치마다 2개 호스트 연결
- IP 주소: 10.0.0.1 ~ 10.0.0.20
- MAC 주소: 00:00:00:00:00:01 ~ 00:00:00:00:00:14

### 2. 핵심 구현 파일

#### **ryu-controller/primary_controller.py**
```python
# Primary Controller 핵심 기능:
# - s1-s5 스위치 관리
# - L2 학습 스위치 구현
# - MAC 주소 기반 플로우 테이블 동적 생성
# - OpenFlow 1.3 프로토콜 사용
```

#### **ryu-controller/secondary_controller.py**  
```python
# Secondary Controller 핵심 기능:
# - s6-s10 스위치 관리
# - 독립적인 L2 학습 기능
# - Primary와 동일한 로직이지만 분리된 도메인
```

#### **mininet/topology.py**
```python
# 토폴로지 정의:
# - 10개 스위치 (s1-s10) 생성
# - 20개 호스트 (h1-h20) 생성  
# - 트리 구조 연결
# - 컨트롤러별 스위치 할당
```

#### **sdn_cli.py**
```python
# SDN CLI 인터페이스 기능:
# - 플로우 규칙 추가/삭제
# - 네트워크 상태 조회
# - 연결성 테스트
# - 실시간 모니터링
```

### 3. 설정 및 실행 과정

#### **환경 준비**
1. **Python 환경**: Python 3.9 + conda 가상환경
2. **패키지 설치**: RYU 4.34, eventlet 0.30.2, setuptools 67.6.1
3. **시스템 패키지**: Mininet 2.3.0+, Open vSwitch

#### **실행 절차**
```bash
# 1. 환경 설정
conda create -n sdn-lab python=3.9 -y
conda activate sdn-lab
pip install setuptools==67.6.1
pip install -r requirements.txt

# 2. 시스템 패키지 설치  
sudo apt install mininet -y

# 3. SDN 환경 시작
./start_sdn.sh

# 4. CLI 인터페이스 실행 (별도 터미널)
python3 sdn_cli.py
```

### 4. CLI 인터페이스 상세

#### **네트워크 상태 조회**
```bash
sdn> show topology          # 토폴로지 구조 표시
sdn> show switches          # 스위치 상태 확인
sdn> show hosts             # 호스트 할당 정보
sdn> show flows s1          # 특정 스위치 플로우 테이블
sdn> status                 # 전체 네트워크 상태
```

#### **플로우 규칙 관리**
```bash
# 플로우 추가
sdn> add flow s1 00:00:00:00:00:01 00:00:00:00:00:03 output:2

# 플로우 삭제
sdn> del flow s1                              # 모든 플로우 삭제
sdn> del flow s1 dl_src=00:00:00:00:00:01     # 특정 플로우 삭제
sdn> clear                                    # 전체 스위치 플로우 삭제
```

#### **연결성 테스트**
```bash
sdn> test ping h1 h3        # 호스트 간 ping 테스트
sdn> test pingall           # 전체 연결성 테스트
```

### 5. 주요 기능 및 특징

#### **L2 학습 스위치 동작**
1. **초기 상태**: Table-miss 플로우만 존재
2. **첫 번째 패킷**: 컨트롤러로 전송 (Packet-In)
3. **MAC 학습**: 소스 MAC과 포트 매핑 저장
4. **플로우 설치**: 학습된 정보로 플로우 규칙 생성
5. **후속 패킷**: 하드웨어에서 직접 포워딩

#### **컨트롤러 간 통신**
- **도메인 내부 통신**: 단일 컨트롤러에서 처리
- **도메인 간 통신**: s3을 통한 경계 통과 
- **경로 예시**: h1 → s1 → s3 → s6 → h11

#### **실시간 모니터링**
- 플로우 테이블 실시간 조회
- 컨트롤러 상태 확인
- 네트워크 토폴로지 시각화

### 6. 테스트 시나리오

#### **기본 연결성 테스트**
```bash
# 같은 컨트롤러 내부 통신
mininet> h1 ping h3         # Primary: s1 → s2
mininet> h11 ping h13       # Secondary: s6 → s7 (s3 경유)

# 컨트롤러 간 통신  
mininet> h1 ping h11        # Primary → Secondary
mininet> h5 ping h15        # s3 → s6 → s8
```

#### **플로우 테이블 분석**
```bash
# 초기 상태 확인
sdn> show flows s1
sdn> show flows s6

# 통신 후 플로우 변화 확인
sdn> show flows s1          # 새로운 플로우 규칙 생성 확인
```

### 7. 구현의 교육적 가치

#### **SDN 핵심 개념 학습**
- **Control/Data Plane 분리**: 중앙집중식 제어
- **OpenFlow 프로토콜**: 컨트롤러-스위치 통신
- **프로그래머블 네트워킹**: 동적 플로우 제어

#### **분산 제어 시스템**
- **도메인 분할**: 확장성 및 장애 격리
- **컨트롤러 협력**: 경계 간 통신 처리
- **로드 분산**: 제어 부하 분산

#### **네트워크 관리**
- **CLI 기반 관리**: 실시간 설정 변경
- **모니터링**: 상태 조회 및 문제 진단
- **자동화**: 스크립트를 통한 환경 구축

## 과제 완료 체크리스트

### ✅ 필수 요구사항
- [x] **10개 라우터(스위치)**: s1-s10 구현
- [x] **2개 컨트롤러**: Primary/Secondary 분리
- [x] **설정 스크립트**: `start_sdn.sh` 자동화
- [x] **CLI 인터페이스**: `sdn_cli.py` 플로우 규칙 관리
- [x] **문서화**: 설정 과정 상세 설명

### ✅ 추가 구현사항  
- [x] **요구사항 파일**: `requirements.txt` Python 패키지 관리
- [x] **호환성 해결**: Python 3.9 + RYU 4.34 + eventlet 0.30.2
- [x] **사용자 가이드**: README.md 완전한 설치/사용법
- [x] **테스트 도구**: 연결성 및 상태 확인 기능

## 결론

본 구현은 과제에서 요구하는 **"10개 라우터 + 2개 컨트롤러 + CLI 인터페이스"**를 모두 충족하며, SDN의 핵심 개념을 실습할 수 있는 완전한 교육용 플랫폼을 제공합니다. 특히 분산 컨트롤러 환경에서의 도메인 간 통신과 실시간 플로우 관리 기능을 통해 SDN의 강력함과 유연성을 체험할 수 있습니다.