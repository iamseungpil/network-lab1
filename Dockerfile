# Ubuntu 22.04 베이스 이미지 사용 (systemd 포함)
FROM ubuntu:22.04

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    # 기본 도구
    sudo \
    wget \
    curl \
    git \
    vim \
    nano \
    net-tools \
    iputils-ping \
    iproute2 \
    iptables \
    traceroute \
    tcpdump \
    screen \
    tmux \
    netcat-openbsd \
    # Python 3.9 설치
    software-properties-common \
    # Mininet 의존성
    openvswitch-switch \
    openvswitch-common \
    # systemd
    systemd \
    systemd-sysv \
    dbus \
    # 빌드 도구
    build-essential \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python 3.9 설치
RUN add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y python3.9 python3.9-dev python3.9-distutils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Python 3.9를 기본 python3로 설정
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 && \
    update-alternatives --set python3 /usr/bin/python3.9

# pip 설치
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.9

# 작업 디렉토리 설정
WORKDIR /opt

# Mininet 소스에서 설치
# 먼저 Mininet 설치에 필요한 의존성 패키지들을 설치
RUN apt-get update && apt-get install -y \
    socat \
    psmisc \
    xterm \
    openssh-client \
    iperf3 \
    telnetd \
    ethtool \
    help2man \
    pyflakes3 \
    pylint \
    python3-pycodestyle \
    python3-pexpect \
    python3-tk \
    || true

# Mininet 설치
RUN git clone https://github.com/mininet/mininet.git && \
    cd mininet && \
    git checkout 2.3.0 && \
    PYTHON=python3.9 ./util/install.sh -n && \
    cd .. && \
    rm -rf mininet

# 작업 디렉토리 변경
WORKDIR /network-lab

# requirements.txt 복사
COPY requirements.txt .

# Python 패키지 설치
RUN pip3 install --no-cache-dir \
    setuptools==67.6.1 \
    wheel \
    eventlet==0.30.2 \
    greenlet==2.0.2

# RYU 및 기타 패키지 설치
RUN pip3 install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . .

# 스크립트 실행 권한 부여
RUN chmod +x *.sh

# OVS 및 시스템 디렉토리 생성
RUN mkdir -p /var/run/openvswitch /var/log/openvswitch /var/lib/openvswitch /etc/openvswitch

# start-sdn-lab.sh 복사
COPY start_sdn.sh /usr/local/bin/start_sdn.sh
RUN chmod +x /usr/local/bin/start_sdn.sh

# systemd 서비스 파일 생성
RUN echo '[Unit]\n\
Description=SDN Lab Environment\n\
After=network.target\n\
\n\
[Service]\n\
Type=simple\n\
ExecStart=/usr/local/bin/start_sdn.sh\n\
Restart=on-failure\n\
RestartSec=5\n\
StandardOutput=journal\n\
StandardError=journal\n\
SyslogIdentifier=sdn-lab\n\
\n\
[Install]\n\
WantedBy=multi-user.target\n\
' > /etc/systemd/system/sdn-lab.service

# 서비스 활성화
RUN systemctl enable sdn-lab.service || true

# 포트 노출
EXPOSE 6700 6800

# systemd를 PID 1로 실행
VOLUME ["/sys/fs/cgroup", "/run", "/tmp"]
CMD ["/sbin/init"]
