<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0068：virt-install 域枚举竞争定向重试

日期：2026-10-13

## 状态

已采纳。

## 背景

`virt-install --print-xml` 生成 XML 时会枚举宿主上的 libvirt domain。如果某个 domain
在枚举期间被并发删除，命令可能输出 `no domain with matching` 并失败，导致 VM 创建失败。

## 决策

- 在 `create-vm.sh` 现有宿主创建锁内，对 `--print-xml` 的失败输出匹配
  `no domain with matching` 时进行定向重试。匹配基于 stderr 文本，不证明所有命中均由并发删除引起。
- 最多尝试三次，相邻重试间隔两秒；其他错误不重试。重试期间保留失败命令和 stderr 事件，
  并追加 `virt_install_retry` 事件。最后一次失败沿用原终态错误码和文案。
- 此决策不修改平台重试策略、虚拟机清理流程或 `destroy-vm.sh`。

## 不采用的方案

- 创建与销毁共用宿主锁会增加等待，且不能覆盖外部的 domain 删除。
- 只在平台层重试需要重新创建资源，范围和恢复成本更大。
- 关闭部分检查不能完全消除 domain 枚举，也可能削弱冲突检查。

## 影响

命中目标文本时，最多额外等待四秒且保持现有创建锁；其他错误仍按原方式报告。
测试以命令桩覆盖重试和失败事件；真实宿主行为需在 Linux 环境单独验证。
