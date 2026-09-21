<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 修复 create-vm.sh 并发 virt-install 导致 VM 创建失败

## 状态

complete。Audit PASS-WITH-NITS（stub stray-file minor 已修）；ruff All checks passed + bash -n 干净 + pytest 绿；ADR 0005 不动（串行化是实现细节）；端到端待用户部署后验证。

## 目标

修复批量启动流水线时，同一台 VM 宿主机上多个 VM 并发执行 `virt-install --print-xml`
导致的间歇性 `vm_create_failed`：

- **报错2**「Could not define storage pool: pool 'instances' already exists with uuid
  c8627bc7...」：多个 `virt-install --print-xml` 并发 ensure `instances` storage
  pool，竞态误 define 已存在的 pool → 冲突。91 上单独跑 `virt-install --print-xml`
  不冲突（报 size 缺失而非 pool 冲突）——证明根因是并发。
- **报错1**「Domain not found: no domain with matching uuid '0b623e13...' (SP4 domain)」：
  `virt-install --check path_in_use=1` 遍历 domain 查磁盘路径占用，引用了刚创建失败
  被删的 SP4 domain（libvirt 缓存残留）→ not found。

实锤：2026-08-05 10:00:22 / 10:03:38，91 宿主上 24.03-SP1/SP3/SP4 aarch64 VM 并发
创建。`create-vm.sh:375` 的 `flock` **只保护缓存镜像下载**（line 374-381），
`virt-install`（line 470）在锁外，无串行化。`vm_uuid = str(uuid4())`（service.py:652）
唯一，非 UUID 冲突。

## 范围

- **A. flock 串行化 virt-install + VNC 补丁 + virsh define**：新增宿主级锁文件
  `/var/lib/libvirt/images/kronos/instances/.kronos-create.lock`，用 `flock -x` 子
  shell 包裹 `virt-install --print-xml`（line 469-475）+ `enable_vnc_websocket_xml`
  （line 477-483）+ `virsh define`（line 485-488）三步。qemu-img 建盘、镜像下载
  （已有锁）不锁。virt-install --print-xml 只几秒，串行对批量影响小。
- **B. 移除 `--check path_in_use=1`**（create-vm.sh:446）：避免 virt-install 遍历
  domain 查磁盘占用（报错1 stale domain 源头）。VM name 含 uuid4、磁盘路径唯一
  不会撞；`virt-install` 前已 `qemu-img create` 建盘，路径被占会先报错。该检查在
  本场景多余且有害。

## 非目标

- 不改 `vm_uuid` 生成（`uuid4()` 正确，非冲突）。
- 不改 libvirt storage pool 配置（instances pool 配置正确，冲突是并发 ensure 竞态）。
- 不改 `vms/service.py` Python 侧（VM 创建编排不变）。
- 不加 VM 创建全局串行（只锁宿主内 virt-install+define，跨宿主仍并行）。
- 不改 spec 0001/ADR 0005（VM 创建不变式不变，只改脚本并发安全）。

## 确认决策（grilling 2 题）

1. **修复方向 = 加锁排队 + 去掉检查**：flock 串行化 virt-install 消除并发 pool
   抢占（报错2）；移除 `--check path_in_use=1` 避免 stale domain lookup（报错1）。
2. **锁范围 = 宿主级锁，锁 virt-install+vnc+define**：锁文件
   `/var/lib/libvirt/images/kronos/instances/.kronos-create.lock`，覆盖三步 libvirt
   交互；建盘/镜像下载不锁。

## 任务

- [x] T0 `create-vm.sh` 加 flock 串行化 virt-install+vnc+define 段 + 移除
  `--check path_in_use=1`。验证 `./scripts/check.sh scripts`（bash -n + shellcheck）干净。
- [x] T1 Audit：独立只读审查（锁正确性、子 shell 释放、事件顺序、--check 移除副作用）。
- [ ] T2 端到端（用户部署后）：批量创建 VM 不再 pool conflict / domain not found。

## 进度

- T0 完成：`create-vm.sh` 加 flock 串行化 virt-install+vnc+define 段（锁文件
  `$INSTANCE_DIR/.kronos-create.lock`）+ 移除 `--check path_in_use=1` + BASE_DIR
  可配置（`KRONOS_BASE_DIR`，默认不变）。TDD 测试
  `test_create_vm_serializes_virt_install_under_concurrency` RED→GREEN
  （mock virt-install/virsh/qemu-img/curl/free/df/cp，并发跑两个 create-vm.sh，
  验证 virt-install 调用时间不重叠）。ruff All checks passed + bash -n 干净 + 测试绿。
- T1 完成：独立只读审查 PASS-WITH-NITS，stub stray-file minor 已修（qemu-img touch 倒数第二参数取 1 词，清理 backend/50G），复跑 ruff + pytest 绿。
- T2 端到端待用户部署后验证。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh scripts`（bash -n + shellcheck）。
- 验收场景：
  1. `./scripts/check.sh scripts` 干净（shell 语法 + shellcheck 无 error）。
  2. 端到端（部署后）：同宿主批量创建多 VM，不再报 pool already exists / domain not found。
- TDD：Python 集成测试 `test_create_vm_serializes_virt_install_under_concurrency`（mock virt-install/virsh/qemu-img 等，并发跑两个 create-vm.sh，验证 virt-install 调用时间不重叠=串行）+ `check.sh scripts` + 独立审查 + 端到端。
