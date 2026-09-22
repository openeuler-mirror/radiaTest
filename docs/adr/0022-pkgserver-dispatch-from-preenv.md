<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0022：pkgserver 执行逻辑重做 — repodata 发现 + builder 调度

日期: 2026-07-28

## 状态

已采纳。

## 背景

pkgserver 模块（`oe_test_service_restart`）当前以 meta-case 模式执行：平台跑一个元用例 `mugen.sh -f service-test -r oe_test_service_restart -x`，该用例内部 `test_adapted_service()` 循环调用其他 mugen 用例（case调case）。导致：

1. **无法按 env_type 分配**：子调用全跑在元用例所在的一台机器上，需要物理机的用例无法分配到物理机。
2. **分析文件未收集**：`failed_install`、`all_services`、`new_service` 等文件生成在用例工作目录，平台只拷 `logs/` 和 `results/`，一个都没收集。
3. **case_filter 无意义**：`service_test_cases` 筛选器选出的 service-test 套件只有一个元用例，等于没筛选。

## 决策

### 1. builder 解析 repodata filelists 发现阶段（跟 pkgcmd 对称）

在 builder 的 `_resolve_cases` 中，`case_filter == "service_test_cases"` 改为：
- 调 `fetch_service_packages(repo_base_url, version, arch)` 解析 update 仓库 binary repo 的 `filelists.xml`，找 `/lib/systemd/system/*.service|target|socket` 文件。
- 提取服务名和类型，构造 mugen 用例名 `oe_test_<type>_<name>`。
- 查 `MugenCase` 表匹配，返回带 `env_type` 的用例列表。
- builder 按 `env_type="both"` 拆 VM/physical env_set，预建 case_run。

不采用：在 pre_env 装包后 `rpm -ql` 发现服务——需要机器运行时才知道，导致动态建 case_run，时序与 pkgcmd 不对称。

### 2. pre_env 只负责装包 + new_service 测试

`PKGSERVER_PRE_ENV`：
- source mugen `configure_repo.sh` + `common_lib.sh`（service-test + cli-test）。
- `package_install()` 装包 → 生成 `update_list`、`install_log`。
- `search_all_services()` 找服务 → 生成 `failed_install`、`all_services`。
- `check_new_service()` 测无专用用例的服务 → 输出到 `new_service_test.log`。
- 分析文件写到 `/opt/pkgserver-logs/`。

不采用 `select_services()`——builder 已用 repodata 做了匹配。

### 3. post_env 做清理 + 扫多 suite

`PKGSERVER_POST_ENV`：
- `clean_up_env()` 停服务 + 卸包 → 生成 `remove_log`。
- 重装 openssh-server + 重启 sshd（`clean_up_env` 卸包含 openssh-server，恢复后 `_self_collect_logs` 才能 SSH 拉日志）。
- 扫全部 `results/` 目录（不只 service-test）生成 `pkgserver-details.log`。
- 拷 mugen `logs/` + `results/`。

### 4. 分析文件收集

`_self_collect_logs` 的 `ls -1F /opt/pkgserver-logs/` 自动发现分析文件，作为 `module_log` artifact 拉回平台。

## 影响

- `repodata.py`：新增 `fetch_service_packages()` + `_filelists_location()` + `_parse_filelists_services()`。
- `builder.py`：`case_filter == "service_test_cases"` 改为 repodata 发现 + MugenCase 匹配。env_set 创建回归正常路径（不再需要空 env_set 特殊处理）。
- `seed.py`：`PKGSERVER_PRE_ENV` 去掉 `select_services` 和 `case_list` 生成；`PKGSERVER_POST_ENV` 扫多 suite。
- `execution.py`：删除 `discover_and_create_case_runs` 和注入逻辑（不再需要）。
- Spec 0003 + CONTEXT.md 同步。
