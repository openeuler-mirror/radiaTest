<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 修复 create-vm.sh stale libvirt volume 导致 virt-install domain not found

## 状态

complete。Audit PASS-WITH-NITS（nit 已修：cleanup 测试加强验 2 次 vol-delete + pool 名 + 卷名）；3 测试绿 + ruff + bash-n 干净；91 清 7 孤儿卷；ADR 0005 不动（vol-delete 是更完整清理，不冲突）；部署待 Reconcile 后。

## 目标

修复部署后仍报 `virt-install --print-xml` → `Domain not found: no domain with matching uuid
'...' (SP4 domain)` 的问题。报错命令已无 `--check path_in_use`（确认移除生效），但仍
domain not found。

根因：virt-install 生成 XML 时刷新 `instances` storage pool，遍历池里所有磁盘卷。
**之前失败/删除的 VM 留下"孤儿卷"**——libvirt 卷记录（`virsh vol-list`）还在，
但对应 domain 已 undefine，卷记录仍引用已删 domain。virt-install 刷新时查到 stale
引用 → `domain not found`。`create-vm.sh` cleanup 只 `rm` 磁盘文件，不 `virsh
vol-delete` 清 libvirt 卷记录，stale 卷累积。flock 串行化只解决并发抢池，不解决
stale 引用。

实锤：91 `virsh vol-list instances` 42 行，含大量历史失败 VM 的孤儿卷 +
`.kronos-create.lock`（锁文件放 instances 目录被 pool 识别为卷）。

## 范围

- **A. cleanup 加 `virsh vol-delete`**：`create-vm.sh` cleanup 函数在 rm 磁盘文件
  前，先 `virsh vol-delete --pool instances <vol-name>` 清 libvirt 卷记录（系统盘 +
  数据盘），`|| true` 不阻塞 cleanup。防止未来 stale 累积。
- **B. 锁文件移出 instances 目录**：`.kronos-create.lock` 从 `$INSTANCE_DIR/`
  移到 `$BASE_DIR/.kronos-create.lock`（kronos 根目录，不在 instances pool 目录，
  避免被 libvirt 识别为 volume）。
- **C. 现有 stale volume 一次性手动清理**：登 91 `virsh vol-delete --pool
  instances` 无 domain 引用的孤儿卷（含 `.kronos-create.lock`）。一次性运维，不
  入脚本。

## 非目标

- 报错2（virtlogd busy）观察，不修（根因不确证，可能随报错1 修复减少）。
- 报错3（DHCP 获取不到）外部 DHCP 服务器，不修。
- 不改 `vm_uuid`（uuid4 正确）。
- 不加 stale volume 自动清理逻辑（一次性手动 + cleanup vol-delete 防未来即可，
  AGENTS.md 简单优先）。
- 不改 spec/ADR 0005（cleanup 细节是实现，不改 VM 创建不变式）。

## 确认决策（grilling 3 题）

1. **修复范围 = 报错1+2 代码修，报错3 外部**：报错1 stale volume 代码修，报错2
   virtlogd 根因不确证先观察，报错3 DHCP 外部。
2. **报错2 = 先修报错1 观察**：virtlogd 根因不确证（journal 无记录/配置空/无 D
   进程），先修报错1（stale volume），报错2 随报错1 修复观察；如仍复现再串行 start。
3. **stale 清理 = 手动清现有 + cleanup 防未来**：现有 42 个孤儿卷一次性手动
   `virsh vol-delete`；create-vm.sh cleanup 加 vol-delete 防未来累积；不加自动清理逻辑。

## 任务

- [x] T0 `create-vm.sh` cleanup 加 `virsh vol-delete`（系统盘+数据盘卷，`|| true`）+
  锁文件移到 `$BASE_DIR/.kronos-create.lock`。TDD 测试验证 cleanup 调 vol-delete +
  锁文件不在 instances 目录。
- [x] T1 手动清 91 现有 stale volume（`virsh vol-delete` 孤儿卷 + 旧 `.kronos-create.lock`）。
- [x] T2 Audit：独立只读审查（cleanup vol-delete 正确性、锁文件位置、测试有效）。
- [ ] T3 部署 dev + 端到端（批量创建 VM 不再 domain not found）。

## 进度

- T0 完成：cleanup 加 `virsh vol-delete`（系统盘+数据盘卷，`|| true`）+ 锁文件移 `$BASE_DIR/.kronos-create.lock`；TDD 3 测试 RED→GREEN。
- T1 完成：91 清 7 孤儿卷（含旧 `.kronos-create.lock`），剩 33 有 domain 引用。
- Audit 完成：PASS-WITH-NITS，nit（测试断言加强验 2 次 vol-delete + pool 名 + 卷名）已修，复跑 3 测试绿 + ruff + bash-n 干净。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh scripts`（bash -n + shellcheck）。
- TDD：扩展 `test_create_vm_concurrent.py` 或新测试，验证 cleanup 调
  `virsh vol-delete`（mock virsh 记录调用）+ 锁文件路径不在 `$INSTANCE_DIR`。
- 验收场景：
  1. `./scripts/check.sh scripts` 干净 + 测试绿。
  2. 91 `virsh vol-list instances` 无孤儿卷 + 无 `.kronos-create.lock`。
  3. 端到端：批量创建多 VM，virt-install 不再 `domain not found`。
