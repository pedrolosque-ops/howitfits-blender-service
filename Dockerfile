FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UVICORN_PORT=8080 \
    PATH="/opt/blender:${PATH}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 python3-pip \
      wget curl ca-certificates xz-utils \
      xvfb libgl1 libglu1-mesa libegl1 \
      libxrender1 libxext6 libxi6 libxxf86vm1 libxfixes3 \
      libxrandr2 libxkbcommon0 libxkbcommon-x11-0 libsm6 libx11-6 && \
    rm -rf /var/lib/apt/lists/*

# Blender 3.6 LTS
RUN wget -q https://download.blender.org/release/Blender3.6/blender-3.6.9-linux-x64.tar.xz && \
    tar -xJf blender-3.6.9-linux-x64.tar.xz && \
    mv blender-3.6.9-linux-x64 /opt/blender && \
    ln -s /opt/blender/blender /usr/local/bin/blender && \
    rm blender-3.6.9-linux-x64.tar.xz

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir fastapi uvicorn

# App code (server.py, scale_export.py, etc.)
COPY . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${UVICORN_PORT}/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
