# SDN Dual Controller Demo Scripts

## 🚀 Essential Scripts (필수 스크립트)

### 1. **cleanup_network.sh**
- **용도**: 네트워크 완전 정리
- **사용 시점**: 데모 시작 전 또는 문제 발생 시
```bash
./cleanup_network.sh
```

### 2. **demo_all.sh**
- **용도**: 전체 듀얼 컨트롤러 시스템 데모 (8가지 테스트)
- **특징**: 
  - 10개 스위치, 20개 호스트
  - 링크 장애 감지 및 재라우팅
  - Cross-domain 통신 테스트
```bash
# 수동 모드 (Enter 키 대기)
./demo_all.sh

# 자동 모드 (3초 후 자동 시작)
./demo_all.sh auto
```

### 3. **demo_dijkstra.sh**
- **용도**: Dijkstra 알고리즘 동작 확인 전용
- **특징**:
  - 실시간 경로 계산 로그 출력
  - 최적 경로 vs 대안 경로 비교
  - 3가지 핵심 시나리오 집중 테스트
```bash
# 자동 모드 권장
./demo_dijkstra.sh auto
```

## 📊 테스트 시나리오

### demo_all.sh (8가지 테스트)
1. Intra-domain 연결성 (Primary)
2. Cross-domain 연결성
3. Primary domain 링크 장애
4. Primary domain 재라우팅
5. Cross-domain 링크 장애
6. Cross-domain 재라우팅
7. 링크 복구
8. 최적 경로 복원

### demo_dijkstra.sh (3가지 시나리오)
1. **정상 라우팅**: 최적 경로 계산
2. **링크 장애**: 대안 경로 발견
3. **경로 복구**: 최적 경로 재계산

## 🔍 실시간 모니터링

### tmux 세션 확인
```bash
# demo_all.sh 실행 후
tmux attach -t dual_controllers:0  # Primary controller
tmux attach -t dual_controllers:1  # Secondary controller

# demo_dijkstra.sh 실행 후
tmux attach -t dijkstra_demo:0     # Primary controller
tmux attach -t dijkstra_demo:1     # Secondary controller
```

### 세션 종료
```bash
tmux kill-session -t dual_controllers
tmux kill-session -t dijkstra_demo
```

## 🎯 권장 사용 순서

1. **첫 실행 (전체 기능 확인)**
```bash
./cleanup_network.sh
./demo_all.sh auto
```

2. **Dijkstra 알고리즘 확인**
```bash
./cleanup_network.sh
./demo_dijkstra.sh auto
```

## ⚙️ 환경 요구사항

- Python 3.8 (conda sdn-env)
- RYU 4.34
- Mininet 2.3.0+
- eventlet 0.30.2
- NetworkX

## 📝 백업된 스크립트

이전 버전이나 중복된 스크립트들은 `backup_scripts/` 디렉토리에 보관됨:
- demo_all_auto.sh (demo_all.sh와 중복)
- demo_conda.sh (demo_all.sh에 통합됨)
- start_dual_controllers.sh (demo에 통합됨)
- start_dual_controllers_conda.sh (demo에 통합됨)
- test_fixed_dual.sh (테스트 전용)
- stop_sdn.sh (cleanup_network.sh로 대체)

## 🚨 문제 해결

네트워크 인터페이스 오류 시:
```bash
./cleanup_network.sh
sudo mn -c
```

컨트롤러가 시작되지 않을 때:
```bash
source /data/miniforge3/etc/profile.d/conda.sh
conda activate sdn-env
./cleanup_network.sh
```

## 📊 성능 지표

- 최적 경로 계산: ~100ms
- 링크 장애 감지: ~1초
- 재라우팅 완료: ~3초
- 경로 복구: ~2초