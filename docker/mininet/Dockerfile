FROM python:3.10-slim

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    mininet \
    openvswitch-switch \
    openvswitch-testcontroller \
    net-tools \
    iproute2 \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
RUN pip install mininet

# 작업 디렉토리 설정
WORKDIR /app

# 시작 스크립트 복사
COPY start-mininet.sh /app/
RUN chmod +x /app/start-mininet.sh

CMD ["/app/start-mininet.sh"]