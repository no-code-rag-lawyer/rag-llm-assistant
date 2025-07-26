FROM python:3.10-slim

# ===== 必要パッケージインストール =====
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        portaudio19-dev \
        git \
        curl \
        openssl \
        ffmpeg \
        dos2unix \
    && rm -rf /var/lib/apt/lists/*

# ===== 作業ディレクトリ =====
WORKDIR /app

# ===== 依存関係インストール =====
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ===== ソースコードコピー =====
COPY . .

# ===== エントリポイントスクリプトコピー =====
COPY entrypoint.sh /app/entrypoint.sh

# Windows改行→Unix改行に変換し、実行権限を付与
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# ===== CN環境変数（起動時に変更可能） =====
ENV CN=127.0.0.1

# ===== 推奨されるexec形式 =====
ENTRYPOINT ["/app/entrypoint.sh"]







