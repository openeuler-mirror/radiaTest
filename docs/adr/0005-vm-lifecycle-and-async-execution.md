<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0005：VM 生命周期和异步执行(VM Lifecycle and Async Execution)

## 状态

已接受(Accepted)。

## 背景

radiaTest 需要支持用户按需申请和释放 openEuler VM。VM 创建可能超过 2 分钟，并依赖
libvirt、内网 qcow2 镜像仓库、DHCP 租约和宿主机实时容量。该能力不适合在 Web
请求线程内同步完成，也不能把 VM 创建编排设计成任意远程 Shell 执行入口。

## 决策

VM 申请和释放使用异步任务模型：

- API 创建 VM 申请单后立即返回。
- VM 创建和销毁由 Celery worker 执行。
- Redis 作为 Celery broker/result backend。
- 申请单、资源、租约和事件等业务状态保存在 PostgreSQL，Redis 不作为业务状态来源。
- 异步任务过程写入通用任务事件(Task Event)，用于定位 worker 领取任务、选择执行目标、
  连接宿主、执行宿主脚本和处理结果等问题。
- 任务事件保存脱敏阶段摘要，不保存完整原始日志或凭据。
- Worker 运行宿主脚本时持续读取 stderr 阶段事件并立即提交任务事件；前端仍通过手动刷新读取，
  不引入实时日志流。
- 任务事件默认保留 30 天，通过部署流程和 CLI 清理，不引入独立定时器或新服务。

VM 宿主和创建方式：

- VM 宿主是带 `vm-host` 标签的 `PHYSICAL` 资源。
- VM 宿主应由 `ADMIN` 永久占用，避免作为普通测试资源被发放。
- radiaTest 只按资源类型、管理状态、`vm-host` 标签和 `arch` 字段筛选候选宿主。
- 不维护独立宿主容量字段，也不从 CPU/内存描述字段推导可分配容量。
- 宿主脚本实时检查 CPU、内存和 `/var/lib/libvirt/images` 所在文件系统的磁盘剩余容量。

宿主执行边界：

- VM 创建和销毁脚本放在 radiaTest 代码仓。
- Backend 和 worker 通过 SSH 公钥登录宿主机 root，把固定脚本临时传到宿主机执行。
- Backend 和 worker 容器只读挂载 `/etc/kronos/ssh`，默认使用
  `/etc/kronos/ssh/id_rsa` 作为宿主机登录私钥；backend 用于同步 VM 电源操作，
  worker 用于异步 VM 创建和销毁。
- 参数使用 JSON，并通过 base64 环境变量传给脚本。
- 脚本 stdout 只输出 JSON 结果，stderr 用于诊断。
- 宿主脚本可以在 stderr 输出结构化阶段摘要和可复现的宿主外部命令，worker
  把这些信息保存为任务事件；命令不包含凭据。
- 宿主脚本失败时，worker 会把触发失败命令的有限 stderr 摘要写入错误信息；
  不保存完整宿主命令日志。
- 创建脚本通过 `virt-install` 生成 libvirt domain XML，不手写完整 domain XML；
  兼容 `virt-install` 不支持 VNC WebSocket 参数的版本时，只补写生成 XML 中的
  VNC WebSocket 属性，再用 `virsh define` 加载。
- aarch64 VM 创建时添加 `pcie-root-port`，让 virtio 网卡落到 PCI bus 2，以兼容
  依赖 `enp2s0` 的既有镜像配置；x86_64 VM 不强制添加该 controller，避免固定
  PCI slot 与宿主默认 machine topology 冲突。
- VM 创建和销毁不提供任意远程 Shell 能力，只执行固定宿主脚本。

安装介质和磁盘：

- 平台从内网 HTTP 镜像仓库目录索引解析可申请镜像，不提供镜像管理页面。
- VM 申请支持自动安装方式和手动安装方式。
- 自动安装方式沿用镜像仓库目录发现结果，提交申请时重新校验所选 qcow2 镜像仍然存在。
- 手动安装方式由用户提供 ISO URL，后端只做基本 URL 格式校验，不要求该 URL
  能被镜像仓库目录发现。
- Web 用户可以上传本地 ISO，平台为其生成内网 HTTP URL，再沿用同一手动安装流程。
- 手动安装 URL 只允许 HTTP/HTTPS，不限制域名或 IP 网段。
- 手动安装方式的发行版、版本和轮次用于展示、追踪和命名，不作为镜像发现校验条件。
- 手动安装方式的轮次可以为空；为空时 VM 实例名和磁盘名省略轮次片段。
- VM 实例名时间戳按 `DISPLAY_TIMEZONE` 生成，默认 `Asia/Shanghai`，格式为
  `YYYYMMDDTHHMMSS`，不带 `Z` 后缀。
- 手动安装方式的缓存文件名只包含 URL 短哈希，避免同一 URL 因展示字段变化而重复下载。
- VM 申请单持久化安装方式(`install_type`)和实际下载地址(`image_url`)；安装方式取值为
  `auto` 或 `manual`。
- 上传的 ISO 按环境保存在 radiaTest 服务器 `/data/kronos/uploads/<环境>/`，不写入
  PostgreSQL、Docker 镜像或容器可写层。后端以读写方式挂载，nginx 以只读方式挂载，
  两者使用共享 SELinux 标签访问同一目录。
- 上传接口要求登录，所有可申请 VM 的角色均可使用；宿主下载地址仅在内网暴露且不鉴权，
  让宿主脚本继续直接使用 `curl image_url`。
- 原始文件名是不可信元数据，只用于扩展名校验、页面提示和审计；磁盘路径只使用平台生成的
  临时名和内容 SHA-256，不拼接用户输入。文件名拒绝路径分隔符、控制字符和超过 255 字符
  的值。
- 后端按原始请求体流式写入并同步计算 SHA-256，不经容器 `/tmp` 中转；nginx 关闭该
  路由的请求体缓冲。单个 ISO 最大 20 GB，上传前要求写入后仍保留 10 GB 可用空间且
  文件系统使用率低于 90%。
- 完整文件使用 SHA-256 命名并去重；上传先写唯一 `.part`，完成后原子 rename。
  重复上传会复用文件并刷新保留时间，并发上传同一内容不会产生多份完整 ISO。
- 上传目录使用跨进程文件锁串行写入，确保每次上传的空间预检包含其他上传已写入的空间。
- 上传失败、浏览器断开或写入异常时删除本次 `.part`。后续上传机会式清理超过 24 小时的
  `.part` 和超过 30 天的完整 ISO；清理只作用于当前环境上传目录。
- 上传成功写审计日志，记录原始文件名、SHA-256、文件大小和相对 URL，不记录内容。
- radiaTest 不解析、解压或执行上传内容，只校验 `.iso` 扩展名和传输边界；这与现有手动
  URL 允许用户指定任意 HTTP/HTTPS 安装介质具有相同内容信任边界。nginx 下载响应固定为
  `application/octet-stream` 和 attachment，并设置 `X-Content-Type-Options: nosniff`。
- 不提供上传 ISO 列表、手动删除、分片上传、断点续传或后台清理服务。
- 宿主机把源 qcow2 缓存在 `/var/lib/libvirt/images/kronos/cache/`。
- 自动安装方式使用从缓存复制出的实例盘，不直接使用缓存镜像。
- 手动安装方式把 ISO 缓存在同一缓存目录，创建固定 50 GB 空系统盘，并通过 VNC
  由用户完成系统安装。
- 手动安装方式的启动顺序为硬盘优先、ISO 兜底；脚本在最终 libvirt XML 中显式设置
  `hd,cdrom`，空盘首次启动会进入安装器，安装完成后重启优先从硬盘启动。
- 自动和手动安装方式创建出的虚拟资源都保存默认 SSH 账号 `root` 和密码 `openEuler12#$`。
- 自动安装方式的系统盘容量由所选 qcow2 镜像的虚拟大小决定，VM 申请不接收系统盘大小参数。
- 缓存下载和实例盘创建都使用临时 `.part` 文件和原子 rename。
- 镜像服务返回 `Content-Length` 时，宿主脚本会在下载前按下载文件大小和保留水位
  做磁盘预检；拿不到 `Content-Length` 时继续执行下载，下载后仍按实际镜像信息
  做完整容量检查。
- 创建失败、中断或超时时，脚本尽量删除缓存 `.part`、实例盘 `.part`、实例盘和
  已定义的 libvirt domain。
- 每次创建 VM 时，宿主脚本机会式清理 `/var/lib/libvirt/images/kronos/cache/` 中超过
  30 天且未被 libvirt domain XML 引用的源 qcow2 和手动 ISO；不清理 `instances/`
  或其他 libvirt 镜像目录，不引入 cron、timer 或独立清理服务。
- 可选数据盘由平台创建固定 50 GB qcow2，数量由用户选择。

成功和失败语义：

- 自动安装方式创建成功必须拿到 DHCP IP，并确认 VM 的 22 端口可连接。
- 手动安装方式创建成功只要求 libvirt domain 已启动并能读取 VNC 端口；不等待用户完成系统安装，不等待 SSH 可连接。
- 创建脚本必须尽量保证全成或全退；任一步失败时回滚 domain 和实例盘。
- 如果失败前已经创建 libvirt domain，脚本在回滚前记录有限的 domain 诊断摘要。
- 回滚失败时不继续尝试其他宿主，申请单失败并提示管理员处理。
- VM 申请长期停留在 `creating` 或已开始后等待宿主并发槽位的 `queued` 时，管理员先人工确认宿主机没有残留 domain 或
  `.part` 文件，再手动刷新 VM 申请列表或申请事件。刷新时会把超过 60 分钟仍处于
  `creating/queued` 的申请单标记为失败；该懒判断只修改 radiaTest 数据库状态，不连接宿主机
  清理资源。
- VM 释放和到期自动释放都触发异步销毁；销毁成功后才释放租约并软删除 VM。
- 销毁失败时租约保持占用，VM 继续显示为需要管理员处理。
- 手动安装完成后，当前占用人或 `ADMIN` 可以在 VM 详情中按 MAC 地址从 DHCP 租约刷新
  OS IP；刷新不改变 radiaTest 资源租约。
- 当前占用人或 `ADMIN` 可以在 VM 详情中读取实时电源状态，并同步执行启动、关机和
  重启。电源操作使用宿主机 `virsh` 短命令，不进入 Celery 队列，不自动轮询状态。

Web VNC 控制台：

- VM 创建时同时配置传统 VNC 端口和 VNC WebSocket 端口。
- VNC WebSocket 端口保存为虚拟资源规格字段 `vnc_websocket_port`，与 `vnc_port`
  同级。
- Web VNC 控制台使用 noVNC，浏览器直接连接宿主机暴露的 VNC WebSocket 地址。
- radiaTest 后端不代理 VNC 图像流，不在宿主机额外运行 websockify。
- 当前内网 HTTP 阶段使用 `ws://<host>:<vnc_websocket_port>/`，不配置 `wss://` 或证书。
- Web VNC 控制台不设置独立 VNC 密码。
- Web VNC 控制台入口权限与 VM 凭据查看一致；该权限只控制 radiaTest 页面入口，不阻止
  用户绕过 radiaTest 直接连接已知的宿主机 WebSocket 端口。
- 旧 VM 不做自动迁移；缺少 `vnc_websocket_port` 时，控制台配置接口返回未配置错误。
- Web VNC 控制台只支持 VM，不支持物理机 BMC KVM 控制台。
- 手动安装 VM 的生成 XML 会把 `on_reboot` 固定为 `restart`，避免安装器内点击重启后
  domain 被 libvirt 关闭。

## 取舍

选择 Celery/Redis，而不是手写后台线程或同步请求，是因为 VM 创建和测试任务执行耗时长，
成熟队列能提供更清晰的任务边界和重试模型。

选择通用 `task_events`，而不是只在 VM 申请中追加 JSON 日志，是因为 VM 创建、销毁和
测试任务都有类似的异步执行轨迹；通用事件表能复用同一套时间线模型，同时各业务页面只暴露必要入口。

选择“脚本随平台传输执行”，而不是预先分发到每台宿主机，是为了让脚本版本跟随
radiaTest 代码版本，减少宿主机初始化和脚本漂移。

选择 `virt-install` 生成 domain XML，而不是手写完整 libvirt XML，是为了把架构相关的
固件、机器类型和设备模型交给成熟工具处理；radiaTest 只负责传入磁盘、网络、CPU 和内存
等必要参数。VNC WebSocket 端口由生成 XML 后的最小补写完成，避免依赖
`virt-install --graphics` 是否支持 `websocket` 选项。

选择宿主实时检查作为准入依据，而不是数据库容量台账，是因为宿主可能存在人工创建的
VM 或其他非 radiaTest 负载。数据库只记录 radiaTest 创建的资源、租约和历史，不作为真实
容量的唯一来源。

选择 noVNC 直连宿主机 VNC WebSocket，而不是 radiaTest 后端代理或宿主机 websockify，
是为了避免新增长连接代理和宿主常驻服务。代价是 VNC WebSocket 端口本身不是强鉴权
入口，radiaTest 只能控制页面入口展示。

选择把用户上传的 ISO 保存在 radiaTest 服务器 `/data` 并由 nginx 提供内网下载，而不是
引入对象存储或独立文件服务，是因为当前是单服务器内网部署。流式原始请求体避免
multipart 在容器临时目录形成第二份大文件；代价是不支持断点续传和跨服务器共享。

## 影响

- 单机 Compose 拓扑增加 `redis` 和 `worker` 服务。
- `backend` 和 `nginx` 需要分别读写、只读挂载当前环境的 ISO 上传目录。
- VM 宿主需要准备 libvirt、镜像目录、公钥登录和脚本依赖的基础工具。
- VM 创建失败时，用户和管理员可以先查看申请单任务事件，再检查宿主机状态。
- 测试任务异步执行可以复用 Celery/Redis 基础设施。
