FROM python:3.10-slim

# 日本語ロケールと必要な基本パッケージ
ENV LANG=ja_JP.UTF-8 \
    LANGUAGE=ja_JP:ja \
    LC_ALL=ja_JP.UTF-8 \
    TZ=Asia/Tokyo

RUN apt update && apt install -y \
    curl \
    git \
    fonts-ipafont \
    locales \
    && echo "ja_JP.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /workspace

# Jupyter用パッケージのみ（軽量化）
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ポート：Jupyter用（FastAPIとは別）
EXPOSE 8888

# Jupyter Lab 起動（--allow-root はroot運用用）
CMD ["jupyter", "lab", "--notebook-dir=/workspace", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]

