<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 版本管理（RC 版本 + 里程碑 + 软件包比对）

## 状态

active

## 目标

在 Kronos 新增「版本管理」域，支撑 RC 版本测试的最核心实际操作：版本与 RC 里程碑
管理、两个 RC 轮次间的软件包比对（binary / source / 同名异构 / 重复包四类视图）、
比对结果查询/筛选/导出。最终目标是让 Kronos 能产出与负责人 `pkg_compare` 工具链
逐项一致的交付内容（7 个 xlsx 的差异口径）。

产品行为、页面、API、权限与验收标准见 [版本管理功能规格](../../spec/0006-version-management.md)。

## 背景

- Kronos 目前只做 update 测试（pipelines 域），无"版本 / RC 轮次"概念。
- RC 版本测试的实际操作（参考负责人交付与 radiaTest）：
  - 一个待发布版本（如 `openEuler-26.09-DevStation`）下按周出多轮 RC；
  - 每轮与上一轮做软件包比对，得出每状态包集合（ADD/DEL/VER_UP/… 全量与同名异构、
    重复包），作为后续"差异→筛选用例→单包测试"的输入；
  - 负责人交付物为 RAR 内含 7 个 xls（everything+EPOL × binary/source/同名异构，
    everything 另加 same-binary），语义为 radiaTest 生产 `compare_str_version`
    （非 PR 初版的朴素字符串比较）。
- 关键事实（实测确认）：
  - source 清单只有公网 `http://121.36.84.172/dailybuild/EBS-<product>/…` 有
    （内网 94 镜像无 source 树）；公网 dailybuild 目录列表为 `title=` 格式，
    与 `pkg_compare` 的抓取正则一致；
  - 物理机 PXE 装机走 94 内网 OS 树（`physical_install_images`），与比对数据源
    **必须隔离**，PXE 表零改动。

## 范围

1. 前端：新增「版本管理」菜单与 `/versions` 页面（RC tab 实做、Update tab 占位）；
   版本详情 → 轮次测试控制台（四 tab 结构，「软件包比对」实做，其余结构占位）；
   删除「流水线类型」菜单/路由/页面（后端 API 保留）。
2. 数据模型：`versions` / `milestones` / `rc_milestone_compares` /
   `rc_package_compare_results` 四张新表 + Alembic 迁移；versions 回填。
3. API：版本/里程碑 CRUD、触发比对、结果查询（分页+筛选+汇总）、全量导出。
4. 比对能力：radiaTest 生产语义（compare_str_version、name.arch 键、
   select_high_pkg、重复包检测）；目录列表 title=/href= 双正则抓取 + 磁盘缓存；
   Celery 异步 + redis 并发锁；source 缺失容忍。
5. 导出：zip 内 7 个 xls（全量含 SAME，xlwt，命名与 `pkg_compare` 交付一致）+
   单视图 CSV「当前筛选」。

## 非目标

- 差异 → 筛选用例 → 流水线执行（比对结果页已留占位按钮，实现方式见"后续扩展"）。
- 版本质量看板（问题解决率、特性清单、转测 checklist 等）与 update 版本监管。
- 里程碑与 PXE 装机的整合（`physical_install_images` 零 DDL、零逻辑改动）。
- 自动发现 dailybuild 轮次（轮次由用户在创建里程碑时登记 build_url）。
- RAR 打包（本期导出 zip；rar 后续按需加）。

## 确认决策（grilling 收敛）

| # | 决策 |
| --- | --- |
| 1 | 页面 = 版本管理菜单；RC tab 实做 + Update tab 占位；「流水线」菜单保留 |
| 2 | 数据模型四表：versions / milestones / rc_milestone_compares / rc_package_compare_results |
| 3 | 版本 = `name(=os_version) / version_type / status / 起止 / remark`；迁移回填 distinct os_version，name 带 `openEuler-` 前缀 |
| 4 | 里程碑 = 版本下 round 实体，关联 optional 语义（不参与 PXE 装配流） |
| 5 | 里程碑登记 1 个比对构建根 URL（默认 `121.36.84.172/dailybuild/EBS-`，可配置），含 kernel 变体；PXE 完全不动 |
| 6 | 抓取 = 目录列表双正则 + 磁盘缓存；比对内容 binary + source + 同名异构 + 重复包四类；source 缺失容忍 |
| 7 | 比对任务 = Celery 异步 + redis 锁；每次比对独立实例可回溯 |
| 8 | 存储 = 非 SAME 变更行落库；全量（含 SAME）导出时现场重算 |
| 9 | 比对语义 = radiaTest 生产 `compare_str_version`（与负责人交付逐项一致） |
| 10 | 权限 = 版本/里程碑写操作 TSE/ADMIN；查看/比对/导出 = 登录即可 |
| 11 | API 前缀 `/api/v1/versions`、`/api/v1/milestones`、`/api/v1/compares` |
| 12 | `physical_install_images` 不加外键（推翻早前 Q4 草案）：PXE 表零改动 |
| 13 | 里程碑加 `pxe_round_label`（从 build_url 自动推导），用于"94 是否有装机源"只读提示注释（不校验） |
| 14 | 导出 = zip 内 7 个 .xls（xlwt，全量含 SAME）+ 单视图 CSV |
| 15 | 配置：`rc_dailybuild_base_url`、`rc_pkglist_cache_dir`、`rc_export_dir` 进 config + deploy/server.env.example |
| 18 | 轮次测试控制台：每轮一个管理页（测试进展/软件包比对/用例筛选/测试模块）；本期只实做比对 tab，其余结构占位；测试进展数据待执行期回填 |

## 数据模型

新增表（backend/app/modules/rc_management/*）：

```text
versions
  id UUID PK
  name VARCHAR(64) UNIQUE        -- os_version，如 openEuler-26.09-DevStation
  version_type VARCHAR(16) NULL  -- INNOVATION / LTS / LTS-SPx
  status VARCHAR(16)             -- testing / finished（测试中 / 已结束）
  start_time, end_time DATE NULL
  remark TEXT NULL
  created_by VARCHAR(64)
  时间戳

milestones
  id UUID PK
  version_id FK versions
  name VARCHAR(64)               -- alpha / round1 / round2 / release ...
  kernel_variant VARCHAR(64) NULL-- 展示用，如 6.18 / 6.6
  build_url VARCHAR(1024)        -- 比对构建根 URL（含 kernel 变体）
  pxe_round_label VARCHAR(128) NULL -- 从 build_url 推导，如 rc4_openeuler-...
  compare_base_milestone_id UUID NULL -> milestones.id  -- 默认前一轮
  start_time, end_time DATE NULL
  created_by VARCHAR(64)
  时间戳
  UNIQUE(version_id, name)

rc_milestone_compares
  id UUID PK
  milestone_id FK milestones     -- 当前轮（target）
  base_milestone_id FK milestones -- 比对基准
  status VARCHAR(16)             -- pending / running / succeeded / failed
  total_changed INT NULL         -- 汇总：变更行数
  summary JSON NULL              -- 各 kind/状态计数，供卡片
  error_msg TEXT NULL
  triggered_by VARCHAR(64)
  triggered_at, completed_at
  UNIQUE(milestone_id, base_milestone_id)  -- 不限制多实例？→ 见风险，默认允许多次
  (实际按决策 7：允许多次实例，故不带 UNIQUE；按需加 id 幂等键)

rc_package_compare_results
  id BIGINT PK AUTO
  compare_id FK rc_milestone_compares
  kind VARCHAR(8)                -- binary / source / isomer / repeat
  repo_path VARCHAR(32)          -- everything / EPOL/main
  pkg_name VARCHAR(255)          -- spec 裸包名（binary/source/isomer；作为 Mugen 用例
                                 --  匹配键，与 MugenCase.suite_name 对齐，不拼 arch）；
                                 -- repeat 行为展示存 name.arch（如 llvm-bolt.x86_64）
  arch VARCHAR(32) NULL          -- binary/source=各架构；isomer=NULL；repeat=对应架构
  status VARCHAR(16)             -- ADD/DEL/VER_UP/VER_DOWN/REL_UP/REL_DOWN/DIFFERENT/LACK/REPEAT
  rpm_base TEXT NULL             -- binary/source/repeat: 基准轮 rpm 文件名(重复包为 \n 多行)；isomer: rpm_x86
  rpm_target TEXT NULL           -- binary/source/repeat: 目标轮 rpm 文件名；isomer: rpm_arm
  created_at
  INDEX(compare_id, kind, repo_path, arch, status)
```

- 仅存非 SAME 变更行（决策 8）。
- 迁移：创建四表 + 从 `physical_install_images` distinct `os_version` 回填 `versions`。

## API

```text
GET    /api/v1/versions?search=&page=         版本分页列表（每页 50，PageResponse）
POST   /api/v1/versions                       新建版本        [TSE/ADMIN]
GET    /api/v1/versions/{id}                  版本详情
PUT    /api/v1/versions/{id}                  编辑版本        [TSE/ADMIN]
DELETE /api/v1/versions/{id}                  删除(有里程碑拒绝) [TSE/ADMIN]
GET    /api/v1/versions/{id}/milestones       版本下里程碑列表
POST   /api/v1/milestones                     创建里程碑      [TSE/ADMIN]
PUT    /api/v1/milestones/{id}                编辑里程碑      [TSE/ADMIN]
DELETE /api/v1/milestones/{id}                删除(有比对记录拒绝) [TSE/ADMIN]
POST   /api/v1/milestones/{id}/compares       触发比对 (body: base_milestone_id)
GET    /api/v1/compares/{id}                  任务状态+汇总
GET    /api/v1/compares/{id}/results          结果(分页 + repo/arch/kind/status 筛选)
GET    /api/v1/compares/{id}/export           导出 zip(7 xls 全量)  [登录]
GET    /api/v1/milestones/{id}/playbook       可选：该轮 94 装机源提示(查询 physical_install_images)
```

- build_url 校验：创建/编辑里程碑时正则校验含 `{version}/{round}/…/` 结构并推导
  `pxe_round_label`（`rc\d+_openeuler-[0-9-]+` 或 `alpha_openeuler-…`）。

## 比对实现

1. `rpm_util.py`：移植 radiaTest 生产比对语义
   - `parse_rpm_file_name`（name-version-release.arch.rpm）
   - `compare_str_version`（分段/数字/oe* 特判，返回 0/1/2）
   - `select_high_pkg`、`rpmlist2rpmdict`（name.arch 键、重复包收集）、
     `compare_rpm_dict`（binary/source）、`compare_rpm_dict2`（同名异构
     DIFFERENT/LACK）
2. `pkglist_fetcher.py`：目录列表抓取
   - `GET {build_url}/{repo}/{arch}/Packages/`（source: `{build_url}/source/Packages/`、
     `{build_url}/EPOL/main/source/Packages/`）
   - 正则同时解析 `title="…rpm">` 与 `href="…rpm"`；`sort -u` 去重后落到
     `rc_pkglist_cache_dir/<version>/<round>/<repo>-<arch>.pkgs`（有缓存不重复抓）
   - source 404 时该块标记 skip，不中断整次比对。
3. `service.py` 触发：校验 target/base 同属一个版本 → redis 锁
   （key=`rc_compare:<target>:<base>`，30min 过期）→ Celery 任务抓取+比对+落库 →
   状态 pending→running→succeeded/failed + `total_changed` + `summary`。
4. `export_service.py`：读缓存清单按同一语义重算**全量**（含 SAME），xlwt 生成 7 个
   xls（sheet 名/表头/列宽与 `pkg_compare` 一致：二进制对比/源码对比；`[arch|包名,
   rcN, rcM, 比对结果]`；同名异构 `[包名, x86_64, aarch64, 比对结果]`；
   same-binary 三列），zip 打包输出到 `rc_export_dir`。

## 后续扩展：差异 → 筛选用例 → 流水线执行（可扩展为）

当前筛选得到的包集合就是触发测试的输入。扩展数据流：

1. 用户按「比对内容 / 仓库 / 架构 / 变更」筛出包集合（`pkg_name` + `arch` + `repo_path` +
   `status`），页面可将当前筛选子集提交为一次「RC 变更用例」流水线触发。
2. 后端复用已有 `case_planner.plan_cases`（`MugenCase.suite_name == 包名` 精确匹配，按
   env_type 拆 vm/physical）与 `service_test_cases`（systemd unit → `oe_test_service_*`
   等）筛出 mugen 用例；无用例的包保留为"无用例"事实。
3. 复用现有 pipelines 执行链路（模块模板 / mugen executor / 日志收集 / 结果回填）跑测试，
   页面把执行结果挂回该次比对实例（`compare_id` 关联）。

本期已为此预留：`rc_package_compare_results.pkg_name` 存**裸 spec 包名**（不拼 arch），
`arch` 独立列；结果页比对结果区已留禁用的「筛选用例并触发测试」占位按钮；`compare_id`
作为回溯与关联键。

## 前端

- 路由：删 `/pipelines/types`；新增 `/versions`（版本管理，RC tab 页面）、
  `/versions/{id}`（版本详情：里程碑列表）、`/versions/{id}/milestones/{mid}`（轮次
  测试控制台）。菜单配置同步。
- 页面结构（已 grill，Q18=方案 A）：
  - 版本列表（表格 + 搜索 + 新建版本）
  - 版本详情：头（名称/类型/status/轮次数/当前轮 + 创建里程碑）；里程碑表
    （轮次/起止/内核/base/最新比对 + 操作「测试管理」）；创建里程碑弹窗
    （名字/起止/内核/build_url + 「94 装机源」只读提示）
  - **轮次测试控制台（里程碑详情页）**：每个轮次 = 该轮的测试管理页，四个 tab：
    - **测试进展**：管控本轮测试活动状态/通过率（本期为空态占位，数据待引例/模块
      执行那期回填）
    - **软件包比对**：触发比对 + 结果筛选（四类视图×仓库×架构×变更）+ 分页 +
      导出 CSV 当前筛选 / 导出 zip 全量交付（本期实做）
    - **用例筛选**：按比对结果筛选出的变更包匹配 mugen 用例并触发流水线
      （本期占位 + 禁用按钮，可扩展）
    - **测试模块**：与 update 一致的模块型测试（docker/kernel/pkgcmd/pkgserver 等）
      登记与执行（预留占位）
  - Update tab：占位空态卡片
- 校验：创建版本/里程碑表单必填与 URL 格式；删除有子资源时给出后端拒绝提示。

## 任务分解

- [x] T1 数据模型与迁移：四表 + versions 回填 + settings 三项 + Alembic
      验证：迁移成功、表结构与回填正确
- [x] T2 版本/里程碑 CRUD API + 权限（TSE/ADMIN）+ pxe_round_label 推导 + 94 提示查询
      验证：API 用例 + 权限拦截
- [x] T3 rpm_util 移植（compare_str_version / select_high_pkg / 两 compare dict）
      验证：单测覆盖 9 状态与 oe*/数字分段；用真实清单对照 pkg_compare 输出
- [x] T4 pkglist_fetcher（双正则抓取 + 磁盘缓存 + source 404 容忍）
      验证：对 121.36.84.172 真实 build 抓每 repo/arch 清单
- [x] T5 比对任务（celery + redis 锁 + 落库 + 汇总）
      验证：rc3-vs-rc4 实际比对，结果行数与交付各状态计数一致
- [x] T6 结果查询（分页 + repo/arch/kind/status 筛选 + 汇总卡片数据）
      验证：接口筛选用例
- [x] T7 导出（zip 7 xls 全量 + CSV 当前筛选）
      验证：导出文件与 pkg_compare 交付 7 文件状态计数一致
- [x] T8 前端：菜单/路由（删流水线类型）+ 版本列表 + 版本详情 + 轮次测试控制台
      （软件包比对实做，测试进展/用例筛选/测试模块占位）+ 导出按钮
      验证：pnpm lint + build；交互手测
- [x] T9 TDD 收尾 + `./scripts/check.sh backend` 全绿（560 passed）+ 前端 typecheck/build
      通过 + 两轮代码审计（发现并修复导出默认 fetch、redis 锁 key、文档同步等）
- [ ] T10 部署 dev + 端到端：rc3-vs-rc4 复现交付数字；版本/里程碑 CRUD；
      导出 zip 在线可下；流水线类型菜单消失但后端 API 可用

## 当前进度

- [x] 后端 T1-T7、前端 T8、T9 检查与审计：`check.sh backend` 560 passed、ruff 零告警、
      前端 typecheck + build 通过
- [ ] T10 部署 dev + 端到端（真实 rc3/rc4 对照交付数字）
- [ ] 代码审查记录、合入 main、计划移入 completed/

## 验证命令

```bash
cd backend && alembic upgrade head
UV_CACHE_DIR="${TMPDIR:-/tmp}/kronos-uv-cache" ./scripts/check.sh all
cd frontend/apps/web-antd && pnpm run lint && pnpm run build
```

## 验收场景

1. 登录后左侧菜单出现「版本管理」，无「流水线类型」；`GET /api/v1/pipelines/types`
   仍可用（建测试模块模板下拉正常）。
2. 版本列表展示回填的历史 os_version（如 openEuler-26.09-DevStation）。
3. 建版本 → 建里程碑（roundN，填 build_url）→「94 是否有装机源」提示正确
   （该轮在 physical_install_images 有 OS 树时提示"有"）。
4. 对 rc3 / rc4（openEuler-26.09-DevStation）触发比对：任务成功；结果各状态计数与
   `pkg_compare` 交付一致（everything binary: SAME 22401 / VER_UP 469 / REL_UP 461 /
   ADD 117 / DEL 27；同名异构 LACK 186；EPOL：ADD 2038 …）。
5. 结果页筛选/分页/汇总卡正确；导出 zip 解压后 7 个 xls 与负责人交付逐项一致。
6. 权限：TE 用户可查看/比对/导出；创建版本/里程碑被拒（403）。

## 风险

- **源可达性**：比对清单依赖 `121.36.84.172` 公网可达与目录结构稳定；结构变化时
  双正则+repodata 回退兜底有限，需随镜像演进维护。
- **缓存膨胀**：每 (版本,轮次,repo,arch) 一份清单，多版本累积占用磁盘；按
  `rc_pkglist_cache_dir` 控制，必要时加清理策略（本期人工/运维手动清）。
- **比对口径漂移**：一旦语义/数据源与 `pkg_compare` 不一致，交付对账会失真；用
  T3/T5/T7 三个对照点锁定（rpm_util 单测、真实比对计数、导出文件计数）。
- **重复比对实例**：允许多次实例可回溯，但可能产生冗余；页面上用"最新比对"聚合，
  详情下钻历史实例。

## 变更记录

- 2026-09-10（用户决策）：取消 versions 自动回填——历史版本不进入平台，版本由用户
  手动创建。轮次命名对齐交付：第一轮 alpha，其后 rc1…rcN；创建版本时「RC 轮次数」
  填 N 生成 alpha + rc1…rcN（共 N+1 个），每轮 7 天从版本开始日期顺排。构建 URL 按
  命名规则自动生成通配模板（抓取时列目录解析最新构建，支持人工编辑精确 URL），
  `milestones.build_url` 改可空（迁移 0046），缺失/未匹配返回 400；0044 改 no-op。
  对应 Spec 0006 与 ADR 0041 已同步。- 2026-09-10（用户决策）：release 全量跑用例——创建卡片新增「全选用例」按钮；
  物理机用例执行与否改为配置开关 `release_physical_enabled`（默认关闭），
  开启时物理用例租用物理机执行，关闭时 NOT_EXECUTED 跳过；release 模板
  env_type 升级为 both（既有行运行时自动升级）。对应 Spec 0003 §9 已同步。
