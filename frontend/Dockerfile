FROM node:24-bookworm-slim AS builder

WORKDIR /app

RUN corepack enable \
    && corepack prepare pnpm@10.33.4 --activate

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
COPY frontend/.npmrc frontend/.node-version ./
COPY frontend/apps ./apps
COPY frontend/internal ./internal
COPY frontend/packages ./packages
COPY frontend/scripts ./scripts
COPY frontend/*.mjs frontend/*.ts frontend/*.json frontend/*.yaml ./

RUN pnpm install --frozen-lockfile
RUN pnpm build
# 部署机 git checkout 可能在 umask 077 下重建文件,静态资源统一可读,
# 避免 nginx worker 因 600 权限返回 403
RUN chmod -R a+rX /app/apps/web-antd/dist

FROM nginx:1.28-alpine

COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web-antd/dist /usr/share/nginx/html

EXPOSE 80
