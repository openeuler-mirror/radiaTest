# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

FROM python:3.12-slim

ARG DEBIAN_APT_MIRROR=https://mirrors.huaweicloud.com/debian
ARG DEBIAN_SECURITY_APT_MIRROR=https://mirrors.huaweicloud.com/debian-security
ARG PYTHON_PACKAGE_INDEX_URL=https://mirrors.huaweicloud.com/repository/pypi/simple
ARG UV_HTTP_TIMEOUT=120
ARG UV_VERSION=0.11.6

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT}" \
    UV_LINK_MODE=copy \
    UV_DEFAULT_INDEX="${PYTHON_PACKAGE_INDEX_URL}" \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN sed -i \
        -e "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_APT_MIRROR}|g" \
        -e "s|http://deb.debian.org/debian|${DEBIAN_APT_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends git openssh-client sshpass ipmitool \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --index-url "${PYTHON_PACKAGE_INDEX_URL}" "uv==${UV_VERSION}"

# COPY backend/pyproject.toml backend/uv.lock ./
# RUN uv sync --frozen --no-dev
COPY backend/pyproject.toml ./
RUN uv sync --no-dev

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
