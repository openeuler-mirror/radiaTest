<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: update 流水线 kernel 模块(物理机重装+跑 mugen + 按 result_parser 派发展示)

## 状态（2026-09-04 归档）

T1–T4 全落地并部署（`399cc34 / 40980b9 / bfa57b8` → main），部署后 kernel 模板 env_type/result_parser/mugen_exec_command 已核验。
`a788699` 之后重跑 `./scripts/check.sh` 全通过（backend 495 passed / 1 skipped，frontend build 通过）。
用户在 kimariyb 环境反馈"C 组 kernel update 流水线已测过很多，端到端无异常"作为运行验证记录；MR 审查以
`a788699` merge commit 为代理。

## 目标

让 update 测试流水线的 **kernel 模块**端到端可用：kernel 只在物理机跑 → RunJob 内自动挑触发者已占用的物理机 → 用 PXE 重装能力重装成 pipeline 的 OS/arch → 等 SSH 通 → 跑 mugen。同时让详情 API 返回 `result_parser`，并通过当前标准日志区展示 kernel 的 LTP artifact。

## 范围

- **T1 模型+迁移**：`TestModuleTemplate` 加 `env_type`（vm/physical/both）取代 `env_type_split` bool；kernel=physical。update 策略按 env_type 产生 RunJob：`both` 为一个 RunJob，并在其 TestJob 内建 VM/physical EnvSet；physical/vm 各建一个对应类型 RunJob。
- **T2 physical EnvSet 重装**：所有物理 EnvSet（kernel 的 physical RunJob，以及 pkgcmd/pkgserver 的 `both` RunJob 内 physical EnvSet）的环境建立改为——找触发者已占用的物理机（arch 匹配，多台取第一）→ 按 pipeline version+arch 找 `physical_install_image` → 调 PXE 重装（把 `run_pxe_install_task` 编排抽成可同步调用函数，RunJob 内联调，等 SSH）→ 再跑 mugen。
- **T3 kernel result_parser**：kernel 使用 `ltp` result_parser；`post_env_script` 上传 mugen 原始日志 + `/opt/ltp/ltp.log` + `/opt/ltp/results` 目录为 artifact；seed 设 kernel.result_parser=ltp。
- **T4 详情页结果分派与日志展示**：`run-job-detail.vue` 接收 `detail.result_parser`；kernel 的 LTP artifact 通过当前标准日志区展示，具体页面布局以 Spec 0003 为准。

## 非目标

- pkgcmd/pkgserver/docker 的专属结果展示（本轮只立派发机制 + kernel，其余沿用/兜底）。
- 其它模块（docker/pkgmanage/pkgcmd/pkgserver）的 env 行为不变。
- 30 分钟 SSH 超时调整（另议）。
- ltp 结果的详细解析（本轮只链接展示）。

## 确认决策

- **Q1 env 建模**：加 `env_type`（vm/physical/both）字段取代 bool；kernel=physical，docker/pkgmanage=vm，pkgcmd/pkgserver=both。
- **Q3 kernel 流程**：RunJob 内全自动（挑机→PXE 重装→等 SSH→跑 mugen）。
- **Q4 选机**：触发者已占用的物理机（arch 匹配，多台取第一）——不找 idle。
- **Q2 结果展示**：按 `result_parser` 派发，每模块封装自己的结果展示，互不影响；kernel 需补 result_parser + 展示。
- **Q5 范围**：只做 kernel + 派发机制。
- **kernel 展示内容**：mugen 原始日志 + `/opt/ltp/ltp.log` + `/opt/ltp/results` 目录；本轮只做**链接展示**，详细解析后续。

## 任务

- [x] 文档：ADR-0015（env_type + kernel 物理流 + result_parser 派发）+ spec 0003 + CONTEXT
- [x] T1 模型+迁移+update 策略+seed/schema
- [x] T2 kernel 物理环境（占用机+PXE 重装同步调用+等 SSH）
- [x] T3 kernel `ltp` result_parser + artifact 上传（mugen 日志/ltp.log/ltp/results）
- [x] T4 详情 API result_parser + kernel artifact 日志展示
- [ ] 验证：./scripts/check.sh all + dev 触发 update 流水线选 kernel → 占用物理机重装→mugen→结果页按 kernel 展示链接

## 进度

- [x] 文档：ADR-0015 + spec 0003 + CONTEXT
- [x] T1 模型+迁移+update 策略+seed/schema/测试/前端管理表单（已部署 399cc34）
- [x] T2 physical RunJob 重装（run_pxe_install 抽同步函数+create_env_node_physical 用占用机+重装,已部署 40980b9）
- [x] T3 kernel `ltp` result_parser + artifact 上传（KERNEL_POST_ENV 加 ltp_results 目录；result_parser=ltp 已有，已部署 bfa57b8 + re-seed）
- [x] T4 详情 API result_parser + kernel artifact 日志展示（后端 detail 响应加 result_parser；早期独立链接块已按当前详情布局收敛，已部署 bfa57b8）
- [x] 部署 T3+T4 + 重跑 seed-pipeline-templates（kernel 模板 has_ltp_results=t,已验证）
