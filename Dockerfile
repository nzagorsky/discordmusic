FROM ubuntu:focal

WORKDIR /bot

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive \
    apt-get install -y gcc ffmpeg python3 python3-pip python3-nacl \
    && rm -rf /root/.cache \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /bot/requirements.txt
RUN pip3 install -r requirements.txt

COPY ./src /bot

CMD ["python3", "run.py"]
