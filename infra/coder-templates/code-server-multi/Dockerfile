FROM codercom/enterprise-base:ubuntu

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    openjdk-17-jdk \
    maven \
    && pip3 install --no-cache-dir --break-system-packages pytest pytest-json-report \
    && rm -rf /var/lib/apt/lists/*

USER coder
