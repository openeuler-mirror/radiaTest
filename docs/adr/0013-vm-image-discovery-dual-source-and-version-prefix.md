<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0013：VM 镜像发现双源解析与版本号带 dist 前缀

## 状态

已接受(Accepted)。

## 背景

`vm_image_repo_root` 配置在 dev 服务器上指向 `172.168.131.119`，但 119 上 `mugen.mirror/` 只有 `iteration/` 子目录（3 个版本），没有 `official/` fallback。VM 申请界面只能选到 3 个版本，老版本（如 22.03-LTS-SP1、24.03-LTS-SP1 等）选不到。

实际镜像仓库在 `172.168.131.94` 上有完整的 `iteration/` + `official/` 两层结构：

- `iteration/<dist>/<dist>-<version>/<round>/<arch>/<dist>-<version>-<arch>.qcow2`——RC 轮次镜像，带 round 层
- `official/<dist>/<version>/<arch>/<dist>-<version>-<arch>.qcow2`——已发布镜像，**无 round 层**

现有 `image_discovery.py` 假设 4 层结构（含 round），只能解析 iteration，不能 fallback 到 official。

同时，为了后续支持多 OS（ubuntu 等），`VMImage.os_version` 需要带 `<dist>-` 前缀来区分 OS。流水线配置的版本号也必须同步以 VM 申请的参数为基准。

## 决策

### 1. `vm_image_repo_root` 改成 94 的 `mugen.mirror`（不带 `/iteration`）

配置从 `http://172.168.131.119:9400/repo_list/mugen.mirror/iteration` 改为 `http://172.168.131.94:9400/repo_list/mugen.mirror`。让 `image_discovery.py` 同时查 `iteration/` 和 `official/` 子目录。

### 2. image_discovery 双源解析

`_discover_uncached(root, dist)` 改成：

1. **主源 iteration**：`{root}/iteration/{dist}/{version_dir}/{round}/{arch}/{file}.qcow2`
   - `version_dir` 是 `<dist>-<version>` 形式（如 `openEuler-24.03-LTS-SP3`），直接作为 `os_version`。
   - `image_round` 来自目录名（如 `round-1`）。
2. **Fallback official**：`{root}/official/{dist}/{version_dir}/{arch}/{file}.qcow2`（无 round 层）
   - `version_dir` 是 `<version>` 形式（如 `24.03-LTS-SP3`），需要拼 `f"{dist}-{version_dir}"` 作为 `os_version`。
   - `image_round` 标为 `"official"`（特殊标记值）。
3. **合并去重**：同一 `(dist, os_version, arch)` 三元组如果 iteration 和 official 都有，**优先 iteration**（保留所有 round 选项，弃 official 同名镜像）。

### 3. `VMImage.os_version` 统一带 `<dist>-` 前缀

- iteration：`os_version = version_dir`（已经是 `openEuler-24.03-LTS-SP3` 形式）
- official：`os_version = f"{dist}-{version_dir}"`（拼成 `openEuler-24.03-LTS-SP3`）
- 大小写规范化：`openeuler-24.03-LTS-SP1` 这种小写目录 normalize 成 `openEuler-24.03-LTS-SP1`（dist 首字母大写，其余小写；version 部分保留原样）

### 4. official 镜像的 `image_round = "official"`

`VMRequestCreate.image_round` 必填校验通过（非空）。VM 名字会带 `official` 片段。前端下拉显示 `official` 作为轮次标签。

### 5. 流水线版本号同步带 `<dist>-` 前缀

`PipelineConfig.versions` 字段从 `["24.03-LTS-SP3", ...]` 改成 `["openEuler-24.03-LTS-SP3", ...]`。前端 `KNOWN_VERSIONS` 常量同步改。Alembic 数据迁移给已有的 `pipeline_configs.versions` 数组每个元素加 `openEuler-` 前缀（如果还没带前缀）。

### 6. 前端版本下拉从 `discover_images` 取

`KNOWN_VERSIONS` 常量退役（或保留作 fallback），前端"测试版本"下拉改成从 `GET /api/v1/vm/images` 拿 distinct `os_version`——跟 VM 申请界面同源，保证两边版本号一致。

## 考虑过的方案

- **strip `openEuler-` 前缀**：跟 `PipelineConfig.versions` 当前格式对齐。否决——后续要支持 ubuntu 等多 OS，不带 dist 前缀无法区分。
- **新增 `vm_image_repo_official_root` 配置项**：两个独立配置查后合并。否决——单配置 + 双查更简洁，且 `mugen.mirror/` 下两个子目录是固定约定。
- **official image_round = `""` 空字符串**：跟现有"image_round 默认空"对齐。否决——VMRequestCreate auto install 必填校验会拒，需要改校验逻辑。
- **official image_round = `"release"`**：语义化。否决——跟目录名 `official` 不一致。
- **保留 119 作为主源**：否决——119 上没有 official fallback，只有 3 个版本。
- **保留 `KNOWN_VERSIONS` 硬编码**：否决——硬编码版本列表会过时，从 `discover_images` 取保证跟仓库同步。

## 影响

- 后端 `modules/vms/image_discovery.py`：`_discover_uncached` 改成双源解析 + os_version 带前缀 + 大小写规范化。
- 后端 `core/config.py`：`vm_image_repo_root` 默认值改成 94 的 `mugen.mirror`（不带 `/iteration`）。
- dev 服务器 env 文件：`VM_IMAGE_REPO_ROOT` 改成 `http://172.168.131.94:9400/repo_list/mugen.mirror`。
- 后端 `modules/pipelines/`：`KNOWN_VERSIONS` 常量同步改（或退役）。
- 前端 `pipelines.ts`：`KNOWN_VERSIONS` 改成带前缀，或前端"测试版本"下拉改从 `getVmImagesApi` 取。
- 数据库 Alembic 迁移：`pipeline_configs.versions` 数组每个元素加 `openEuler-` 前缀（如果还没带前缀）。
- `CONTEXT.md`：补充"VM 镜像发现双源解析"和"版本号带 dist 前缀"说明。
- 不改 ADR 0005（VM 生命周期）——本 ADR 是镜像发现层补充，不动 VM 申请/释放链路。
