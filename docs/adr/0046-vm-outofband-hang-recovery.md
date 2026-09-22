<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0046: VM 挂死的宿主机带外判活与硬复位恢复

日期：2026-09-11
状态：已接受（2026-09-11 修订：增加用例间连接拒绝探针，victim 用例零损失；修订二：硬复位前关键边界强制刷盘）

## 背景

2026-09-05 至 09-11 期间 prod/dev 共 60+ 个 VM TestJob 因 SSH 断连中断（prod 32 + dev 32），DB 事件流回放定位出三类根因：

1. **initrd 家族用例**（`oe_test_service_initrd-cleanup` 等 4 例）：脚本伪造 `/etc/initrd-release` 强行 isolate 到 switch-root，sshd 被停——9/8 prod 14 个任务全灭。已由危险用例过滤（ADR 0043）拦截。
2. **`oe_test_ebtables`/`oe_test_ebtables_002`/`oe_test_firewalld_server` 链**（DevStation rc4 镜像）：用例失败且残留防火墙规则（DROP），SSH 全部 `Connection timed out`——9/10 prod 4 个任务每个损失 232 个未执行用例（约 65% 覆盖率）。合法用例，失败模式"用例挂了且把网络带走"不可预知（同类：kernel 驱动加载、IPVLAN、libvirt socket 个例）。
3. **`oe_test_socket_sssd-nss`**：停 `sssd-nss.socket` 造成 NSS 阻塞，新 SSH 认证挂起 3–5 分钟后自愈——每个 mugen 全量任务误标 1 个用例 `vm_hang`（job 仍继续，但该用例真实结果丢失）。ADR 0044 范围取舍时"机制未取证，不查不修"的遗留项。

结构缺口：ADR 0042/0044 的带外确认门只覆盖配置了 BMC 的物理机；VM 走"阈值+复核即判死"，熔断（连续 3 个 vm_hang/RemoteCommandError）后直接批量标 error，从未利用宿主机这个天然带外通道。平台已有宿主机 SSH 通道（`vm_host_ssh_key_path`，console 取证在用），`virsh domstate` 就是 VM 的"机箱电源状态"。

同场修复的预存缺陷：`_capture_and_store_console` 用 `getattr(resource, "host_resource_id")`/`getattr(resource, "vm_name")` 读宿主信息，但这两个字段在 `virtual_resource_specs` 拆表（ADR 0002）后不在 `resources` 主表上——getattr 恒 None，VM 挂死取证一直静默走 BMC 分支（no-op）。测试用 SimpleNamespace 假对象携带同名属性，掩盖了该缺陷。

## 决策

把 ADR 0044 的带外确认 + 观察模式架构对称推广到 VM，并补一个物理机没有的能力：宿主机硬复位恢复。

1. **domstate 判据（三态）**：心跳阈值+复核失败后经宿主机 `virsh domstate` 确认——`running`/`paused`/`in shutdown`/`in migrate`/`post-copy`/`pmsuspended`/`idle` → True（活态）；`shut off`/`shutted down`/`crashed`/`dying` → False（死态）；宿主 SSH 失败/空输出/未识别 → None（不下结论）。死态锚定 10 分钟关机宽限（复用 `WATCH_POWER_OFF_DEADLINE_SECONDS`，覆盖 `on_crash=restart` 自动拉起；等价物理机断电宽限）；活态与查询失败等观察上限（复用 `WATCH_TIMEOUT_SECONDS=1800`）。HangDetector 状态机零改动，`_VmHangGate` 对称 `_BmcHangGate` 提供 confirm/回调。
2. **自愈拿回真实结果**：观察期内 SSH 恢复（sssd 类 3–5 分钟）→ 用例继续执行拿回真实结果，不标任何错误——修复第 3 类误标。
3. **熔断点硬复位恢复**：连续 3 个 vm_hang/RemoteCommandError 触发熔断前，先尝试恢复——抓 console 存证（`console-recovery.log`）→ `virsh destroy` + `virsh start`（等价拔电重启，磁盘保留；destroy 容忍失败，start 后 domstate 活态即复位成功）→ 轮询 SSH 就绪（最长 `SSH_READY_TIMEOUT_SECONDS=900`，受任务剩余时间与取消约束）。成功 → 连击计数清零、肇事用例保持 `error(vm_hang)`（消息注明硬复位）、继续剩余用例；失败/无通道 → 维持原熔断批量标 error。**每环境集限 1 次**，避免杀手用例连环触发重启循环。
4. **适用范围**：宿主信息从 `virtual_spec.host_resource_id`/`vm_name` 解析（同场修复的预存缺陷），宿主机 `primary_ip` 与 `vm_host_ssh_key_path` 可用即启用；动态/静态 VM 一视同仁（租约保证任务期独占，destroy 只断电不删盘）。物理机、无宿主引用、key 未配置 → 无门无恢复，维持原判定（ADR 0044/0042）。
5. **事件与取证**：`vm_recovery_started`（warning）/`vm_recovered`（info）/`vm_recovery_failed`（warning）三段留痕；观察模式复用 `hang_watch`/`hang_recovered` 事件与 console 取证产物（watch-entry）；判死 detail 的关机证据区分来源——BMC"电源断开" vs 宿主机"VM 已关机"（`off_evidence` 属性），观察超时文案通用化为"观察期 N 秒未见恢复"。

## 备选方案与不采用理由

- **扩大危险用例过滤（ebtables/firewalld 入名单）**：ADR 0043 拦的是"设计上就会关机/切换 root"的用例；ebtables/firewalld 是合法网络测试，全局排除会在所有镜像上静默缩水覆盖，且"失败即致命"类不可穷举（kernel/IPVLAN/libvirt 个例证明）。恢复机制不挑用例，覆盖未知杀手。
- **首个 SSH 失败即硬复位**：单次 RemoteCommandError 常是瞬断（现状 continue 即自愈）；在 3 连击熔断点恢复，信号"持续死链"才动手，避免对瞬断 VM 无谓硬复位。代价是最多 2 个用例先标 error，相对每个任务 200+ 用例的损失可忽略。
- **`virsh reboot` 优雅重启优先**：防火墙残留/isolate 僵尸态对 ACPI 事件可能无响应，还得二级超时兜底；destroy+start 一步到位，对任务独占的测试 VM 无风险。
- **观察超时即恢复（不等熔断）**：心跳挂死路径（EnvSetHangError）与起连失败路径（RemoteCommandError）形态不同，统一在熔断点恢复一个挂载点覆盖两者；观察超时后最多再等 2 个用例的连接超时（约 1 分钟）才动手，时序可接受。
- **每环境集多次恢复**：连环杀手场景无实证（9/10 四个任务均单一断点）；一次预算内未恢复说明环境不可用，多次重启只会把 15h 预算烧在循环上。

## 修订：用例间连接拒绝探针（job 10235）

部署当日 kimariyb job 10235 实锤新形态：`oe_test_crypto_policies_switch` 在
1 秒内连续切换 7 次加密策略，每次 `update-crypto-policies` 经 reload-cmds.sh
执行 `systemctl try-restart sshd`，触发 systemd 启动速率限制（start-limit-hit）
——sshd 停止监听，而既建立会话不受影响，用例正常跑完判 passed。原版恢复
机制的缺口：① victim 用例要先吃 3 次连接失败才触发熔断恢复（每次事故最多
损失 3 个用例）；② 末尾用例杀掉 sshd 时用例循环已结束，post_env 直接失败，
全 passed 的 job 被误标 error。

修订决策：

1. **用例间探针**：每个用例执行前与 post_env 前做一次 SSH 探活，**只认
   `Connection refused`**（sshd 挂了但 OS/网络活着的确定签名，与
   _HeartbeatStats 的"拒绝"分类同源）且有宿主通道时，先硬复位恢复再继续
   ——victim 用例拿回真实结果，job 按真实结果收敛。
2. **超时/失联不触发**：机器状态未知时交给既有挂死链路（观察模式/熔断），
   误恢复代价是白硬复位一次。
3. **恢复预算按尝试计、与熔断点共享**：探针尝试过恢复（无论成败）即耗尽
   该环境集预算——恢复失败说明环境不可用，连环硬复位只会烧任务预算
   （与原版"每环境集限一次"同一保守性）。
4. 事件文案区分触发来源（trigger=probe/breaker），复用
   vm_recovery_started/vm_recovered/vm_recovery_failed。

带外核查事实：VM 域 XML 未配置 qemu-guest-agent 通道、镜像未装
qemu-guest-agent（`/dev/virtio-ports/` 不存在）——"免重启、只重启 sshd"当前
无通道可走，列为 backlog（依赖装机工序与镜像变更），本修订维持硬复位为
恢复手段。

## 修订二：硬复位前强制刷盘（job 10237/10238）

修订一部署当日实锤设计缺陷：`virsh destroy` 等价拔电，复位前未落盘的页缓存
写回全部丢失（ext4 延迟分配）。job 10238 现场：mugen 配置（conf/env.json）
与两个已通过用例的日志/results 写入后仅 0.5~7 秒即被 destroy → 全部 0 字节；
重启后每次 `mugen.sh` 在 read_conf.py 解析空 JSON 崩溃 → **后续用例全部秒败**
（表现为"恢复成功了但用例全失败、日志 0KB"）。job 10237（keep_env 复用被
复位过的 VM）同因秒败——损坏的环境会投毒后续任务。"destroy 磁盘保留"的原
假设不完整：磁盘结构在，近期写不在。

修订决策：**关键边界强制 sync**，把丢失面收敛到杀手用例自身——

1. 环境就绪后（部署/配置/pre_env 完成、首个用例前）对 control `sync` 一次：
   保住 env.json/框架状态，治"后续用例全失败"与 keep_env 复用投毒。
2. 每个用例正常返回后 best-effort `sync`：保住已完成用例的日志/results，
   治"日志 0KB"。
3. 两处门控在宿主通道存在（只有该 VM 可能被硬复位；物理机/无通道 VM 不付
   同步开销）。`sync_vm_disks` 契约：绝不抛异常——SSH 已死是杀手用例的预期
   场景，失败静默，下轮探针恢复接管。
4. 杀手用例自身的日志无法保住（sshd 死后无从 sync），由 console 取证覆盖
   ——接受的残留丢失面。

备选不采用：`virsh reboot` 优雅重启优先 + destroy 兜底（ACPI 让 OS 自己刷盘
但僵尸态可能不响应、恢复时长翻倍）列为 backlog，待本修订上线后按实际丢失面
评估；恢复后重跑 mugen prepare 的健康自检（平台耦合 mugen 内部结构）拒绝。

## 影响

- `HangDetector` 零改动：VM 门只是 `confirm_fn` 的另一个实现，断电/关机宽限状态机复用。
- `execute_env_set` 的两个相同 except 分支合并为一个；熔断点插入恢复尝试（每环境集一次预算由循环内局部状态持有，不落库不加表）。
- VM 挂死取证（console_diagnostic）自本 ADR 起真正生效（修复前恒走 BMC 分支 no-op）。
- 误判代价的有意变化：真挂死 VM 的判死最迟 30 分钟（原约 3 分钟）；熔断点恢复最多再花 15 分钟（SSH 就绪等待），受任务剩余时间约束不会越过 15h 总截止。
- 物理机行为不变：不做自动断电重启（ADR 0042 边界），宿主机硬复位仅针对任务独占的 VM。
- prod 部署另行授权（可与 ADR 0043 过滤同批）。
