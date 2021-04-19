FROM python:3.9.1-slim-buster 

WORKDIR /bot

RUN apt-get update \
    && apt-get install -y gcc ffmpeg libffi-dev \
    && rm -rf /root/.cache \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /bot/requirements.txt
RUN pip3 install -r requirements.txt

COPY ./src /bot

CMD ["python", "run.py"]
