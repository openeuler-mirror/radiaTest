<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0041：VM 登记与删除以宿主机事实为准的对账

日期: 2026-09-08

## 状态

已采纳（Grill 确认，逐项决策见 `docs/plans/active/vm-host-fact-reconciliation.md`）。

## 背景

平台数据与宿主机实际状态存在漂移窗口，登记与删除都可能在 DB 与宿主事实不一致的情况下收尾：

1. 登记：`create-vm.sh` 回传成功后直接建资源与租约，无回读确认。脚本回传与宿主实际不符（如 domain 创建后秒挂）时，平台登记一个宿主机上不存在的 VM。
2. 删除：`destroy-vm.sh` 按步骤顺序执行（virsh destroy → undefine → 删盘），部分执行失败（已断电未 undefine、已 undefine 磁盘残留）只记 `destroy_failed`，事件不含宿主实际状态；脚本成功后的记账失败（如租约释放异常）导致宿主已删而 DB 仍显示在用。
3. 恢复：`_recover_vm_destroys` 只清锁标 `destroy_interrupted`，不回读宿主，漂移要等人工重试才收敛。
4. 排障实证（2026-09-07，kimariyb 实例）：批量销毁瞬间对同一宿主并发多条 SSH，超出 sshd 默认 `MaxStartups 10:30:100` 的连接在 kex 阶段被重置（`kex_exchange_identification: Connection reset by peer`），`host_connection_failed` 786 次对成功 344 次；`process_vm_destroy` 对连接失败无重试，资源保留，表现为"批量删除总剩几台、第二次才删掉"。

## 决策

### 1. 不变量：存在性 + 删除收敛

- DB 登记的每台 VM 在其宿主机上必须真实存在。
- 删除流程结束（成功或失败收敛）后，宿主机不留该 VM 的 libvirt domain 与磁盘文件。
- 宿主孤儿（创建中途崩溃导致宿主机有 VM 而 DB 无登记）由创建流程自回滚保证，不建全局扫描。

### 2. 对账时机：操作内 + 恢复路径

- 新增只读宿主脚本 `inspect-vm.sh`（契约 `VMHostInspectPayload`/`VMHostInspectResult`）：回读 domain 存在性、电源态、系统盘/数据盘文件存在性。
- 创建：`create-vm.sh` 成功后、建资源前回读确认；未确认存在则本宿主 attempt 失败并换下一宿主。
- 删除：脚本失败后回读宿主，按事实决定收敛或如实标记失败。
- 恢复：清锁前回读宿主，按事实决定落账收敛或维持清锁。
- 不新增定时器、不在列表/详情页加探测（Lazy 惯例）；外部手段删除宿主 VM 的情况平台不主动发现。

### 3. 动作边界：确认消失才落账

- 删除/恢复回读确认宿主已无此 VM（domain 与磁盘均不存在）→ 自动完成记账收敛（自动释放租约(AUTO_RELEASE)、软删资源、`destroy_succeeded` 事件注明收敛来源）。
- 回读发现 VM 仍在 → 不自动重删（避免不可控循环），如实记录宿主实际状态（电源态/残留盘）进 `destroy_failed` 事件，保持资源与租约可重试，由人工再释放或过期懒释放收敛（`destroy-vm.sh` 按 `virsh dominfo` 幂等续删）。
- 回读失败 → 视为未确认，按失败处理。
- 创建回读未确认存在 → 不登记、不建租约；回读失败时先尽力回滚清理（幂等），避免宿主孤儿。
- 销毁对 `host_connection_failed` 做有限次指数退避+抖动重试（瞬时故障自愈，治批量并发 SSH 超限的实测根因）；语义性失败不重试；重试事件追加记录保留原始失败事实。

## 取舍 / 不采用

- **不采用定时对账任务**：需要后台 worker 与全量扫描，违背项目 Lazy Release 惯例；漂移集中在操作链路上产生，在操作与恢复路径上回读即可闭环。
- **不采用详情页读时探测**：每次打开详情一次 SSH，成本高且只能覆盖被查看的 VM。
- **不采用自动重删**：宿主仍在时自动重试删除脚本有不可控循环风险；重试仍由人工或懒释放触发，脚本幂等可安全续删。
- **恢复仍不删 VM 本体（对既有取舍的澄清）**：恢复回读只"发现已消失才落账"，从不主动执行删除；该语义是对恢复逻辑的增强而非推翻。
- **宿主孤儿不做全局扫描**：孤儿只在创建流程中途产生，由创建回读失败时的尽力回滚 + 既有 Worker 恢复覆盖。

## 影响

- 后端：`vms/host_contract.py`（inspect 契约）、`vms/host_scripts/inspect-vm.sh`（新增）、`vms/service.py`（销毁重试与回读收敛、创建登记确认、`finalize_destroy_by_host_fact` 公开收敛入口）、`tasks/recovery.py`（销毁恢复回读）。
- 前端无改动：收敛与失败事实通过既有任务事件时间线展示。
- `docs/spec/0001-resource-management.md` VM 申请/释放验收语义同步本 ADR。
