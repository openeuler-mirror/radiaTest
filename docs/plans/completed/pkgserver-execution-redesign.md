<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: pkgserver 执行逻辑重做 — pre_env 发现 + 平台调度

## Goal

拆掉 `oe_test_service_restart` 的 meta-case 模式(case调case),改为:
pre_env 完成装包+分类+new_service 测试,平台读回分类结果按 env_type 动态建 case_run 直接跑独立用例。

## Scope and Non-Goals

### 做
- 重写 `PKGSERVER_PRE_ENV`:拆 `oe_test_service_restart` 的 `pre_test()` + `run_test()` 的 `check_new_service()`,生成 `case_list` 文件 + 全部分析文件。
- 重写 `PKGSERVER_POST_ENV`:`clean_up_env()` + 扫多 suite results + 拷分析文件到 `/opt/pkgserver-logs/`。
- `builder.py`:`case_filter == "service_test_cases"` 返回空 case 列表(运行时发现)。
- `execution.py`:`execute_env_set` 在 pre_env 后,若 `result_parser == "pkgserver"` 且 case_runs 为空,SSH 读 `case_list` → 查 `MugenCase` 表 env_type → 过滤本 env_set → 动态建 case_run。
- `tasks.py`:`_self_collect_logs` 拉分析文件(`failed_install`/`all_services`/`new_service`/`adapted_service`/`install_log`/`update_list`/`remove_log`/`new_service_test.log`)。
- ADR 0022 + Spec 0003 + CONTEXT.md 同步。

### 不做
- 不改 builder 的 env_set 动态创建逻辑(ADR 0018)。
- 不改 `run_case` 核心逻辑(只改 `execute_env_set` 的 pre_env 后注入)。
- 不改 per-case collect 逻辑(pkgserver 仍走 `_per_case_collect_log`)。
- 不重建 `failed_case` 文件(前端 case 列表替代)。
- 不改其他模块(docker/kernel/pkgcmd/pkgmanage)。
- 不引入两阶段触发(单次触发,pre_env 内完成发现)。

## Confirmed Decisions

1. pre_env 做装包+找服务+分类+check_new_service → 写 case_list 文件供平台读取。
2. 平台读 case_list → 查 MugenCase.env_type → 按本 env_set 的 env_type 过滤 → 动态建 case_run。
3. pre_env 生成的分析文件收集到平台作为 module_log artifact。
4. `failed_case` 不重建(前端 case 列表已展示结果)。
5. pre_env 必须 source mugen 的 `configure_repo.sh`(不能只用 UPDATE_REPO_SETUP 替代,`package_install` 的 `dnf list` grep 依赖 `test_update_repo` 变量)。

## ADR/Spec 冲突说明

| 文档 | 冲突点 |
|------|--------|
| ADR 0018 §2 | env_set 动态建基于 plan_cases 结果;pkgserver 新模型 case_runs 为空,env_set 需在 builder 阶段按 env_type="both" 预建 VM+physical |
| Spec 0003 §5.7 | pkgserver 模板定义 `case_filter=service_test_cases` 描述需更新 |

## Task Checklist

### Task 1: seed.py — 重写 PKGSERVER_PRE_ENV + PKGSERVER_POST_ENV

- [ ] PKGSERVER_PRE_ENV:
  - source mugen `configure_repo.sh` + `common_lib.sh`
  - `package_install()` → 生成 `update_list`、`install_log`
  - `search_all_services()` → 生成 `failed_install`、`all_services`
  - `select_services()` → 生成 `new_service`、`adapted_service`、`json_file`
  - `check_new_service()` → 输出重定向到 `new_service_test.log`
  - 从 `json_file` 提取 `suite/case` 对 → 写 `case_list` 文件(每行 `suite/case`)
  - 分析文件写到 `/opt/pkgserver-logs/`(不是工作目录)
- [ ] PKGSERVER_POST_ENV:
  - `clean_up_env()` → 生成 `remove_log`
  - 扫全部 `results/` 目录(不只 service-test)生成 `pkgserver-details.log`
  - 确保分析文件已在 `/opt/pkgserver-logs/`(pre_env 已写)
  - 拷 mugen `logs/` + `results/` 到 `/opt/pkgserver-logs/`

### Task 2: builder.py — case_filter 返回空

- [ ] `_resolve_cases`:`case_filter == "service_test_cases"` → 返回 `([], [], [])`
- [ ] env_set 仍按 env_type="both" 动态建 VM + physical(ADR 0018)

### Task 3: execution.py — pre_env 后动态建 case_run

- [ ] 新增 `_discover_and_create_case_runs(db, job, env_set, control)`:
  - SSH 读 `/opt/pkgserver-logs/case_list`
  - 解析 `suite/case` 对
  - 查 `MugenCase` 表,过滤 `env_type` 匹配本 env_set
  - 建 `TestCaseRun`(status=pending)挂到本 env_set
  - db.commit()
- [ ] `execute_env_set`:pre_env 后,若 `job.result_parser == "pkgserver"` 且 `env_set.case_runs` 为空 → 调 `_discover_and_create_case_runs`
- [ ] 刷新 `case_iter`(重新取 env_set.case_runs)

### Task 4: tasks.py — _self_collect_logs 拉分析文件

- [ ] 分析文件已在 `/opt/pkgserver-logs/`(pre_env/post_env 写的),`_self_collect_logs` 的 `ls -1F` 会自动发现它们作为 module_log artifact

### Task 5: 后端测试 (TDD)

- [ ] test: `_resolve_cases` 对 `case_filter == "service_test_cases"` 返回空
- [ ] test: `_discover_and_create_case_runs` 读 case_list → 按 env_type 过滤 → 建 case_run
- [ ] test: `_discover_and_create_case_runs` 无 case_list 文件时返回空(不报错)

## Verification

- `./scripts/check.sh backend` — ruff + pytest
- 手动验证(远程 dev):
  - pkgserver RunJob: pre_env 装包+分类+生成分析文件
  - case_list 正确生成,case_run 按 env_type 分配
  - 分析文件作为 module_log 在 RunJob 详情可见
  - post_env 清理+扫描多 suite results

## Progress

- [x] Task 1: seed.py — PKGSERVER_PRE_ENV + PKGSERVER_POST_ENV 重写
- [x] Task 2: builder.py — case_filter 返回空 + 空 cases 建空 env_sets (TDD)
- [x] Task 3: execution.py — discover_and_create_case_runs + execute_env_set 注入 (TDD)
- [x] Task 4: tasks.py — 无需改代码,_self_collect_logs 自动发现分析文件
- [x] Task 5: 后端测试 — 3 个新测试(builder/discover-found/discover-empty)

## Verification Results

- 后端 ruff: PASS
- 后端 pytest: 30 pipeline_execution + seed tests PASS (7 预存失败与我无关)
- 独立审计: 无阻塞项。3 个风险需 dev 验证:
  1. case_list awk 解析格式需对照真实 mugen json_file 输出验证
  2. package_install() 内部调 cfg_openEuler_repo 配 repo(源码已确认)
  3. clean_up_env 定义在 service-test common_lib.sh(已确认)
- 已加 0-case warning event (审计建议)
