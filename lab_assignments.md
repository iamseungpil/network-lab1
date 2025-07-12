# SDN 실습 과제

## 과제 1: 기본 L2 스위치 동작 분석
### 목표
L2 학습 스위치의 기본 동작 원리를 이해하고 MAC 테이블 변화를 관찰

### 실습 단계
1. **초기 상태 확인**
   ```bash
   mininet> sh ovs-ofctl dump-flows s1
   mininet> sh ovs-ofctl dump-flows s6
   ```

2. **첫 번째 패킷 전송 (h1 → h3)**
   ```bash
   mininet> h1 ping -c 1 h3
   ```

3. **플로우 테이블 변화 확인**
   ```bash
   mininet> sh ovs-ofctl dump-flows s1
   mininet> sh ovs-ofctl dump-flows s2
   ```

### 분석 포인트
- 초기 table-miss 플로우만 존재
- 첫 패킷 후 양방향 플로우 규칙 생성
- MAC 주소와 포트 매핑 확인

## 과제 2: 컨트롤러 간 통신 경로 추적
### 목표
Primary와 Secondary 컨트롤러 간 패킷 경로를 추적하고 각 스위치의 역할 이해

### 실습 단계
1. **Cross-controller ping (h1 → h18)**
   ```bash
   mininet> h1 ping -c 1 h18
   ```

2. **경로상 모든 스위치 플로우 확인**
   ```bash
   mininet> sh ovs-ofctl dump-flows s1  # Primary entry point
   mininet> sh ovs-ofctl dump-flows s3  # Primary-Secondary bridge
   mininet> sh ovs-ofctl dump-flows s6  # Secondary entry point  
   mininet> sh ovs-ofctl dump-flows s9  # Secondary endpoint
   ```

3. **컨트롤러 로그 분석**
   - Primary 컨트롤러: s1, s3에서의 패킷 처리
   - Secondary 컨트롤러: s6, s9에서의 패킷 처리

### 분석 포인트
- 패킷이 어떤 경로로 전달되는가?
- 각 컨트롤러가 언제 개입하는가?
- 브리지 스위치(s3)의 역할은?

## 과제 3: 로드 밸런싱 기능 구현
### 목표
두 컨트롤러 간 트래픽 분산을 위한 로드 밸런싱 기능 추가

### 구현 과제
```python
# primary_controller.py에 추가할 기능
def load_balance_decision(self, src_mac, dst_mac):
    """
    MAC 주소 해시를 기반으로 경로 결정
    Primary 영역 호스트들도 Secondary 경로로 우회 가능
    """
    # TODO: 구현
    pass

def install_alternate_path(self, datapath, src, dst):
    """
    대체 경로 플로우 설치
    s1 → s3 → s6 경로로 우회
    """
    # TODO: 구현  
    pass
```

### 구현 요구사항
- MAC 주소 기반 해싱으로 경로 선택
- Primary 영역 내 통신도 일부는 Secondary 경로 사용
- 양방향 플로우 규칙 설치
- 로드 분산 비율 조정 가능

## 과제 4: 장애 복구 메커니즘
### 목표
컨트롤러 장애 시 자동 복구 기능 구현

### 시나리오
1. **Primary 컨트롤러 중단**
   ```bash
   # Primary 컨트롤러 프로세스 종료
   sudo pkill -f primary_controller.py
   ```

2. **Secondary가 Primary 영역 인수**
   - s1-s5 스위치를 Secondary가 관리
   - 기존 플로우 테이블 유지 또는 재구성

### 구현 과제
```python
# secondary_controller.py에 추가할 기능
def detect_primary_failure(self):
    """Primary 컨트롤러 장애 감지"""
    # TODO: 구현
    pass

def takeover_primary_switches(self):
    """Primary 영역 스위치 인수"""
    # TODO: 구현
    pass
```

## 과제 5: QoS (Quality of Service) 구현
### 목표
특정 트래픽에 우선순위를 부여하는 QoS 기능 구현

### 구현 요구사항
- ICMP(ping) 트래픽: 높은 우선순위
- 일반 TCP 트래픽: 보통 우선순위  
- 대역폭 제한 및 우선순위 큐 설정

### 구현 과제
```python
def apply_qos_policy(self, datapath, packet_type):
    """
    패킷 타입에 따른 QoS 정책 적용
    """
    if packet_type == 'icmp':
        priority = 100
        queue_id = 1  # High priority queue
    else:
        priority = 50 
        queue_id = 2  # Normal queue
    
    # TODO: 플로우 규칙에 QoS 적용
    pass
```

## 평가 기준

### 기본 과제 (60점)
- 과제 1, 2 완료
- 올바른 분석 보고서 작성
- 실습 과정 스크린샷 포함

### 고급 과제 (40점)
- 과제 3, 4, 5 중 2개 이상 선택 구현
- 코드 품질 및 주석
- 성능 테스트 결과
- 창의적 기능 추가

## 제출 형식
```
submission/
├── analysis_report.md      # 분석 보고서
├── screenshots/           # 실습 스크린샷
├── modified_controllers/  # 수정된 컨트롤러 코드
└── test_results/         # 테스트 결과
```