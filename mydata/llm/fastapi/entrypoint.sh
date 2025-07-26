#!/bin/sh
set -e

if [ ! -f /app/key.pem ] || [ ! -f /app/cert.pem ]; then
    echo "Generating self-signed certificate for CN=${CN}"
    openssl req -x509 -newkey rsa:4096 \
        -keyout /app/key.pem \
        -out /app/cert.pem \
        -days 365 -nodes \
        -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Dev/OU=Dev/CN=${CN}"
fi

exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --ssl-keyfile=/app/key.pem \
    --ssl-certfile=/app/cert.pem

