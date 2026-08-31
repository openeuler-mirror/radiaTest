#!/bin/sh
# 为 dev 容器生成 redis TLS 自签 CA + 服务端证书（仅本地开发使用）
# redis 服务端与 app 容器共用 radiatest-redis-certs 命名卷
set -eu

CERT_DIR=/certs

if [ ! -f "${CERT_DIR}/redis-ca.crt" ]; then
  openssl genrsa -out "${CERT_DIR}/redis-ca.key" 2048
  openssl req -x509 -new -nodes -key "${CERT_DIR}/redis-ca.key" -sha256 -days 3650 \
    -subj "/CN=radiaTest-dev-ca" -out "${CERT_DIR}/redis-ca.crt"

  openssl genrsa -out "${CERT_DIR}/redis.key" 2048
  openssl req -new -key "${CERT_DIR}/redis.key" -subj "/CN=redis" \
    -out "${CERT_DIR}/redis.csr"
  printf 'subjectAltName=DNS:redis,IP:127.0.0.1\n' > "${CERT_DIR}/ext.cnf"

  openssl x509 -req -in "${CERT_DIR}/redis.csr" \
    -CA "${CERT_DIR}/redis-ca.crt" -CAkey "${CERT_DIR}/redis-ca.key" \
    -CAcreateserial -out "${CERT_DIR}/redis.crt" \
    -days 3650 -sha256 -extfile "${CERT_DIR}/ext.cnf"

  rm -f "${CERT_DIR}/redis.csr" "${CERT_DIR}/ext.cnf"
  chmod 0644 "${CERT_DIR}/redis-ca.crt" "${CERT_DIR}/redis.crt"
  # redis.key 需可被 redis 容器内非 root 用户读取（redis 服务以 redis 用户运行）；
  # 这是 dev-only 自签证书，0644 仅存在于本地命名卷，不进入镜像或仓库
  chmod 0644 "${CERT_DIR}/redis.key"
  chmod 0600 "${CERT_DIR}/redis-ca.key"
fi
