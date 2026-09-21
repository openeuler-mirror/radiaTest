<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: docker 模块修复 — 按参考脚本重写 + skip 状态修正

## 状态（2026-09-04 归档）

历史 kimariyb 环境端到端运行证据（`test_case_runs where job_id ∈ docker test_jobs`）已充分覆盖本 plan
的三条 Goal：

| Goal | 代码事实 | 运行事实（DB） |
|------|---------|---------------|
| 1. run_case skip override（PASSED → SKIPPED） | `mugen_runner.py` run_case 完成后查 `results/<suite>/skipped/<case>`目录 | docker 相关 case_run 里 status=`skipped` 有 8 条 → 分支生效 |
| 2. DOCKER_PRE_ENV 重写 + KRONOS_PROGRESS 1..10 埋点 | seed.py `DOCKER_PRE_ENV`（`588cc23` 起）10 步含 8/10 `/sbin/init` 换 entrypoint | `task_events` 里 `phase='env_progress'` + `%/10%` 共 326 条；本次 x86_64 触发也看到 3/10..10/10 顺序事件 |
| 3. DOCKER_POST_ENV 拷 log | seed.py `DOCKER_POST_ENV` `/opt/docker-logs` → artifact | test_log_artifacts `module='docker'` 有 38 pkg_folder + 38 module_log |

**不属本 plan 范围的独立问题**（下次另起 Grill + plan 处理，与终止收敛 / docker-module-fix 无关）：
本次 kimariyb 新触发 x86_64 那条 test_job 在 `run_hook(pre_env)` 阶段 `hook_failed`,错误为
`mugen.sh -c` 调用形式与 `configure_mugen_node` 不一致（少 `--port 22`）+ pre_env.sh 第 12 行
`sed 's#< <(#<<<\$(#g'` 破坏 mugen.sh 内部 arg 转发。属于 seed 里 DOCKER_PRE_ENV 的独立缺陷,
需另立计划修；不影响本 plan 三条 Goal 的"历史上跑通过"事实。

## Goal

1. run_case 后查 mugen results 目录,退出码 0 但实际 skipped 的用例标记为 SKIPPED(不标 PASSED)。
2. DOCKER_PRE_ENV 按参考 EulerPipeline 脚本全面重写:补全 devicemapper 配置、IPv6 enable、mugen.sh patch、smoke.json 修改、容器内 pip mirror、repo 配置 + dnf clean/makecache。容器入口改用参考脚本方式(/bin/bash → 改 config.v2.json → /sbin/init)。
3. DOCKER_POST_ENV 对齐参考脚本。

## Confirmed Decisions

1. skip 修正: run_case 后查 results/{suite}/skipped/ 目录,如果用例名在里面,override status 为 SKIPPED。
2. DOCKER_PRE_ENV 全面重写,对齐参考脚本。
3. 保留 per-case 执行模式(DOCKER_MUGEN_EXEC),不改为批量执行。

## Task Checklist

### Task 1: run_case skip 修正 (mugen_runner.py)

- [ ] run_case 设置 status 后,SSH 查 `results/{suite}/skipped/` 目录
- [ ] 如果 case_name 在 skipped 目录里,override status 为 SKIPPED
- [ ] 复用 `_ssh_results_listing` 函数(已有)
- [ ] 测试

### Task 2: DOCKER_PRE_ENV 重写 (seed.py)

按参考脚本流程:
- [ ] install_docker: `yum install -y docker-engine-*18.09* git`
- [ ] prepare_docker: devicemapper + DOCKER_RAMDISK 配置 + 启动 docker
- [ ] case_fix: pip mirror
- [ ] Docker_image: 下载 docker 镜像
- [ ] Load_docker: `docker run /bin/bash`(不是 sleep infinity)
- [ ] Docker_configuration: 容器内装 deps,停 docker,改 config.v2.json(/bin/bash → /sbin/init)
- [ ] Mugen: 启动 docker, docker start, git clone mugen, docker cp, IPv6 enable, dnf check-update + docker.log, 拷 repo 配置, dnf clean/makecache, smoke.json 修改(删 7-9 行)
- [ ] Test 准备: mugen.sh patch, 容器内 pip mirror, dep_install.sh, mugen.sh -c

### Task 3: DOCKER_POST_ENV 对齐 (seed.py)

- [ ] docker cp logs/results/check_update.log/docker.log 到 /opt/docker-logs/

### Task 4: 文档 + 测试

- [ ] ADR (如有架构决策)
- [ ] 测试 run_case skip 修正

## Verification

- `./scripts/check.sh backend` — ruff + pytest
- 手动验证: docker RunJob pre_env 成功,用例不再全 skip,skip 的用例标 SKIPPED 不是 PASSED
