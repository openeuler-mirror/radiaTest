<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 物理机重装系统按钮归位 + 安装镜像数据补齐

## 状态（2026-09-04 归档）

`e81be1d` 部署后在 kimariyb 环境 A 组端到端已人工验：
- 资源管理列表 · 物理机行操作列出现"重装"按钮，详情抽屉无重装按钮（`canInstall` 生效条件为 `ADMIN + PHYSICAL + bmc_ip/mac_address/primary_ip 齐全 + ≠maintenance`，与 `views/resources/index.vue` 一致）
- "重装系统"弹窗镜像下拉按目标机 arch 过滤（DB 已 seed：aarch64 25 条、x86_64 24 条互不可见）
- 提交装机走 `installResourceApi`，无 500

## 目标

1. 把"重装系统"按钮从物理机**详情抽屉**移到物理机**列表行操作列**，与详情/编辑/释放同级，并从抽屉中移除。
2. 用 radiaTest `i_mirroring` 真实镜像数据灌入 `physical_install_images` 表，使重装弹窗能选镜像；落成可复现 seed CLI。

## 范围和非目标

### 范围

- 前端 `views/resources/index.vue`：列表行 action 列加"重装系统"按钮（`canInstall`）；详情抽屉 `#extra` 移除重装按钮
- 后端 `app/cli.py` + `app/modules/resources/`：新增 `seed-install-images --json-file` 子命令，按 `(os_version, arch)` 幂等 upsert
- 用 radiaTest official 稳定版镜像集生成 `install-images.json`（仓库外），灌入 dev 库
- 同步更新 [ADR 0014](../../adr/0014-physical-machine-pxe-install.md) 第 76 行、`CONTEXT.md` 第 476 行：UI 位置由"详情页"改为"列表行操作"

### 非目标

- 不建安装镜像管理 UI（ADMIN 暂用已有 create/delete API 维护）
- 不动后端 PXE 编排（`pxe_install.py` / `host_scripts/pxe-install.sh` / ks·grub 模板）
- 不动详情抽屉里的 编辑/占用/释放/强制释放
- 不做 radiaTest 实时同步
- 不灌 `iteration.repo` 每日轮次与 NULL-efi 行（CentOS/AnolisOS/部分 round）

## 确认决策

- **D1（ADR 冲突裁决）**：以代码为准，改代码 + 同步更新 ADR 0014 与 CONTEXT.md 的 UI 位置描述。
- **D2（seed 数据集）**：取 radiaTest `i_mirroring` 中 `location LIKE '%official.repo%'` 且 `efi IS NOT NULL AND location IS NOT NULL` 的行。
  - `os_version` = milestone.name（清理 " release" 后缀）
  - `arch` = frame
  - `efi_url` = efi
  - `repo_url` = location
  - **保留各行原始主机**（`139.9.114.65` 外部镜像 / `172.168.131.94` 内网 PXE）。理由：radiaTest 与 radiaTest 的 PXE 服务器是同一台 172.168.131.94，radiaTest 用这些 URL 成功装机即证明可达；重写主机反而可能在内部镜像未同步的旧版本上 404。
- **D3（制品形式）**：新增 `seed-install-images --json-file`（或 stdin `-`）子命令，复用 `upsert-resource --json-file` 约定。数据 JSON 放仓库外（`/etc/kronos/install-images.json`），CLI 逻辑在仓库内。详见确认门。

## 数据集（radiaTest official 稳定版，~26 版本 × 2 架构）

openEuler-20.03-LTS / -SP1 / -SP2 / -SP3 / -SP4；20.09；21.03；21.09；22.03-LTS / -64kb / -SP1 / -SP2 / -SP3 / -SP4；22.09；23.03；23.09；24.03-LTS / -SP1 / -SP2 / -SP3 / -SP4；24.09；25.03；25.09。

每行：`{os_version, arch, efi_url, repo_url}`。主机混用 139.9.114.65 与 172.168.131.94，保留原值。

## 任务分解

### Task 1: 后端 seed CLI

- `app/modules/resources/service.py` 加 `upsert_install_image(db, payload)`（按 `(os_version, arch)` 查存在→更新，否则创建）
- `app/cli.py` 加 `seed_install_images(args)` + `seed-install-images` subparser（`--json-file` 必需，支持 `-` 读 stdin）
- 验证：`backend/tests/` 加 `test_seed_install_images.py`，断言新建 + 幂等 + 字段正确

### Task 2: 生成数据 + 灌入 dev

- 从 radiaTest .14 导出 official 集 → 生成 `/etc/kronos/install-images.json`
- `python -m app.cli seed-install-images --json-file /etc/kronos/install-images.json`（在 backend 容器/uv 环境跑）
- 验证：`select count(*) from physical_install_images;` > 0

### Task 3: 前端按钮归位

- `views/resources/index.vue` 列表行 action 列（`column.key === 'action'`）加"重装系统" `<Button v-if="canInstall(...)">`
- 详情抽屉 `#extra` 移除重装 `<Button>`（保留 编辑/占用/释放/强制释放）
- 验证：dev :8080 物理机管理页——行操作列有"重装系统"；详情抽屉无；点重装弹窗镜像下拉非空

### Task 4: 文档同步

- [ADR 0014](../../adr/0014-physical-machine-pxe-install.md) 第 76 行："前端物理机详情页加'重装系统'按钮" → "前端物理机列表行操作列加'重装系统'按钮"
- `CONTEXT.md` 第 476 行："前端物理机详情页有'重装系统'按钮" → "前端物理机列表行操作有'重装系统'按钮"
- `docs/runbook/server-deployment.md` 补 `seed-install-images` 用法（若 runbook 有 seed 章节）

## 验证命令与验收场景

```bash
./scripts/check.sh all
# dev 库镜像非空
docker exec kronos-dev-postgres-1 psql -U kronos -d kronos_dev -c "select count(*) from physical_install_images;"
```

验收场景：

- 物理机管理页：每条物理机行操作列出现"重装系统"（满足 `canInstall`：ADMIN + PHYSICAL + 有 bmc_ip/mac/primary_ip + 非 maintenance）
- 点"详情"打开抽屉：抽屉头部按钮区**无**"重装系统"
- 点行内"重装系统"：弹窗镜像下拉有 ~52 项，选一个可"开始装机"
- `seed-install-images` 重复执行：created=0 updated=N（幂等）

## 进度

- [x] Task 1 后端 seed CLI — `app/modules/resources/service.py:upsert_install_image` + `app/cli.py:seed-install-images --json-file`
- [x] Task 2 数据生成 + 灌入 — `/etc/kronos/install-images.json`(49 条 official 稳定版,仓库外);dev 库 `physical_install_images` 已灌入 49 行
- [x] Task 3 前端按钮归位 — `views/resources/index.vue`:列表行 action 列加重装按钮;详情抽屉 `#extra` 移除重装按钮
- [x] Task 4 文档同步 — ADR 0014 第76行、CONTEXT 第476行、runbook 第3节补 `seed-install-images` 用法

## 验证证据

- `tests/test_seed_install_images.py`:3 passed(新建 + 幂等更新 + 不同 arch 独立)
- 后端 `ruff check app/cli.py app/modules/resources/service.py tests/test_seed_install_images.py`:All checks passed
- 全量后端 pytest:247 passed,1 pre-existing failure(`test_enqueue_run_job_raises_without_broker`,pipeline/broker 相关,与本次改动无交集)
- dev 库 `select count(*) from physical_install_images` = 49
- 前端:RotateCw 已导入复用,无新 import;改动为纯模板(移动按钮+新增复用已有函数/图标的按钮);typecheck 依赖 pnpm install(本机无 node_modules),留待 `./scripts/check.sh all` 或 deploy 构建验证

## 待办(部署验证)

- 前端 typecheck/build:`./scripts/check.sh frontend`(需 pnpm install)或 deploy 构建时 vue-tsc
- 部署到 dev 后浏览器验收:行操作列有重装按钮、抽屉无、弹窗下拉非空

---

## Round 2:修复装机内部错误 + 按架构过滤 + 改名

### 背景与根因

部署 dev 后用户点「开始装机」报「内部服务器错误」。后端日志:`AttributeError: 'Resource' object has no attribute 'bmc_ip'` @ `router.py:384 install_resource`。根因:`bmc_ip`/`bmc_username`/`bmc_password_ciphertext` 在 `Resource.physical_spec`(PhysicalResourceSpec)上,而既有 install 代码(提交 3c7f562)把它们当 `resource.*` 直接访问。表空时从没人点过装机,Round 1 灌数据后首次暴露。

### 范围

- 修 `router.py:384` + `pxe_install.py`(173/213/214)BMC 字段访问 → `resource.physical_spec.*`,任务内加 `physical_spec` 非空 guard
- 前端弹窗镜像按目标资源 `arch` 过滤(aarch64 机不显示 x86);`arch` 为 null 降级显示全部
- 行按钮「重装系统」→「重装」(2 字,与详情/编辑/释放一致);弹窗标题保留「重装系统」

### 非目标

- 不改 ADR/CONTEXT(仅修 bug + UI 微调,无架构/决策变化)
- 不动 install 5 步编排逻辑、ks/grub 模板、pxe-install.sh

### 任务

- [x] 回归测试 `test_install_physical_resource_schedules_task`(mock `run_pxe_install_task.delay`,断言 physical_spec 有 bmc_ip 时端点返回 200 `{status:scheduled,task_id}` 而非 500)—— RED 复现 AttributeError,GREEN 通过
- [x] 修 `router.py:384` + `pxe_install.py` BMC 属性访问(guard physical_spec)
- [x] 前端 arch 过滤(`installTargetArch` + `installImagesFiltered` computed + `openInstallModal` 存 arch + Select 用过滤列表)
- [x] 行按钮改名「重装」

### 验证证据

- 回归测试:RED 复现 `AttributeError: 'Resource' object has no attribute 'bmc_ip'` → 修复后 GREEN
- `ruff check router.py pxe_install.py test_resources.py`:All checks passed
- 全量后端 pytest:**248 passed**(+1 新回归测试),1 pre-existing failure(broker,无关)
- 前端:`computed` 已导入,`ResourceRecord.arch` 为 `null | string`,`record.arch ?? ''` 类型安全;改动为模板+1 个 computed+1 个 ref;typecheck 留待 deploy 构建
