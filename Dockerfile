FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 NUMBA_NUM_THREADS=4
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git libgomp1 libsndfile1 && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/alextitonis/fly.ai.git vendor/fly.ai && git -C vendor/fly.ai checkout --detach 5e931b8dc4856550565c5fa129d3d0c055af3dd1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY critic ./critic
COPY scripts/setup_voice.py ./scripts/setup_voice.py
RUN mkdir -p data results && python -c 'from flybrain import download; download("data")' && python scripts/setup_voice.py
COPY . .
RUN useradd --uid 1000 --create-home critic && chown -R critic:critic /app
USER critic
EXPOSE 7860
CMD ["sh", "-c", "python -m uvicorn critic.server:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
