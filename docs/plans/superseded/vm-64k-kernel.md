<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 创建 2403sp4-64k 内核 VM/物理机 + update 流水线 pre_env 换 64k

## 状态

已于 2026-09-04 被 [ADR 0024](../../adr/0024-vm-64k-kernel-post-processing.md) 取代，移入本目录保存历史实施记录。本文的旧 T3/T4 流水线 pre-env 安装、累积仓库和“本周只记录检查”的描述均不可再执行。

## 当前有效规则

- `-64k` 只支持 `openEuler-24.03-LTS-SP4-64k`/aarch64，并在 VM 创建或物理机 PXE 的环境创建阶段完成后处理；不在 Mugen pre-env 后安装或重启。
- 普通 VM 申请可最多回退 5 个 update 轮次；流水线 VM/物理机只检查最新轮。最新轮未转测时，当前 Node、EnvSet 和 Case 收敛为 `NOT_EXECUTED`，TestJob 正常成功。
- 安装成功必须设置默认 64k 启动项、等待 SSH 恢复并验证 `getconf PAGESIZE=65536`；物理流水线失败时资源禁用。

下文仅保留当时的目标、任务和进度，不能作为当前实现或验证清单。后续若需补充 64k 行为，必须基于 ADR 0024 新建 active 计划。

## 目标

支持创建 2403sp4-64k 内核的 VM/物理机用于 update 测试，两种场景：
1. **普通申请**（VM/物理机创建时 64k）：os_version 选"openEuler-24.03-LTS-SP4-64k"，正常装 2403sp4
   后 → 换 update repo → dnf install kernel-64k + 重启 → 对外提供 64k 机器。
2. **update 测试流水线**：用普通 4k 2403sp4 VM，pre_env 从当前 update repo 换 64k kernel
   （验证 repo 里的 kernel-64k）。repo 没 64k → 日志报"本周未转测 64k kernel，跳过测试"+ 结束。

64k 内核从 2403sp4 update repo 获取（每周转测）。普通申请时若当前 repo 无 kernel-64k，自动
回退上一轮 repo 再试，最多 N 轮，全找不到才失败回滚。update 流水线不回退，直接跳过测试。

## 范围

- **A. os_version 识别**：os_version 后缀 "-64k"（如 `openEuler-24.03-LTS-SP4-64k`）触发 64k
  后处理。不新增字段，复用 os_version。
- **B. 普通申请 64k 后处理（VM）**：create-vm.sh 末尾，os_version 含 -64k 时，VM 启动后
  SSH 换 update repo → dnf install kernel-64k → 重启 → 验证 64k page size。
- **C. 普通申请 64k 后处理（物理机）**：pxe_install 验收后，os_version 含 -64k 时，SSH
  换 update repo → dnf install kernel-64k → 重启 → 验证 64k page size。
- **D. update 流水线 pre_env 64k**：pre_env.sh 从当前 update repo dnf install kernel-64k +
  重启。repo 没 64k → 日志"本周未转测 64k kernel，跳过测试" + 跳过本 env_set（不回退）。
- **E. 回退策略**：普通申请 B/C 后处理时，当前 update repo 无 kernel-64k → 自动换上一轮
  repo URL 再试，最多 5 轮。全找不到 → 创建失败回滚 + 日志。
- **F. 日志记录**：
  - 普通申请成功：task_events phase=kernel_64k_installed message="kernel-64k from round-N"
    + 更新 resource.kernel_version="6.x.x-64k (round-N)"。
  - 普通申请回退全失败：task_events phase=kernel_64k_not_found + 失败回滚。
  - update 流水线跳过：task_events phase=kernel_64k_skipped message="本周未转测 64k kernel，
    跳过测试"。

## 非目标

- 不改 VM 创建/PXE 主流程（只在末尾加 64k 后处理 hook）。
- 不新增数据库字段（用 os_version 后缀 -64k）。
- 64k 只针对 2403sp4（其他 os_version 不支持 -64k 后缀）。
- 不做 64k 内核镜像仓库（kernel-64k 从 update repo rpm 安装，不是独立 qcow2 镜像）。
- 不改其他 os_version 的 update repo/换源逻辑。
- 不改 spec/ADR 0005/0002（VM 创建不变式不改，64k 是后处理 hook）。

## 确认决策（grilling 8 题）

1. **64k 在哪换**：创建流程末尾后处理（VM 创建成功/PXE 成功后换 repo+dnf install+重启）+ update
   流水线 pre_env。通用，不改主流程。
2. **配置方式**：os_version 后缀 "-64k"（如 openEuler-24.03-LTS-SP4-64k），不新增字段。
3. **update repo URL**：复用 2403sp4 update 源（不新配置）。
4. **kernel-64k 缺包时**：普通申请回退上一轮 repo；update 流水线跳过测试。
5. **回退策略**：脚本自动回退 N 轮（5）+ 日志提醒（用户知道装的是哪轮内核）。
6. **os_version 识别**：后缀 -64k 触发 + task_events + resource.kernel_version 日志。
7. **update 流水线 64k**：用 4k VM + pre_env 从当前 repo 换 64k（验证 repo kernel-64k）。
8. **两种场景区分（2026-08-07 grill 修订）**：普通申请回退找（按轮次 repoquery +
   回退 5 轮）；update 流水线**不 scope 到本周快照**——裸 `dnf install` 从 pre_env 配的
   累积 update repo 装过去转测的 64k（本周没转测也装），只加"本周转测检查"日志
   （`kernel_64k_repo_check`，找到/未找到都记，带 ISO 日期）进流水线日志 + VM 申请
   详情页。原"本周快照无 64k → 跳过"太麻烦，改为装累积 + 日志（用户接受测旧 64k）。
   裸 dnf install 失败（累积也无）才 SKIPPED。

## 任务

- [x] T0 后端 os_version 识别 + 64k 后处理 service（检测 -64k 后缀，触发换 kernel 后处理）。
- [x] T1 VM 64k 后处理（process_vm_request create_lease 后调 install_kernel_64k_via_ssh
  + round 回退 5 轮 + 全失败 _rollback_just_created_vm）。含 T1a round 回退 + T1b host 集成。
- [x] T2 pxe_install 末尾 64k 后处理（Step5 后调 apply_kernel_64k_to_physical + 全失败标 ERROR）。
- [x] T3 update 流水线 pre_env 64k（version -64k 信号 + run_env_set Python 装 kernel-64k +
  repo 没就 SKIPPED + 日志，不回退）。
- [x] T4 回退策略（普通申请回退 5 轮 repo + 日志；流水线不 scope 到本周快照、装累积
  repo 的 64k + "本周转测检查"日志 `kernel_64k_repo_check`）。
- [ ] T5 TDD + check.sh + Audit（TDD 绿 + check_backend 绿 + check_docs 绿；Audit 待跑）。
- [ ] T6 部署 dev + 端到端。含 review 遗留两项（均需 dev 真机实跑才能定，T0-T3 部署前不触发，盲写无意义）：
  - **B 验证 64k 真启动**：`dnf install kernel-64k` 装了≠ 64k 真启动（grub 可能仍默认 4k）。T6 实跑看 `getconf PAGESIZE` 是否 65536；不自动默认就加 `grubby --set-default` 指向 64k kernel。验证失败→按 kernel_64k_not_found 回滚/标错。
  - **C VM SSH-login 竞态**：`create-vm.sh:589` 只等 TCP 22 端口，不等 sshd 接受登录。T6 看 install_kernel_64k_via_ssh 首 SSH 是否竞态→空 repoquery→误回滚。竞态就在装之前加 `wait_for_ssh_login`（B 的 post-reboot 等待也复用它）。物理机路径有 `_wait_for_ssh` 兜底，不受影响。

## 进度

- Clarify + grilling 完成（8 题），确认门通过。
- Architect 完成（explore subagent 查技术方案）：
  - **VM 后处理插入点**：`vms/service.py:process_vm_request` line 758（`create_resource_from_vm_result` 后）→ `request.status=SUCCEEDED` 前，调 `apply_kernel_64k`。SSH 辅助用 `run_ssh_command`（`test_management/remote.py`）。
  - **物理机后处理插入点**：`vms/pxe_install.py:249→251`（SSH 验收成功后→凭据回写前），`run_ssh_command` 已 import（line 26），密码 `DEFAULT_ROOT_PASSWORD` 可用。
  - **update 流水线 pre_env**：`mugen_runner.py:run_hook`（`execution.py:151-160` 调用），无内置换源，要在模板 pre_env 或 run_hook 前加 64k 换 + 跳过逻辑。
  - **round 回退（已纠正）**：Architect 原笔记说用 `image_discovery.discover_images()` 枚举回退是**错的**——`discover_images()` 枚举的是 qcow2 镜像 round（值如 `round-9`，来自 `iteration/<dist>/<version>/<round>/<arch>/`），与 kernel-64k 所在的 update repo 轮次不是一回事。update repo 轮次是日期目录 `update_YYYYMMDD`，从 `${version}-update.json` 取（`pipelines/repodata.py:_latest_update_dir` 已实现取最新一个）。T1a 新增 `list_update_dirs(version)` 复用同一 JSON 解析返回全量降序列表，最多回退 5 轮。用户已确认（2026-08-06 grill）。
  - **VM_IMAGE_REPO_ROOT 冲突已修**：compose 默认去掉 `/iteration`（commit 1e3cd89），dev.env/prod.env 已正确。
- **T0 完成**（未 commit）：`apply_kernel_64k` service（os_version -64k 识别 + SSH dnf install kernel-64k + reboot + 日志 task_events + kernel_version 更新）。TDD 2 测试绿（47 passed）。不含 round 回退（T1a）。
- **T1a grill 已确认**（2026-08-06，4 题决策）：
  1. 轮次来源：用 `repodata.py` 同源逻辑（新增 `list_update_dirs(version)` 返回 `update_YYYYMMDD` 全量降序），**不用** `image_discovery.discover_images()`（那是 qcow2 镜像 round-9，与 update repo 无关）。
  2. 换 repo 方式：service.py 内极小 SSH helper——给定 round 标签，往 VM 写 `[openEuler_update_${round}]` repo 文件（baseurl 指向该轮 update 目录）+ dnf clean + makecache。不引入 `pipelines/seed.py` 的 `UPDATE_REPO_SETUP` 整块（含 EPOL/official/source 等无关逻辑）。
  3. 无包检测：每轮先 SSH `dnf repoquery --enablerepo=openEuler_update_${round} kernel-64k`；有输出→`dnf install`；无输出→try next。多一轮 SSH 但回退判定可靠，不把网络错误判为“无包”。
  4. 全失败回滚：销毁刚建的 VM（既有销毁路径）+ `fail_request(code=kernel_64k_not_found)` + `task_events phase=kernel_64k_not_found`。与 VM 创建失败语义一致。
  - 日志 `kernel-64k from round-N` 的 “round-N” 解释为实际 round 标签 `update_YYYYMMDD`（比序号更可调试）。
  - 回退逻辑做成 service.py 内可复用 helper，T1（VM）+ T2（物理机）共用；T3 流水线不回退（用最新一轮，无则跳过+日志）。
- **T1/T2/T3 待做**：
  - T1a: round 回退（discover_images 全量枚举 + 排序回退最多 5 轮 + 日志记录 round）
  - T1b: host_runner 集成（process_vm_request line 758 后调 apply_kernel_64k）
  - T2: 物理机 64k 后处理（pxe_install.py:249→251 调 apply_kernel_64k）
  - T3: update 流水线 pre_env 64k（模板 pre_env 或 run_hook 前换 64k + repo 没就跳过测试+日志）

## 进度（T0-T3 完成态，2026-08-07）

- **T0-T3 全部完成**（未 commit）：279 测试绿，ruff 绿。实现：
  - `repodata.py:list_update_dirs`（新增，返回 `update_YYYYMMDD` 全量降序，复用 `_collect_update_dirs`；`_latest_update_dir` 重构为复用它）。
  - `service.py:install_kernel_64k_via_ssh`（共享核心：轮次枚举 + 写每轮 update repo + repoquery 预检 + dnf install + reboot + 日志；全失败 raise `Kernel64kNotFoundError`，事件通过 `record_event` 回调由 VM/物理机各自记录）。
  - `service.py:apply_kernel_64k`（VM 入口，包 `record_vm_request_event`）+ `_rollback_just_created_vm`（destroy-vm.sh + 释放租约 + 软删 resource + fail_request）。`process_vm_request` create_lease 后调 apply_kernel_64k；except `Kernel64kNotFoundError` → `_rollback_just_created_vm(host=)` + return。
  - `pxe_install.py:apply_kernel_64k_to_physical`（物理机入口，包 `_record_event`，subject_type=resource/task_type=pxe_install）；`_record_event` 扩展 `error_code`；`run_pxe_install` Step5 后调，全失败标 `management_status=ERROR`（物理机不能销毁，留 4k）。
  - `mugen_runner.py:apply_pipeline_kernel_64k`（流水线入口：判 `job.os_version` 以 `-64k` 结尾 → 是则 `dnf install kernel-64k`（当前 update repo，不回退）→ 成功 reboot+wait_for_ssh_ready，失败标所有 case_run SKIPPED + env_set SUCCEEDED + `kernel_64k_skipped` 日志；非 -64k 直接 no-op，无 SSH）。`execution.py:execute_env_set` pre_env 后调。
  - `service.create_vm_request`：`os_version` 带 `-64k` 时 strip 后查 base 镜像 + `request.os_version` 保留 `-64k`（否则 find_image miss）。
  - 前端：`api/core/pipelines.ts` `KNOWN_VERSIONS` 加 `openEuler-24.03-LTS-SP4-64k`；`views/virtual-machines/index.vue` `osVersionOptions` 在 2403sp4 base 存在时追加 `-64k`，`roundOptions` 按 base 版取 round。
  - **pivot**：T3 信号从 `config_data["kernel_64k"]`+哨兵 改为 `version -64k` 后缀（用户前端选 -64k 版本即触发，无额外 SSH，无 builder 注入）。
  - `config.py:vm_openeuler_update_repo_root`（新 settings，默认 `http://121.36.84.172/repo.openeuler.org`）+ `.env.example`/`server.env.example` 占位。
- **TDD 覆盖**：T1a 5（含回退+rollback）+ T1b 2（VM 集成成功/失败）+ T2 2（物理机装/全失败）+ T3 3（helper skip/install/noop，version 信号）+ find_image -64k strip 1 = 13 新测试。
- **kernel_version 标记**为 `64k ({round})`，**不读真实 uname、不验证 page-size**（避免 reboot 后轮询 SSH）。注意：kernel-64k installed ≠ 64k 真启动（grub 可能仍默认 4k），page-size 验证（`getconf PAGESIZE`=65536）+ 必要的 `grubby --set-default` + VM SSH-login-wait 留 **T6 dev 实跑确认**后再加（见任务 T6 B/C）。
- **check_docs 误报已修**：CONTEXT.md/ADR/spec 里被 check_docs 误判为相对时间的措辞（recent-N / 就近上游语义）已改"最新/就近"稳定措辞，check_docs 现绿。
- **待办**：T5 Audit（/code-review + /neat-freak，用户触发）+ T6 部署 dev 端到端。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh all`。
- TDD：os_version -64k 识别 + 后处理 mock（SSH dnf install + 重启）+ 回退 + 日志。
- 验收场景：
  1. 申请 os_version=2403sp4-64k 的 VM → 装 2403sp4 → 换 64k kernel → 重启 → 64k page size。
  2. repo 无 kernel-64k → 回退上一轮 → 找到 → 装 + 日志记录 round。
  3. update 流水线 pre_env 换 64k → repo 无 → 跳过测试 + 日志。
