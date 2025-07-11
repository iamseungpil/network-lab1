FROM python:3.8-slim

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    net-tools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# RYU 설치 (Python 3.8과 호환 가능한 버전)
RUN pip install ryu==4.34 eventlet==0.31.0 webob==1.8.9 routes==2.5.1

# 작업 디렉토리 설정
WORKDIR /app

# 포트 노출
EXPOSE 6633 8080

# 시작 스크립트 복사
COPY start-controller.sh /app/
RUN chmod +x /app/start-controller.sh

CMD ["/app/start-controller.sh"]