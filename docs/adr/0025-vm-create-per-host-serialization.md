<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0025：流水线 VM 创建按宿主机并发控制

日期: 2026-08-15

## 状态

已采纳。

## 背景

一次流水线触发 5 版本 × 2 架构 × 4 模块 = 40 个 RunJob，每个 RunJob 独立调 `create_env_node_vm` → `process_vm_request` → 宿主机上跑 `create-vm.sh`。所有任务同时压到宿主机，IO/CPU 争抢导致每台 VM 创建 20-30 分钟。

实测：单独触发 1 台 VM（docker-test 流水线）时，创建只需 ~1 分钟。瓶颈不是单台创建慢，而是多台并发创建争抢宿主机资源。

## 决策

### 1. 按宿主机并发控制 VM 创建 + 负载均衡

在 `process_vm_request` 中，当 `serialize_per_host=True` 时：

1. **遍历候选宿主**，对每个宿主先尝试非阻塞锁（`LOCK_NB`）。
2. 拿到锁 → 选定该宿主，执行 `run_host_script("create-vm.sh")`。
3. 没拿到锁（该宿主所有槽位忙）→ 跳到下一个候选宿主试。
4. 所有候选宿主都忙 → 回到第一个候选宿主阻塞等待（`LOCK_EX`），记 `queued` 事件。

这样同架构多台宿主机能均匀分布 VM 创建任务，新增宿主自动纳入负载均衡。不同宿主机并行不受影响。

### 2. fcntl.flock 多槽位文件锁

用 `fcntl.flock(LOCK_EX)` 文件锁，按 `settings.vm_max_concurrent_per_host`（默认 4，可配）为每个宿主机分配 N 个"槽位"lock 文件，路径 `/tmp/kronos-host-locks/vm-create-{host_ip}-{slot}.lock`。每个槽位允许 1 台 VM 同时创建，N 台可并行。所有槽位忙时，轮询所有 slot（`LOCK_NB` + 1s sleep），不阻塞在单个文件上（避免 flock 排他性导致其他等待者卡在 slot 0 上）。

选择文件锁而非 threading.Lock / multiprocessing.Lock 的原因：
- Celery 的 ForkPoolWorker 是 fork 出来的独立进程，`threading.Lock` 跨不了进程。
- `multiprocessing.Lock` 在 Celery billiard fork 行为下行为复杂。
- 文件锁跨 fork 进程可靠，进程崩溃时内核自动释放，无需 Redis 等外部服务。

### 3. 只作用于流水线 VM 创建

`process_vm_request` 新增 `serialize_per_host: bool = False` 参数。`create_env_node_vm`（流水线）传 `True`，手动 VM 申请不传（默认 `False`）。

### 4. 排队状态和事件可见

所有候选宿主都忙时，VM 申请单状态从 `creating` 切换为 `queued`（"等待创建"），同时记录 `vm_request_event` phase=`queued`，message 含宿主 IP。阻塞等到锁后切回 `creating`。前端 VM 管理页面和时间线均可见。

## 不采用

- **全局串行**：不同宿主机可以并行，全局串行浪费多宿主机能力。
- **Redis 分布式锁**：当前单 worker 部署，文件锁够用。引入 Redis 增加复杂度和依赖。
- **全局串行**：不同宿主机可以并行，全局串行浪费多宿主机能力。
- **手动 VM 申请也排队**：手动申请频率低，不需要排队。

## 影响

- `vms/host_lock.py`（新增）：`host_create_lock(host_ip)` context manager + `try_host_lock(host_ip)` / `release_host_lock(fh)` 非阻塞接口。
- `vms/service.py`：`process_vm_request` 加 `serialize_per_host` 参数，遍历候选宿主试锁（非阻塞），全忙时回退阻塞等第一个宿主。
- `vms/models.py`：`VMRequestStatus` 新增 `QUEUED = "queued"`，排队时设此状态，锁获取后切回 `CREATING`。
- `test_management/envs/vm.py`：`create_env_node_vm` 传 `serialize_per_host=True`。
- `views/virtual-machines/vm-view.ts`：前端显示 `queued` 状态为"等待创建"（蓝色标签）。
- Spec 0001 同步。
