# radiaTest devcontainer - openEuler 基础镜像（对齐生产 build/docker-compose 的 openeuler/openeuler:22.03-lts）
#
# 资源要求：
#   - 内存 >= 4GB（前端 webpack 构建（vue-cli-service build）对内存敏感）
#   - 磁盘 >= 10GB（Python 依赖 + node_modules + 中间件数据卷）
#
# 使用说明：
#   - 系统包使用 dnf 包名（openEuler），不要照抄 apt 写法
#   - 内网镜像源用 ARG/ENV 传入，不要写死

ARG OPENEULER_IMAGE=openeuler/openeuler:22.03-lts
FROM ${OPENEULER_IMAGE}

ARG TZ=Asia/Shanghai
ENV TZ="${TZ}"

# Node.js 版本：radiaTest-web 的 package-lock.json 为 lockfileVersion 3（npm 9+/Node 18+），
# openEuler 22.03 dnf 自带的 nodejs 过旧，改用官方二进制（x86_64 / aarch64）
ARG NODE_VERSION=v18.20.4
ARG NODE_DIST_URL=https://nodejs.org/dist

# 基础工具链 + Python 3.9（openEuler 22.03 默认）+ 构建工具
RUN dnf update -y && dnf install -y \
    git \
    curl \
    wget \
    tar \
    unzip \
    xz \
    jq \
    vim \
    tmux \
    sudo \
    shadow \
    openssl \
    file-libs \
    gcc \
    gcc-c++ \
    make \
    cmake \
    pkgconf \
    python3 \
    python3-devel \
    python3-pip \
    && dnf clean all

# 注：openEuler 22.03 LTS 默认源（含 EPOL）没有 ripgrep 包，如需 rg 可后续用 cargo 安装

# Node.js 18 LTS（含 npm 10，可读取 lockfileVersion 3）
RUN set -eux; \
    case "$(uname -m)" in \
      x86_64) NODE_ARCH=x64 ;; \
      aarch64) NODE_ARCH=arm64 ;; \
      *) echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "${NODE_DIST_URL}/${NODE_VERSION}/node-${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" \
      -o /tmp/node.tar.xz; \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1; \
    rm -f /tmp/node.tar.xz; \
    node --version && npm --version

# 创建开发用户（devcontainer remoteUser）
RUN useradd -m -s /bin/bash vscode && \
    echo 'vscode ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/vscode && \
    chmod 440 /etc/sudoers.d/vscode && \
    mkdir -p /workspace /commandhistory /etc/radiaTest && \
    chown -R vscode:vscode /workspace /commandhistory /etc/radiaTest

WORKDIR /workspace
USER vscode

ENV PATH="/home/vscode/.local/bin:/usr/local/bin:$PATH"
ENV PYTHONPATH="/home/vscode/.local/lib/python3.9/site-packages"
ENV HOME=/home/vscode
ENV SHELL=/bin/bash
ENV EDITOR=vim
