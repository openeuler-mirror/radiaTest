<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 硬复位前强制刷盘：收敛页缓存丢失面

日期：2026-09-11（根因定位 + 方案 A 经用户确认）

## 背景

job 10238/10237 实锤 ADR 0046 恢复机制的设计缺陷：`virsh destroy` 等价拔电，
复位前 ~30 秒内未落盘的页缓存写回全部丢失（ext4 延迟分配）。10238 现场：
mugen 配置（`conf/env.json`）与两个已通过用例的日志/results 写入仅 0.5~7
秒后即被 destroy → 全部 0 字节；重启后每次 `mugen.sh` 在 `read_conf.py`
解析空 JSON 崩溃 → **后续用例全部秒败**。10237（keep_env 复用 10236 复位
过的 VM）同因秒败——损坏的环境会投毒后续任务。

## 范围（方案 A：关键边界强制 sync）

- **环境就绪后**（case 循环前，pre_env/部署/配置完成后）：对 control 执行
  一次 `sync`——保住 env.json/框架状态，治"后续用例全失败"与 keep_env
  复用投毒。
- **每个用例正常返回后**：best-effort `sync`——保住已完成用例的日志/
  results，治"日志 0KB"。
- 两处均**门控在宿主通道存在**（`vm_host_channel` 非 None）：只有该 VM
  可能被硬复位，物理机/无通道 VM 不付同步开销。
- `sync_vm_disks` 契约：**绝不抛异常**（SSH 已死是杀手用例的预期场景），
  失败静默记日志，下轮探针恢复接管。
- 杀手用例自身的日志无法保住（sshd 死后无从 sync），由既有 console 取证
  覆盖——接受的残留丢失面。

## 明确不做

- `virsh reboot` 优雅重启优先 + destroy 兜底（方案 B）——backlog，恢复
  时长翻倍，待 A 上线后按实际丢失面评估。
- 恢复后重跑 mugen prepare 的健康自检（方案 C）——平台耦合 mugen 内部
  结构，拒绝。
- peer 节点 sync（reset 只针对 control；日志/results 也只在 control）。
- 新增配置参数（超时用代码常量）。

## 实施步骤

1. RED：`sync_vm_disks` 单元测试（命令内容/超时/吞异常契约）+
   execution 测试（环境就绪 1 次 + 每用例完成 1 次、异常用例不触发、无
   通道不 sync）。
2. GREEN：`mugen_runner.sync_vm_disks` + `execution.py` 两处接线。
3. ADR 0046 修订二 + Spec 0003 §4.6 同步；`./scripts/check.sh` 全绿。

## 验证标准

- 混合结果（通过/异常）下 sync 恰好发生在环境就绪 + 每个正常返回的用例
  之后；异常用例不触发。
- 无宿主通道时零 sync 调用（既有测试全部不受影响）。
- `sync_vm_disks` 在 SSH 失败时不向上抛异常。
