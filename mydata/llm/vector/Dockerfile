FROM python:3.10-slim

# --- ロケール & タイムゾーン設定 ---
ENV LANG=ja_JP.UTF-8 \
    LANGUAGE=ja_JP:ja \
    LC_ALL=ja_JP.UTF-8 \
    TZ=Asia/Tokyo \
    CONTAINER_ROLE=vector

# --- システムパッケージ（OCR / PDF / 基本ユーティリティ） ---
RUN apt update && apt install -y \
    # OCR系
    tesseract-ocr \
    tesseract-ocr-jpn \
    ocrmypdf \
    ghostscript \
    qpdf \
    unpaper \
    # LibreOffice & PDF処理
    libreoffice \
    poppler-utils \
    # 基本ユーティリティ
    build-essential \
    locales \
    fonts-ipafont \
    libgl1 \
    libglib2.0-0 \
    curl \
    unzip \
 && echo "ja_JP.UTF-8 UTF-8" > /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

# --- ユーザー作成 & ワークディレクトリ指定 ---
RUN useradd -m libreuser
USER libreuser
ENV HOME=/home/libreuser
WORKDIR /app

# --- Pythonライブラリインストール（依存まとめ） ---
COPY --chown=libreuser:libreuser requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# --- ↓ volumeでコードをマウントする前提なのでCOPYは不要 ---
# COPY --chown=libreuser:libreuser . .

# --- CMDはdocker-composeで指定する前提 ---
CMD ["tail", "-f", "/dev/null"]










