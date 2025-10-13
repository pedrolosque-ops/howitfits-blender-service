FROM ubuntu:22.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-pip wget curl ca-certificates \
    xvfb libgl1 libxrender1 libxext6 libxi6 libxxf86vm1 \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.9-linux-x64.tar.xz && \
    tar -xf blender-3.6.9-linux-x64.tar.xz && \
    mv blender-3.6.9-linux-x64 /opt/blender && \
    ln -s /opt/blender/blender /usr/local/bin/blender

WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

ENV UVICORN_PORT=8080
EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
