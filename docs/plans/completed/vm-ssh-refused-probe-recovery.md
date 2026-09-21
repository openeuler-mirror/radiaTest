<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# VM SSH 服务失效的用例间探针恢复

日期：2026-09-11（经方案对齐，用户确认推荐档）

## 背景

job 10235（kimariyb，crypto-policies 套件）实锤：`oe_test_crypto_policies_switch`
在 1 秒内连续切换 7 次加密策略，每次 `update-crypto-policies` 经
reload-cmds.sh 执行 `systemctl try-restart sshd`，触发 systemd 启动速率限制
`start-limit-hit`，sshd 停止监听。已建立的会话不受影响 → 用例正常跑完判
passed；下一个连接（0.1 秒后 post_env）即 `Connection refused`。

ADR 0046（当日已部署 kimariyb）只覆盖"套件中间"场景：victim 用例连击 3 次
→ 熔断点硬复位。缺口：① 每次事故损失最多 3 个 victim 用例（探活失败即标
error）；② 套件末尾用例杀掉 sshd 时（本例）用例循环已结束，post_env 直接
失败 → 全 passed 的 job 被误标 error。

带外核查事实：VM 域 XML 未配置 qemu-guest-agent 通道，镜像未装
qemu-guest-agent（`rpm -q` not installed，`/dev/virtio-ports/` 不存在）——
"不重启 VM、只重启 sshd"当前无通道可走。

## 范围（用户确认的推荐方案）

- **用例间探针**：`execute_env_set` 用例循环头部 + post_env 前，对控制机做
  一次 SSH 探活；**只认 `Connection refused`**（sshd 挂了但 OS/网络活着的
  确定签名）且有宿主通道且恢复预算未用时，先 `try_vm_recovery` 硬复位再
  继续 → victim 用例拿回真实结果，job 按真实结果收敛。
- **恢复预算共享**：探针与熔断点共用 ADR 0046 的"每环境集限 1 次"预算
  （连环杀手场景无实证，多次重启只会烧任务预算）。
- **try_vm_recovery 加 trigger 参数**（breaker/probe），`vm_recovery_started`
  事件文案区分触发来源。
- **`_vm_host_channel` 转公开 `vm_host_channel`**：探针门控需要跨模块调用。

## 明确不做

- qemu-guest-agent 通道与镜像改造（秒级免重启恢复）——backlog，依赖装机
  工序与镜像变更，另行立项。
- 超时/失联触发恢复：机器状态未知，交给既有挂死链路（观察模式/熔断），
  误恢复代价是白重启一次。
- 增加恢复预算次数、新增配置参数、前端改动、新凭据/表字段。

## 实施步骤

1. RED：`ssh_connect_refused` 单元测试（refused=True；超时/失联/健康/
   进程超时=False）+ `execute_env_set` 探针测试（探针恢复零 victim、无通道
   不探、预算共享、post_env 前恢复/失败维持现状）+ trigger 文案测试。
2. GREEN：`mugen_runner.ssh_connect_refused`（复用 HEARTBEAT_TIMEOUT，
   分类逻辑与 `_HeartbeatStats` 的"拒绝"签名一致）；`try_vm_recovery`
   trigger 参数；`execution.py` 循环头部与 finally 接线。
3. ADR 0046 修订段 + Spec 0003 §4.6 同步；`./scripts/check.sh` 全绿。

## 验证标准

- 探针恢复场景：全部用例真实结果（无 victim error），恢复调用恰 1 次。
- job 10235 场景（末尾用例杀 sshd）：post_env 前恢复 → post_env 正常执行
  → job 不误标 error。
- 无通道/超时/预算用尽：行为与 ADR 0046 既有语义完全一致（既有测试不动
  仍绿）。
