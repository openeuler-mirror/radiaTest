<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: Update 测试流水线

## 状态

active

## 目标

在 radiaTest 上实现 openEuler update 测试流水线：手动或 API 触发后，对配置的版本列表 × 双架构，全并行执行 5 个测试模块（docker、kernel、pkgcmd、pkgmanage、pkgserver），收集日志和子用例结果，Web UI 看板展示。

## 范围和非目标

### 范围

- Pipeline 编排层（配置、触发、Run 管理）
- 模块模板表和 CRUD
- pkgcmd/pkgserver 用例预筛选（repodata 解析 + env_type 拆分）
- 物理机执行模式
- VM 挂死检测和 console 诊断
- 子用例结果解析和存储
- 日志收集和共享卷存储
- Web UI 看板（矩阵视图 + 多级下钻 + 日志在线查看）
- 外部触发 API 接口

### 非目标

- 自动定时调度（保留 API 接口，但不做主动监测）
- CSV 导出（Web UI 替代）
- EulerPipeline workaround 兼容（全部去掉）
- 测试任务真实 VM 环境联调（ADR 0032 的环境前提，不在本 Plan 范围内）

## 确认决策

见 [ADR 0032](../../adr/0032-update-test-pipeline.md)。

## 数据模型

### 新增表

```text
test_module_templates
  id              UUID PK
  name            VARCHAR(64) UNIQUE  -- docker/kernel/pkgcmd/pkgmanage/pkgserver
  display_name    VARCHAR(128)
  mugen_suite     VARCHAR(255)       -- smoke/ltp/cli-test/pkgmanager-test/service-test
  env_set_num     INTEGER DEFAULT 1  -- pkgmanage=2 (两个用例分开执行)
  node_num        INTEGER DEFAULT 1  -- pkgmanage=2 (control+peer)
  case_filter     VARCHAR(64)        -- none/repodata_packages/service_test_cases
  env_type_split  BOOLEAN DEFAULT FALSE  -- pkgcmd/pkgserver=TRUE
  skip_packages   JSON DEFAULT []    -- 空（不跳过任何包）
  pre_env_script  TEXT
  post_env_script TEXT
  result_parser   VARCHAR(64)        -- none/ltp/pkgcmd/pkgserver/pkgmanage/docker
  created_at, updated_at

update_pipeline_configs
  id              UUID PK
  name            VARCHAR(128)       -- "openEuler Update Weekly"
  module_template_ids JSON []        -- 有序模块模板 ID 列表
  versions        JSON []            -- ["20.03-LTS-SP4", ...]
  archs           JSON []            -- ["aarch64", "x86_64"]
  repo_base_url   VARCHAR(255)       -- http://121.36.84.172/repo.openeuler.org
  created_at, updated_at

update_pipeline_runs
  id              UUID PK
  config_id       FK update_pipeline_configs
  version         VARCHAR(64)        -- "24.03-LTS-SP3"
  status          VARCHAR(32)        -- pending/running/succeeded/failed
  triggered_by    VARCHAR(64)        -- user_id 或 "api"
  triggered_at    TIMESTAMP
  completed_at    TIMESTAMP NULL
  created_at, updated_at

update_pipeline_run_jobs
  id              UUID PK
  pipeline_run_id FK update_pipeline_runs
  module_template_id FK test_module_templates
  arch            VARCHAR(32)        -- aarch64/x86_64
  env_type        VARCHAR(32) NULL   -- vm/physical（pkgcmd/pkgserver 拆分用）
  test_job_id     VARCHAR(36) NULL   -- 关联 test_jobs.id
  status          VARCHAR(32)       -- pending/created/running/succeeded/failed
  created_at, updated_at

test_case_run_details
  id              UUID PK
  case_run_id     FK test_case_runs
  sub_test_name   VARCHAR(255)       -- LTP: syscalls_01, pkgcmd: bash, pkgserver: service_restart
  status          VARCHAR(32)        -- passed/failed/skipped/error
  detail          JSON               -- 额外信息
  created_at

test_log_artifacts
  id              UUID PK
  pipeline_run_id FK update_pipeline_runs NULL
  job_id          FK test_jobs
  module          VARCHAR(64)        -- docker/kernel/pkgcmd/pkgmanage/pkgserver
  arch            VARCHAR(32)
  artifact_type   VARCHAR(64)        -- mugen_logs/mugen_results/auxiliary/console_capture
  artifact_name   VARCHAR(255)       -- check_update.log, ltp.log, console-output.txt 等
  storage_path    VARCHAR(512)       -- /data/test-logs/<pipeline_run_id>/<module>/<arch>/<filename>
  created_at
```

### 扩展现有表

- `test_case_runs`: 新增 `skipped` 状态（无用例的包）
- `test_jobs`: 新增 `pipeline_run_job_id` (nullable FK)
- `test_env_nodes`: 物理机模式只设 `resource_id`、不设 `vm_request_id`

## 模块边界

### 新增后端模块

```text
backend/app/modules/pipelines/
  models.py          -- 5 张新表的 ORM 模型
  schemas.py         -- Pydantic 请求/响应模型
  service.py         -- Pipeline 配置 CRUD、触发、Run 管理
  router.py          -- API 路由
  repodata.py        -- 解析 repodata/primary.xml.gz 获取包列表
  case_planner.py    -- 匹配包列表和 Mugen 用例索引，按 env_type 拆分
  log_collector.py   -- SSH 到 VM/物理机拉取整理好的日志包
  result_parser.py   -- 各模块子用例结果解析（LTP/pkgcmd/pkgserver/...）
```

### 扩展现有模块

```text
backend/app/modules/test_management/
  envs/
    vm.py            -- 现有（不变）
    physical.py      -- 新增：物理机执行模式（选资源→占用→SSH→执行→保留）
  execution.py       -- 扩展：物理机 EnvSet 支持
  frameworks/
    mugen_runner.py  -- 扩展：心跳线程、挂死检测、console 诊断
```

### 新增前端

```text
frontend/apps/web-antd/src/views/update-pipelines/
  list.vue           -- Pipeline 配置列表和触发按钮
  detail.vue         -- Pipeline Run 详情（矩阵看板 + 下钻）
  module-detail.vue  -- 模块×架构详情（Mugen 用例列表 → 子用例 → 日志）
  templates.vue      -- 模块模板管理
```

### 新增 API

```text
GET    /api/v1/update-pipelines/configs              -- Pipeline 配置列表
POST   /api/v1/update-pipelines/configs              -- 创建配置
PUT    /api/v1/update-pipelines/configs/{id}         -- 更新配置（版本列表、模块）
POST   /api/v1/update-pipelines/trigger              -- 触发流水线
GET    /api/v1/update-pipelines/runs                 -- Run 列表
GET    /api/v1/update-pipelines/runs/{id}            -- Run 详情（矩阵视图数据）
GET    /api/v1/update-pipelines/runs/{id}/jobs/{job_id}  -- 模块详情（用例+子用例）
GET    /api/v1/update-pipelines/runs/{id}/logs       -- 日志列表
GET    /api/v1/update-pipelines/runs/{id}/logs/{artifact_id}  -- 日志内容
GET    /api/v1/update-pipelines/module-templates     -- 模板列表
PUT    /api/v1/update-pipelines/module-templates/{id} -- 更新模板
```

## 任务分解

### Task 1: 数据模型和迁移

- 创建 5 张新表的 ORM 模型
- 扩展 TestCaseRun 新增 `skipped` 状态
- 扩展 TestJob 新增 `pipeline_run_job_id`
- Alembic 迁移脚本
- 验证：迁移成功，表结构正确

### Task 2: 模块模板和 Pipeline 配置 API

- TestModuleTemplate CRUD（list/get/update）
- UpdatePipelineConfig CRUD（list/get/create/update）
- 预填充 5 个模块模板的初始数据
- 前端模板管理和配置页面
- 验证：API 能列出模板和配置，前端能展示

### Task 3: Pipeline 触发和 Run 管理

- `POST /trigger` 接口：根据 config 的版本×架构矩阵创建 PipelineRun
- 每个 PipelineRun 为每个模块×架构创建 UpdatePipelineRunJob
- pkgcmd/pkgserver 的 env_type 拆分（为 vm/physical 各创建一个 RunJob）
- 每个 RunJob 创建对应 TestJob（预分配 TestCaseRun）
- 触发 API 支持外部调用（无认证或 token 认证）
- 验证：触发后数据库中 Run/RunJob/TestJob 记录正确

### Task 4: Repodata 解析和用例规划

- `repodata.py`: HTTP 请求 `repodata/repomd.xml` → `primary.xml.gz` → 解析包名列表
- `case_planner.py`: 包列表 × mugen_cases 表 → 匹配有用例的包 → 按 env_type 拆分
- 无用例的包创建 `skipped` TestCaseRun
- 验证：给定版本和仓库 URL，能正确解析包列表并拆分用例

### Task 5: 物理机执行模式

- `envs/physical.py`: 选择物理资源 → 创建租约 → 设 node.resource_id → 不创建 VM
- 扩展 `execution.py: execute_env_set` 支持物理机 EnvSet
- 物理机 SSH 使用资源凭据（ssh_username + decrypt(ssh_password_ciphertext)）
- 测试完保留环境和租约（不释放、不销毁）
- 验证：能选择物理资源、SSH 执行 Mugen、结果正确记录

### Task 6: 心跳检测和挂死诊断

- `mugen_runner.py`: 执行 case 时启动后台心跳线程（30s SSH `echo ok`）
- 连续 3 次失败 → 判定挂死 → SSH 到 VM 宿主机 `virsh console` / `virsh domstate`
- console 输出存为 test_log_artifacts（artifact_type=console_capture）
- TestCaseRun 标记为 `error`，error_code=`vm_hang`
- 物理机：BMC IPMI serial console（如果可用）
- 验证：模拟 SSH 超时，心跳检测触发，console 输出被捕获

### Task 7: 子用例结果解析

- `result_parser.py`: 各模块的子用例解析器
  - LTP: 解析 `results/*.log` 提取子用例 pass/fail
  - pkgcmd: 解析 Mugen `results/<suite>/succeed|failed|skipped/` 目录
  - pkgserver: 解析 Mugen 标准 results 目录（改造后不再用 override 生成的文件）
  - docker: 解析 `check_update.log` 和 smoke results
  - pkgmanage: 解析 fail_list 文件
- 结果存入 test_case_run_details 表
- 在 Mugen 执行后（post_env_script 或独立步骤）触发解析
- 验证：各模块能正确解析子用例结果并存入数据库

### Task 8: 日志收集任务

- `log_collector.py`: PipelineRun 所有模块完成后执行
- SSH 到每台 VM/物理机，拉取 `/tmp/module-logs/` 下整理好的日志
- 存到 radiaTest 服务器共享卷 `/data/test-logs/<pipeline_run_id>/<module>/<arch>/`
- 创建 test_log_artifacts 记录
- 共享卷挂载到 worker 容器
- 验证：日志文件正确收集到服务器，数据库记录路径正确

### Task 9: Web UI 看板

- Pipeline Run 详情页：模块×架构矩阵，每格 pass/fail/skip 计数 + 状态色块
- 点击格子 → 模块详情页：Mugen 用例列表（suite/case/exit_code/status）
- 点击用例 → 子用例列表（LTP 子用例、每包结果、每服务结果）
- 点击子用例 → stdout/stderr/辅助日志在线查看
- 日志从共享卷读取，API 返回内容
- 验证：矩阵正确渲染，下钻链路完整，日志可查看

### Task 10: 全链路集成

- 5 个模块模板的 pre_env_script 和 post_env_script 编写
- 从 lkp-tests 脚本迁移逻辑，去掉 EulerPipeline workaround
- 端到端验证：触发 → 创建 VM/物理机执行 → Mugen 执行 → 子用例解析 → 日志收集 → 看板展示
- 验证：完整流水线跑通，看板数据正确

## 验证命令

```bash
# 数据库迁移
cd backend && alembic upgrade head

# 后端检查
./scripts/check.sh all

# 前端检查
cd frontend && pnpm run lint && pnpm run build

# 端到端
# 1. 确认模块模板和 Pipeline 配置已预填充
# 2. 触发一个版本+架构的最小流水线
# 3. 等待执行完成
# 4. 看板展示结果
```

## 当前进度

- [x] Task 1: 数据模型和迁移
- [x] Task 2: 模块模板和 Pipeline 配置 API
- [x] Task 3: Pipeline 触发和 Run 管理
- [x] Task 4: Repodata 解析和用例规划
- [x] Task 5: 物理机执行模式
- [x] Task 6: 心跳检测和挂死诊断
- [x] Task 7: 子用例结果解析
- [x] Task 8: 日志收集任务
- [x] Task 9: Web UI 看板
- [x] Task 10: 全链路集成

## 发现和未解决问题

- 无
