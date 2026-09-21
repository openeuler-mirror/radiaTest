<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# VM 登记与删除以宿主机事实为准的对账

## 背景

当前 VM 登记与删除存在平台数据与宿主机实际状态漂移的窗口：

- 登记：`create-vm.sh` 成功回传后直接 `create_resource_from_vm_result` 入库，无创建后回读确认；脚本回传与宿主实际不符时（如 domain 秒挂）仍会登记。
- 删除：`destroy-vm.sh` 部分执行失败（已 destroy 未 undefine、已 undefine 磁盘残留）只记 `destroy_failed`，事件里没有宿主实际状态；脚本成功后的记账失败（如 `release_lease` 异常）导致宿主已删而 DB 仍显示在用。
- 恢复：`_recover_vm_destroys` 只清锁标 `destroy_interrupted`，不回读宿主，DB 与宿主的漂移要等人工重试才收敛。
- 排障实证（2026-09-07，kimariyb 实例 task_events）：批量删除时 `host_script_failed/host_connection_failed` 786 次对成功 344 次，报文为 `kex_exchange_identification: Connection reset by peer`——批量销毁瞬间并发 SSH 超过宿主 sshd 默认 `MaxStartups 10:30:100`，而 `process_vm_destroy` 对连接失败无重试，资源保留导致"批量总剩几台、第二次才删掉"。

Grill 已确认（用户逐项选择）：

1. **不变量**：DB 登记的每台 VM 宿主机上必须真实存在；删除流程收敛后宿主机不留该 VM 的 domain 和磁盘；宿主孤儿（创建中途崩溃）由创建流程自回滚保证，不建全局扫描。
2. **对账时机**：操作内 + 恢复路径回读宿主；不新增定时器、不在列表/详情页加探测（遵循 Lazy 惯例）。外部手段删宿主 VM 的情况平台不主动发现，已接受。
3. **动作边界**：回读确认宿主已无此 VM（domain+磁盘均无）才自动完成记账收敛（释放租约+软删+收敛事件）；宿主仍在则不自动重删，如实记录宿主实际状态并保持可重试；创建回读不存在则不登记、按失败处理。

## 范围

- 新增宿主探测脚本 `inspect-vm.sh`（走现有 `host_runner`/`host_scripts` SSH 推送模式）与契约 `VMHostInspectPayload`/`VMHostInspectResult`：回读 domain 存在性、电源态、系统盘/数据盘文件存在性。
- 创建（`process_vm_request`）：`create-vm.sh` 成功后、`create_resource_from_vm_result` 前回读确认；未确认存在则按失败处理（该宿主记 attempt 失败，不登记、不建租约）。
- 删除（`process_vm_destroy`）：`host_connection_failed` 做有限次退避重试（带 jitter，瞬时连接抖动自愈，治批量并发 SSH 超限的实测根因）；重试耗尽后的失败路径回读宿主——确认已消失则自动落账收敛；仍存在/回读失败则维持现行为，并把宿主实际状态写进 `destroy_failed` 事件。
- 恢复（`_recover_vm_destroys`）：清锁前先回读——确认已消失则按无 actor 自动释放租约并软删资源、记收敛事件；仍存在/回读失败维持现状（清锁 + `destroy_interrupted`）。
- 文档：ADR 0041（宿主事实对账取舍，含对"恢复不删 VM 本体"的澄清——恢复仍不删，只是发现已消失才落账）；Spec 0001 VM 申请/释放章节同步验收语义。

## 明确不做

- 不做定时对账任务、不做列表/详情页读时探测。
- 不自动重试删除脚本（重试仍由人工再释放或过期懒释放触发，脚本 dominfo 幂等续删）。
- 不处理平台外手工删除宿主 VM 的主动发现。
- 不改 create-vm.sh / destroy-vm.sh 现有行为（inspect 为新增只读探测）。

## 实施步骤

1. TDD：`VMHostInspectPayload/Result` 契约与 `inspect-vm.sh`（shell 语法检查 + 契约字段）。
2. TDD：销毁 `host_connection_failed` 退避重试（重试后成功 → `destroy_succeeded`；耗尽 → 失败路径）。
3. TDD：删除失败路径回读：已消失 → 租约释放 + 软删 + `destroy_succeeded`（收敛语义）；仍在 → `destroy_failed` 事件含宿主实际状态。
4. TDD：恢复路径回读：已消失 → 自动落账；仍在 → 现状 `destroy_interrupted`。
5. TDD：创建登记前回读（mock `run_host_script`）：回读不存在 → attempt 失败、无资源、无租约。
6. ADR 0041 + Spec 0001 同步。

## 验证标准

- 新增行为各有先失败再通过的测试；`test_vms.py` 既有销毁/恢复用例保持绿。
- 定向 pytest + `./scripts/check.sh` 通过。
- ADR/Spec/计划齐备。
