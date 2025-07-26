# === ビルド用ステージ ===
FROM python:3.10-slim as builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git curl wget pkg-config libstdc++-12-dev \
    && rm -rf /var/lib/apt/lists/*

# llama.cpp をクローン
RUN git clone https://github.com/ggerganov/llama.cpp.git

# llama.cpp ディレクトリに移動
WORKDIR /app/llama.cpp

# CMakeビルド
RUN mkdir -p build && \
    cmake -S . -B build -DLLAMA_STATIC=ON && \
    cmake --build build --config Release

# === 実行用ステージ ===
FROM python:3.10-slim

# 実行に必要なものだけ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# llama.cppの実行バイナリだけコピー
COPY --from=builder /app/llama.cpp/build /app/llama.cpp/build

# Python依存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py /app/server.py

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]

