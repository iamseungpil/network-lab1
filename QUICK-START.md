# 🚀 SDN Lab 빠른 시작 가이드

## 💡 초보자 (추천)

### 1단계: 준비
```bash
git clone <repository-url>
cd network-lab1
./make-executable.sh
```

### 2단계: 한 번에 실행
```bash
./run-simple.sh
```

### 3단계: 테스트
Mininet CLI에서:
```bash
mininet> pingall
mininet> h1 ping h11
mininet> exit
```

### Screen 조작법
- **세션 나가기**: `Ctrl+A, D` (백그라운드 유지)
- **재연결**: `./run-simple.sh`

---

## 🔧 고급 사용자 (tmux)

### 실행
```bash
./run.sh
```

### tmux 조작법
- **컨트롤러 보기**: `Ctrl+B, 0`
- **Mininet CLI**: `Ctrl+B, 1`
- **세션 나가기**: `Ctrl+B, D`
- **재연결**: `./connect.sh`

---

## 🛠️ 문제 해결

### 전체 재시작
```bash
docker stop sdn-lab && docker rm sdn-lab
./run-simple.sh  # 또는 ./run.sh
```

### 재연결만
```bash
./run-simple.sh  # screen 버전
./connect.sh     # tmux 버전
```

**상세 가이드**: `README.md` 또는 `TMUX-GUIDE.md` 참조
