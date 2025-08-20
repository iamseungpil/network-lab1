# SDN Dijkstra 라우팅 프로젝트 분석 및 정리 보고서

## 프로젝트 개요
이 프로젝트는 Software-Defined Networking (SDN) 환경에서 Dijkstra 알고리즘을 사용한 동적 라우팅 시스템을 구현합니다. Ryu 컨트롤러와 Mininet을 활용하여 네트워크 토폴로지를 구성하고, 링크 실패 시 자동 재라우팅을 수행합니다.

## 주요 구성 요소

### 1. 토폴로지 (Topology)
- **simple_topology.py**: 다이아몬드 형태의 4개 스위치, 4개 호스트 토폴로지
  - 기본 테스트용 단순 구조
  - 다중 경로 제공으로 장애 복구 테스트 가능
  
- **graph_topology_10sw_20h.py**: 복잡한 그래프 형태의 10개 스위치, 20개 호스트 토폴로지
  - 실제 네트워크 환경 시뮬레이션
  - 다양한 경로 선택 및 부하 분산 테스트 가능

### 2. 컨트롤러 (Controller)
- **ryu-controller/main_controller.py**: Dijkstra 기반 SDN 컨트롤러
  - LLDP를 통한 동적 토폴로지 발견
  - NetworkX를 활용한 최단 경로 계산
  - OpenFlow 1.3 프로토콜 지원
  - 실시간 링크 상태 모니터링 및 장애 감지
  - 자동 플로우 테이블 업데이트

## 실행 방법

### 환경 설정
```bash
# Conda 환경 활성화
conda activate sdn-lab

# 필요 패키지 (이미 설치됨)
# - ryu (4.34)
# - mininet
# - networkx
```

### 통합 실행 스크립트
```bash
# 기본 실행 (simple topology)
./sdn_demo.sh

# 복잡한 토폴로지 실행
./sdn_demo.sh --complex

# 자동 테스트 포함 실행
./sdn_demo.sh --test

# 정리
./sdn_demo.sh --clean
```

## 테스트 결과

### 1. 정상 연결 테스트
- **결과**: ✅ 성공
- h1 → h4 ping: 평균 RTT 6.294ms
- 모든 호스트 간 연결 정상

### 2. 동적 라우팅 테스트
- **시나리오**: s1-s2 링크 차단
- **결과**: ✅ 성공
- 링크 실패 감지: ~2초
- 대체 경로 계산 및 적용: 즉시
- 패킷 손실 없이 통신 유지

### 3. 링크 복구 테스트
- **시나리오**: s1-s2 링크 복구
- **결과**: ✅ 성공
- 토폴로지 재발견 및 최적 경로 재계산

## 프로젝트 구조 정리

### 정리 전
- 중복 파일 다수 (archive/, backup_scripts/ 등)
- 여러 개의 셸 스크립트 산재
- 테스트 파일들이 루트에 혼재

### 정리 후
```
network-lab1/
├── ryu-controller/
│   ├── main_controller.py     # 메인 Dijkstra 컨트롤러
│   └── main_controller_stp.py  # STP 지원 버전
├── mininet/
│   └── dijkstra_graph_topo.py # 추가 토폴로지
├── simple_topology.py          # 기본 토폴로지
├── graph_topology_10sw_20h.py # 복잡한 토폴로지
├── sdn_demo.sh                # 통합 실행 스크립트
├── start_sdn_demo.sh          # 기존 호환성 유지
├── requirements.txt           # Python 의존성
├── environment.yml            # Conda 환경 설정
└── backup_all/               # 아카이브된 이전 파일들
```

## 핵심 기능

### 컨트롤러 기능
1. **토폴로지 발견**: LLDP 패킷을 통한 자동 네트워크 구조 파악
2. **경로 계산**: Dijkstra 알고리즘으로 최단 경로 계산
3. **플로우 설치**: OpenFlow를 통한 스위치 플로우 테이블 관리
4. **장애 감지**: 포트 상태 변경 이벤트 모니터링
5. **자동 복구**: 링크 실패 시 대체 경로 자동 설정

### 로깅 및 모니터링
- 상세한 이벤트 로깅 (스위치 연결, 패킷 처리, 경로 계산)
- 시각적 이모지 표시로 이벤트 타입 구분
- 실시간 토폴로지 상태 표시

## 사용 시나리오

### 기본 테스트
```bash
# CLI에서 실행
h1 ping h4        # 기본 연결 테스트
pingall           # 전체 연결 테스트
```

### 장애 시뮬레이션
```bash
link s1 s2 down   # 링크 차단
h1 ping h4        # 재라우팅 확인
link s1 s2 up     # 링크 복구
```

### tmux 세션 제어
- `Ctrl+b + ↑/↓`: 창 전환
- `Ctrl+b + d`: 세션 분리
- `Ctrl+b + [`: 스크롤 모드

## 기술 스택
- **Python 3.9**: 메인 프로그래밍 언어
- **Ryu 4.34**: SDN 컨트롤러 프레임워크
- **Mininet**: 네트워크 에뮬레이션
- **NetworkX**: 그래프 알고리즘
- **OpenFlow 1.3**: 스위치 제어 프로토콜
- **tmux**: 터미널 멀티플렉싱

## 결론
프로젝트가 성공적으로 정리되었으며, 모든 핵심 기능이 정상 작동합니다:
- ✅ 동적 토폴로지 발견
- ✅ Dijkstra 기반 최단 경로 라우팅
- ✅ 링크 실패 시 자동 재라우팅
- ✅ 단일 통합 실행 스크립트
- ✅ 깔끔한 프로젝트 구조

이제 하나의 스크립트(`sdn_demo.sh`)로 모든 기능을 실행할 수 있으며, 불필요한 파일들은 backup_all 폴더로 이동되었습니다.