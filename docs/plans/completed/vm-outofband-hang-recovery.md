<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# VM 带外判活与宿主机硬复位恢复（ADR 0046）

## 背景与动机

2026-09-05 至 09-11 期间 prod/dev 共 60+ 个 VM job 因 SSH 断连中断（prod 32 + dev 32），三类根因：

- initrd 家族用例（`oe_test_service_initrd-cleanup` 等）伪造 `/etc/initrd-release` isolate 到 switch-root，sshd 被停——已由危险用例过滤（ADR 0043）拦截，但 prod 未部署。
- `oe_test_ebtables`/`oe_test_ebtables_002`/`oe_test_firewalld_server` 在 DevStation rc4 镜像上失败并残留防火墙规则（DROP），SSH 全部 `Connection timed out`，每个 job 损失 232 个未执行用例（约 65% 覆盖率）。
- `oe_test_socket_sssd-nss` 停 sssd-nss.socket 造成 NSS 阻塞，新 SSH 认证挂起 3-5 分钟后自愈；当前 VM 无确认门，用例被误标 `vm_hang`（job 仍继续，但该用例真实结果丢失）。

结构缺口：VM 判死走"阈值+复核"无带外确认（ADR 0044 仅物理机有 BMC 电源确认门），且熔断后不利用宿主机通道做恢复。平台已有宿主机 SSH 通道（`vm_host_ssh_key_path`，console 取证在用），`virsh domstate` 即 VM 的"机箱电源状态"。

## 范围

- 判活映射（用户确认）：心跳判挂死后查宿主机 `virsh domstate` 三态——
  - `running`/`paused`/`in shutdown` → VM 活着，进观察模式等 SSH 自愈（自愈后用例拿回真实结果）；
  - `shut off`/`crashed`/`dying` → 锚定 10 分钟宽限（复用 `WATCH_POWER_OFF_DEADLINE_SECONDS`，覆盖 `on_crash=restart` 自动拉起），到点判死；
  - 宿主机查询失败 → 回退现状（阈值+复核判死，无确认门）。
- 观察上限复用 `WATCH_TIMEOUT_SECONDS=1800`，不新增参数。
- 恢复动作：观察超时（domstate 活着但 SSH 未恢复）→ 先抓 console 取证（复用 `capture_vm_console_output`）→ `virsh destroy`+`virsh start` 硬复位 → 等就绪复用 `SSH_READY_TIMEOUT_SECONDS=900`；每 env_set 限 1 次，第二次判死走现有熔断。
- 结果归属：观察期内自愈 → 用例真实结果不标错；恢复成功 → 肇事用例标 `error(vm_hang)`（不新增 error_code），事件消息注明宿主机硬复位，后续用例继续、连击计数清零；恢复失败 → 维持现状判死熔断。
- 事件留痕：新增 phase `vm_recovery_started`/`vm_recovered`/`vm_recovery_failed`；console 取证存 `console_diagnostic` 产物。
- 适用范围：有宿主通道（`host_resource_id` 存在、宿主 `primary_ip` 可用、`vm_host_ssh_key_path` 已配置）的 VM，动态/静态一视同仁；无通道回退现状。
- 文档：新建 ADR 0046；ADR 0044 的 VM 路径段落加指向；Spec 0003 §4.6 同步。

## 明确不做

- 不改熔断批量标记语义（维持 `error`，不引入批量 `not_executed`）。
- 不扩危险用例名单（ebtables/firewalld 是合法用例，"失败即致命"类不可穷举）。
- 不新增宿主凭据/表字段/轮询任务；复用 console 取证同一 SSH key 通道。
- 不做 `virsh reboot` 优雅重启（防火墙残留/isolate 僵尸系统对 ACPI 可能无响应）。
- prod 部署不在本计划内（部署需另行授权，可与 ADR 0043 过滤同批）。

## 实施步骤

1. 测试先行（先失败）：
   - `test_console_capture.py`：domstate 三态解析（活着/死/查询失败/未知输出）；硬复位原语（destroy+start 顺序、失败返回）。
   - `test_hang_detector.py`/门测试：VM 门 confirm 三态映射；shut off 宽限锚定；查询失败回退。
   - `test_pipeline_execution.py`：观察超时触发恢复流程（事件留痕、限 1 次、恢复成功继续、失败判死）；自愈用例拿回真实结果；无宿主通道 VM 维持现状。
2. 最小实现：`console_capture.py` 增 domstate 探测与硬复位原语；`mugen_runner.py` 增 `_VmHangGate`（对称 `_BmcHangGate`）并接线 `_build_bmc_hang_gate` 位置；恢复流程在 `run_case` 挂死路径接入。
3. 文档：ADR 0046、ADR 0044 指向行、Spec 0003 §4.6；完成后本计划移入 `completed/`。

## 验证标准

- 新增/修改关键行为测试先失败后通过；`./scripts/check.sh` 通过。
- sssd 场景回放锁定：domstate=running + 心跳失败 → 观察模式 → SSH 恢复 → 用例真实结果不标错。
- ebtables 场景回放锁定：domstate=running + 观察超时 → destroy+start → SSH 回来 → 肇事用例 error(vm_hang) 注明硬复位、后续用例继续、计数清零。
- 恢复失败与无通道场景维持现状判死；二次触发不再恢复。
- 审查通过后准备 merge commit message，经授权合入 main。
