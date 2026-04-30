FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KAWAII_NONINTERACTIVE=1 \
    KAWAII_SKIP_SYSTEM_UPDATE=1 \
    KAWAII_SKIP_PIP_INSTALL=1 \
    KAWAII_PYTHON_BIN=python3

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libsndfile1 \
        libportaudio2 \
        portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

CMD ["python", "kawaii.py"]
