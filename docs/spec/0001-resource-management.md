<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Spec 0001：资源管理功能规格(Resource Management)

## 状态

有效(Active)。

## 目标

radiaTest 提供可用的内网测试资源管理平台。真实用户应能查找机器、占用资源、查看授权凭据、释放资源；管理员应能维护资源台账、导入导出数据，并追踪关键操作。

## 用户和角色

`ADMIN`：

- 创建、禁用和重置本地用户账号。
- 分配角色：`ADMIN`、`TSE`、`TE`。
- 管理资源池。
- 创建、编辑、导入、导出和软删除资源。
- 导入当前租约。
- 申请 VM。
- 占用任何 active idle 资源，包括关键资源。
- 创建永久租约。
- 强制释放任何租约。
- 查看全部凭据。
- 查看审计日志和租约日志。

`TSE`（测试系统工程师）：

- 管理资源池。
- 创建和编辑 active 资源，但不能编辑被别人占用的资源。
- 申请 VM。
- 占用非关键的 active idle 资源。
- 续期和释放自己的租约。
- 强制释放 `TE` 租约。
- 只有占用非关键资源期间，才能查看该资源凭据。
- 查看全部租约日志。
- 不能查看审计日志。

`TE`：

- 查看资源公共信息。
- 申请 VM。
- 占用非关键的 active idle 资源。
- 续期和释放自己的租约。
- 只有占用非关键资源期间，才能查看该资源凭据。
- 查看自己的租约日志。
- 不能编辑资源、管理用户、导入导出或查看审计日志。

## 功能需求

### 认证(Authentication)

- 用户使用本地用户名和密码登录。
- 不支持 Web 自助注册。
- Web 会话使用 JWT 访问令牌。
- Web JWT 访问令牌有效期为 1 天。
- 用户可以创建带名称和过期时间的 PAT。
- PAT 明文只在创建时展示一次。
- PAT 只保存不可逆哈希。
- 禁用用户不能登录，也不能继续使用已有 PAT。
- 角色变更只影响变更后的请求。
- JWT 仅作为身份票据，授权以数据库中的当前用户状态和角色为准。
- 每次请求鉴权时检查用户是否仍然启用。
- 用户被禁用后，已有 JWT 不能继续访问 API。

### 用户管理(User Management)

- 用户管理仅 `ADMIN` 可用。
- 支持用户列表。
- 支持创建本地用户，创建时填写用户名、显示名、角色和初始密码。
- 支持修改显示名。
- 支持修改角色：`ADMIN`、`TSE`、`TE`。
- 支持启用和禁用用户。
- 支持重置密码。
- 仅支持单用户操作，不支持批量用户操作。
- 禁用用户不能登录，也不能继续使用已有访问令牌或 PAT。
- `ADMIN` 不能禁用自己。
- `ADMIN` 不能把自己的角色改为 `TSE` 或 `TE`。
- 系统不能禁用或降级最后一个启用的 `ADMIN`。
- 管理员重置密码用于处理其他用户账号；用户修改自己的密码使用独立流程。
- 创建用户时，管理员手动输入初始密码和确认密码。
- 重置密码时，管理员手动输入新密码和确认密码。
- 不生成临时密码。
- 不要求首次登录强制改密。
- 密码不写审计日志；用户管理审计记录操作类型、操作者、目标用户和不含密码的详情。
- 用户创建、角色修改、启用、禁用和重置密码必须写审计日志。
- 用户管理页面不展示审计日志；审计日志使用独立页面查看。
- 不支持物理删除用户。
- 不支持用户自助注册、自改角色或自改用户名。
- 不支持 OAuth 或 SSO 作为 Web 登录方式。
- 支持飞书身份绑定用于飞书 Bot 识别已有 radiaTest 用户。
- 不支持在用户管理页面维护 PAT。
- 用户管理开发不包含 PAT 创建、撤销或 PAT 鉴权。
- `create-admin` CLI 只用于初始化第一个管理员和紧急恢复。
- 用户管理 API 不要求 `Idempotency-Key`。
- 用户管理不提供独立用户详情页。
- 用户管理页面使用列表和弹窗完成操作。
- 新建用户、编辑用户和重置密码使用弹窗。
- 启用和禁用用户使用确认弹窗。
- 创建用户后不自动登录该用户。
- 不提供邀请链接、一次性注册链接、邮件通知或消息通知。
- 用户管理不展示在线状态。
- 不支持强制下线。
- 只有 `ADMIN` 显示用户管理菜单。
- `TSE` 和 `TE` 直接访问用户管理页面时显示无权限。
- 用户管理 API 必须后端鉴权，不能依赖前端菜单隐藏。
- 非 `ADMIN` 调用用户管理 API 返回 403。
- 用户管理 API 使用 REST 风格，`GET` 只用于读取，不用于修改。
- `GET /api/v1/users` 获取用户列表。
- `POST /api/v1/users` 创建用户。
- `PATCH /api/v1/users/{user_id}` 修改显示名、角色或启用状态。
- `POST /api/v1/users/{user_id}/reset-password` 重置用户密码。
- `POST /api/v1/users/me/change-password` 修改当前用户自己的密码。
- 不提供 `DELETE /api/v1/users/{user_id}`。
- 用户管理 API 错误遵循[平台运行时规格](./0005-platform-runtime.md)，本节不重复定义公共错误格式。

用户名规则：

- 用户名创建后不可修改。
- 用户名全局唯一。
- 用户名只允许小写字母和数字。
- 用户名长度为 3 到 64。
- 不允许中文、大写字母、空格、点、下划线或短横线。
- 中文姓名或真实姓名放入显示名。

显示名规则：

- 显示名可选。
- 显示名长度最多 128。
- 显示名允许中文、英文、数字和常见空格。
- 显示名前后空白自动去除。
- 用户列表和详情始终展示用户名；有显示名时同时展示显示名。

### 飞书 Bot(Feishu Bot)

- 支持每套环境配置一个独立飞书 Bot。
- `dev` 和 `prod` 都启用飞书 Bot，但必须使用不同飞书应用。
- `ADMIN` 在飞书开放平台创建飞书应用后配置 radiaTest；一套环境只需要配置一次。
- 飞书应用配置保存在数据库中，每套环境一份。
- 飞书应用配置包括 `app_id`、`app_secret` 和启用状态。
- `app_secret` 按内网测试环境规则明文保存在数据库中，不提交到 Git。
- radiaTest 不实现飞书应用扫码创建或绑定向导；`ADMIN` 在 radiaTest 手动保存 `app_id` 和
  `app_secret`。
- 飞书 Bot 运行在独立 `bot` 进程中，使用飞书长连接接收消息。
- 除 `help` 或 `帮助` 入口外，飞书用户必须先绑定已有 radiaTest 用户，才能使用 Bot 命令。
- 飞书绑定从已登录的 radiaTest Web 发起，扫码确认后完成绑定。
- 飞书绑定保存 `open_id` 和可用时的 `union_id`。
- 飞书 Bot 匹配绑定关系时优先使用 `union_id`，没有 `union_id` 时使用 `open_id`。
- 飞书绑定使用飞书 OAuth 授权码流程，只保存飞书用户标识，不保存 `user_access_token`
  或 `refresh_token`。
- 未绑定用户可以发送 `help` 或 `帮助` 获取飞书首页卡片；资源查询和凭据查看仍需要完成绑定。
- 飞书扫码不自动创建 radiaTest 用户，也不自动分配角色。
- 飞书 Bot 根据绑定关系使用对应 radiaTest 用户的当前角色和启用状态执行鉴权。
- 所有 Bot 命令和卡片交互只允许在飞书私聊中使用。
- Bot 产品范围包含查询型卡片交互、VM 申请和受资源权限约束的远程命令执行；
  其他写命令必须先补充确认、幂等和审计规则。
- Bot 一级卡片入口包括物理机管理、虚拟机管理、账号与帮助。
- 用户只有发送 `help` 或 `帮助` 时才进入一级卡片。
- 不对无法识别文本做兜底卡片回复，不做关键词自动跳转。
- 不设置混合物理机和 VM 的“我的资源”一级入口。
- 物理机管理包含“我的物理机”和“所有物理机”。
- 虚拟机管理包含“我的虚拟机”和“创建虚拟机”。
- “创建虚拟机”使用单张卡片提交 VM 申请：
  - 版本和架构使用下拉选择。
  - 只支持自动安装方式，不支持手动输入镜像 URL。
  - vCPU 默认 2，上限 16。
  - 内存默认 4 GB，上限 32 GB。
  - 额外数据盘数量默认 0，上限 4；每块固定 50 GB。
  - 额外网卡数量默认 0，上限 4。
  - 租期默认 1 天；`ADMIN` 可以填 0 表示永久。
  - 用途默认“飞书申请 VM”。
  - 提交后返回 VM 申请状态卡片；卡片提供手动刷新状态按钮，不自动轮询。
  - VM 创建成功后，刷新状态直接展示 VM 详情和当前用户可见的 SSH 凭据。
  - 同一张创建卡重复提交时按同一个表单处理；Bot 重启后未提交的创建卡需要重新打开。
- Bot 支持查看帮助、查看本人绑定、分页查看我的物理机、分页查看所有物理机、查看
  物理资源详情、分页查看我的 VM、查看 VM 详情、申请 VM 和远程执行命令。
- 物理机管理不做多级筛选抽屉；默认分页展示当前用户占用的物理资源，并提供查看全部入口。
- 物理机列表和详情分别展示管理状态、占用状态和测试状态。测试状态取值为 `idle`、`testing`，
  根据非终态 Test Job 已关联的物理 Env Node 动态计算，不保存为资源台账字段。
- `testing` 状态提供对应 Test Job 的详情入口。测试期间禁止释放或强制释放租约、修改
  资源字段和手动 PXE 重装；允许查看资源与凭据、延长租约。
- 物理资源和 VM 的飞书分页卡片每页展示 5 条。
- 物理资源列表卡片只展示 `OS IP`、`BMC IP`、占用人和详情入口。
- 资源详情卡片展示资源详细信息。
- 资源详情卡片按当前用户权限直接展示可见凭据；无权限时凭据显示为 `***`。
- 资源详情卡片可以进入远程命令执行卡片。
- 远程命令执行卡片展示目标资源、OS IP 和 SSH 用户；打开卡片后，用户直接在同一
  飞书私聊发送命令文本，Bot 按当前待执行资源处理该文本。
- 远程命令执行使用资源保存的 SSH 用户和密码；不要求用户再次输入密码。
- 远程命令执行复用凭据查看权限：`ADMIN` 可以对任意资源执行命令；`TSE` 和 `TE`
  只能对自己当前占用的非关键资源执行命令。
- 不单独识别 `vm-host` 标签；VM 宿主仍按普通物理资源和既有租约权限处理。
- 远程命令允许 shell 语法，命令不能为空，命令长度最多 1000 字符。
- 远程命令同步执行，超时 60 秒，不分配交互式 TTY。
- stdout/stderr 只回传飞书卡片，合计最多展示 8 KB，超过后截断。
- 每次远程命令执行必须写审计日志，记录操作者、目标资源、命令原文、退出码、
  耗时和是否超时；审计日志不保存 stdout/stderr。
- 资源详情卡片可以预留占用、释放等写操作位置，但不展示未实现按钮。
- 我的物理机为空时显示“当前没有占用中的物理机”。
- 我的 VM 为空时显示“当前没有创建中的 VM”。
- 所有物理机为空时显示“没有可显示的物理机”。
- 不在卡片交互里实现复杂资源筛选系统。
- 复杂资源过滤可通过 LLM 自然语言理解扩展，例如按自然语言描述筛选硬件规格。
- 飞书查看凭据沿用现有凭据权限和审计规则，不记录查看行为。
- 不在群聊中返回资源信息或凭据。

密码规则：

- 密码长度至少 8。
- 不要求大小写、数字或特殊字符组合。
- 不做密码过期策略。
- 不做历史密码检查。
- 创建用户、重置密码和用户修改自己的密码使用同一密码规则。

用户列表字段：

- 用户名。
- 显示名。
- 角色。
- 状态。
- 最后登录时间。
- 创建时间。

用户列表默认按创建时间倒序。不做复杂多列排序。用户 ID 默认不在列表展示，密码哈希永不返回前端，PAT 不在用户管理页面展示。

### 我的账号(Account Profile)

- 已登录用户可以修改自己的密码。
- 修改自己的密码必须输入旧密码、新密码和确认密码。
- 用户不能修改自己的用户名。
- 用户不能修改自己的角色。
- 管理员不能通过用户管理给自己重置密码。
- `TE`、`TSE` 和 `ADMIN` 都可以修改自己的密码。
- 该能力与管理员用户管理页面分离。

### 资源池(Resource Pool)

- `ADMIN` 和 `TSE` 可以创建、编辑和停用资源池。
- 资源池只用于分类和筛选。
- 资源池不授予或限制权限。

### 资源(Resource)

- 系统管理 `PHYSICAL` 和 `VIRTUAL` 两类资源。
- 每个资源有内部 UUID `id`。
- 每个资源有公开且不可变的 `resource_code`。
- 物理资源的 `resource_code` 是设备整机 SN。
- 虚拟资源的 `resource_code` 是 VM UUID。
- `ADMIN` 可以通过独立审计操作修正 `resource_code`。
- 资源支持软删除。
- 默认资源列表不显示已软删除资源。
- 默认资源列表按主 IP 自然排序，数字片段按数值比较，例如 `172.168.131.9`
  排在 `172.168.131.10` 前面。

通用资源字段：

- 资源编码。
- 资源类型。
- 显示名，可选。
- 资源池。
- 管理状态。
- 连通状态。
- 占用状态。
- 主 IP，物理资源必填；手动模式创建的虚拟资源可以暂时为空。
- MAC 地址。
- OS 版本。
- 内核版本。
- SSH 账号和加密 SSH 密码。
- 标签。
- 关键资源标记。
- 使用场景。
- 扩展 JSON 字段。

物理资源专属字段：

- 设备位置。
- 设备分布。
- BMC IP。
- BMC 账号和加密 BMC 密码。
- CPU 型号和数量。
- 内存数量和规格。
- HDD 数量和规格。
- SSD 盘数量和规格。
- SSD 卡数量和规格。
- 主板 SN。

虚拟资源专属字段：

- 可选宿主物理资源。
- VM 名称。
- VNC 端口。
- VNC WebSocket 端口。
- vCPU 数量。
- 内存 MB。
- 系统盘 GB。
- 系统盘路径。
- 数据盘数量。
- 数据盘单块容量 GB。
- 数据盘路径列表。

### VM 申请(VM Request)

- `TE`、`TSE` 和 `ADMIN` 都可以申请 VM。
- 用户提交 VM 申请后得到 VM 申请单。
- VM 创建异步执行，API 不在请求线程内等待创建完成。
- VM 登记前回读宿主确认 domain 真实存在（[ADR 0041](../adr/0041-vm-host-fact-reconciliation.md)）；未确认存在则本宿主尝试失败并尝试下一宿主，不登记、不建租约，避免登记宿主机上不存在的 VM。
- VM 申请单记录申请人、规格、租期、用途、状态、错误原因、宿主尝试摘要和创建出的资源。
- VM 申请单状态包括 `pending`、`queued`、`creating`、`succeeded`、`failed`、`cancelled`。
- `pending` 申请可以取消。
- `queued` 和 `creating` 不支持取消。
- `succeeded` 后通过释放 VM 销毁。
- VM 申请使用现有租约规则：`TE` 和 `TSE` 最长 14 天，`ADMIN` 可以永久占用。
- Web VM 申请页租期默认 7 天；`ADMIN` 可勾选永久占用复选框改为永久租约。
- 申请创建的 VM 默认不是关键资源。
- 申请成功后，新 VM 归申请人占用。
- VM 是按需创建的资源，不从长期空闲 VM 台账中复用。
- VM 释放后不回到空闲资源池。

VM 规格：

- 默认规格为 2 vCPU 和 4 GB 内存。
- 用户可以调整 vCPU、内存、额外数据盘数量和额外网卡数量，上限为 16 vCPU 和 32 GB 内存。
- 自动模式系统盘大小由所选 qcow2 镜像的虚拟大小决定，用户不选择系统盘大小。
- 手动模式创建固定 50 GB 空系统盘，并通过 ISO 启动安装。
- 手动模式启动顺序为硬盘优先、ISO 兜底，最终 libvirt XML 显式设置 `hd,cdrom`，
  安装完成后重启应从硬盘启动。
- 支持可选数据盘，用户只选择额外数据盘数量。
- 额外数据盘数量范围为 0 到 4，默认 0。
- 每块数据盘固定 50 GB，不支持用户定制单块容量。
- 额外网卡数量范围为 0 到 4，默认 0；额外网卡与主网卡使用相同的 bridge 和 virtio 模型。
- `arch` 必选。
- VM 申请支持可选换内核：选定 OS 版本、轮次和架构后，可下拉选内核变体（dailybuild
  `*-with-kernel-*` 子目录）或手填 kernel RPM URL 兜底，二选一触发创建时自动换内核；
  都留空则不换内核。Web VM 申请页提供该入口，飞书 Bot 不支持。`kernel_version` 记录
  换内核成功后 `uname -r` 的真实值。
- 换内核为 VM 创建同步后处理：配本地 repo → 精确 `dnf install kernel-<NVR>` → reboot →
  等 SSH 回来 → `uname -r` 验证新内核生效。失败（repo 不可达、包不存在、install 失败、
  uname 不匹配）即销毁刚建的 VM 并标记申请失败，与 `-64k` 后处理语义一致。用户显式换
  内核优先于 `os_version` 的 `-64k` 后缀，两者互斥。

VM 镜像选择：

- Web VM 申请页支持安装方式选择：自动和手动。
- 飞书 Bot 创建 VM 只支持自动模式，不支持手动输入镜像 URL。
- 自动模式下，用户从后端解析出的镜像列表中选择发行版、OS 版本、轮次和架构。
- 当前默认发行版为 `openEuler`。
- 镜像来自内网 HTTP 目录索引。
- 镜像仓库层级为 `<dist>/<os_version>/<round>/<arch>/`。
- 每个镜像目录只识别固定文件名 `<os_version>-<arch>.qcow2`。
- 镜像发现结果使用短时内存缓存，默认 5 分钟，不写入数据库。
- 自动模式提交 VM 申请时，后端重新校验所选镜像仍然存在。
- 手动模式下，用户输入 ISO URL，并输入发行版、OS 版本和轮次。
- 手动模式的 ISO URL 输入框旁提供本地 ISO 上传按钮；上传完成后自动填入生成的 URL，
  URL 仍可手动修改。
- 所有已登录用户均可上传 ISO。原始文件名必须以 `.iso` 结尾，最长 255 字符，不能包含
  路径分隔符或控制字符；单个文件最大 20 GB。
- 上传时展示进度；上传期间禁止提交 VM 申请、切换文件或关闭申请弹窗，刷新、关闭页面
  或离开路由前显示浏览器确认提示。
- 用户确认离开、网络断开或上传失败后，本次上传终止；平台清理临时文件，用户需要重新
  上传完整文件，不支持断点续传。
- 上传成功后生成当前环境的内网 HTTP URL。该下载 URL 不要求登录，供 VM 宿主直接下载。
- 上传文件的磁盘路径只使用平台生成的临时名和内容 SHA-256，不使用原始文件名。下载响应
  固定为附件并禁止 MIME sniff；radiaTest 不解析、解压或执行 ISO 内容。
- 相同内容按 SHA-256 去重。完整 ISO 保留 30 天，异常残留的临时文件保留 24 小时；
  后续上传触发懒清理，不提供 ISO 管理页面或手动删除功能。
- 手动模式的发行版、OS 版本和轮次输入框默认空，placeholder 分别为 `dist`、
  `version`、`round`；发行版和 OS 版本必填，轮次可选。
- 手动模式不要求 URL 出现在镜像发现结果中；后端只做基本 URL 格式校验。
- 手动 URL 只允许 HTTP/HTTPS，不限制域名或 IP 网段。
- 手动模式仍然需要选择架构；架构不从 URL 自动推断。
- 手动模式轮次为空时，VM 名称和实例盘名称省略轮次片段。
- VM 名称时间戳按 `DISPLAY_TIMEZONE` 生成，默认 `Asia/Shanghai`，格式为
  `YYYYMMDDTHHMMSS`，不带 `Z` 后缀。
- 飞书卡片里的时间按 `DISPLAY_TIMEZONE` 展示。
- 手动模式 ISO 缓存文件名只包含 URL 短哈希，避免同一 URL 因展示字段变化而重复下载。
- 宿主机缓存目录 `/var/lib/libvirt/images/kronos/cache/` 只保存源 qcow2 和手动 ISO；
  每次创建 VM 时机会式清理该目录下超过 30 天且未被 libvirt domain XML 引用的缓存文件，
  不清理 `instances/` 或其他 libvirt 镜像目录，不引入定时器或独立清理服务。
- 镜像服务返回 `Content-Length` 时，宿主脚本在下载前检查
  `/var/lib/libvirt/images` 所在文件系统是否满足下载大小和 10 GB 缓冲；拿不到
  `Content-Length` 时不阻塞下载。
- VM 申请单保存 `install_type`，取值为 `auto` 或 `manual`。
- VM 申请记录列表和详情展示安装方式和 `image_url`，不提供安装方式筛选。

VM 宿主选择和创建：

- VM 宿主是 `PHYSICAL` 资源，使用 `vm-host` 标签标记。
- VM 宿主应由 `ADMIN` 永久占用，避免作为普通测试资源发放。
- radiaTest 只按资源类型、管理状态、`vm-host` 标签和 `arch` 字段筛选候选宿主。
- 没有填写 `arch` 的宿主不参与自动创建 VM。
- radiaTest 不维护独立宿主容量字段，也不从硬件描述字段推导可分配容量。
- 宿主机脚本实时检查 CPU、内存和 `/var/lib/libvirt/images` 所在文件系统的磁盘剩余容量。
- 候选宿主容量不足时，radiaTest 尝试下一个候选宿主。
- 所有候选宿主都失败时，VM 申请单状态为 `failed`。
- 流水线 VM 创建按宿主机并发控制 + 负载均衡：`process_vm_request`（`serialize_per_host=True` 时）遍历同架构候选宿主，对每个宿主先尝试非阻塞锁（`fcntl.flock LOCK_NB`，[ADR 0025](../adr/0025-vm-create-per-host-serialization.md)）；拿到锁则选定该宿主执行 `create-vm.sh`，没拿到则跳到下一个候选宿主。所有候选宿主所有槽位都忙时，回到第一个候选宿主阻塞等待并记录 `queued` 事件，申请单状态显示"等待创建"。并发数由 `settings.vm_max_concurrent_per_host`（默认 4）控制，通过 `VM_MAX_CONCURRENT_PER_HOST` 环境变量配置。所有槽位忙时轮询而非阻塞在单个文件。手动 VM 申请不受此限制。
- 手动刷新 VM 申请列表或申请事件时，超过 60 分钟仍处于 `creating` 或已开始后等待
  宿主并发槽位的 `queued` 申请会被
  标记为 `failed`，错误码为 `stale_creating`；该判断不连接宿主机清理资源。
- VM 创建脚本必须尽量保证全成或全退；没有完整满足安装方式对应的成功条件时，
  应回滚已创建的 domain、实例盘、数据盘和缓存下载 `.part`。
- 回滚失败时，VM 申请单状态为 `failed`，并记录需要管理员处理的错误。
- 自动模式创建完成前必须拿到 DHCP IP，并确认 VM 的 22 端口可连接。
- 手动模式创建完成前只要求 libvirt domain 已启动并能读取 VNC 端口，不等待用户完成系统安装或 SSH 可连接。

VM 展示和访问：

- VM 列表优先展示 VM 名称、OS IP 和 VNC，随后展示架构、OS 版本、规格、
  租约期限等信息。
- VM 详情展示 MAC 地址。
- 当前占用人和 `ADMIN` 可以在 VM 详情中手动刷新 OS IP。
- 刷新 OS IP 时，后端按 VM MAC 地址读取 DHCP 租约(DHCP Lease)并更新资源 `primary_ip`。
- DHCP 租约不是 radiaTest 资源租约(Resource Lease)，刷新 OS IP 不改变占用关系或租约期限。
- 未找到 DHCP 租约时，不清空已有 OS IP。
- VM 详情展示实时电源状态，并提供手动刷新状态按钮。
- 当前占用人和 `ADMIN` 可以在 VM 详情中发送启动、关机和重启命令。
- VM 电源操作通过宿主机 `virsh` 同步执行，不自动轮询状态；用户需要手动刷新状态。
- VM 电源操作写审计日志，记录操作者、目标 VM、宿主和操作后的电源状态。
- VM 创建时保留传统 VNC 端口，并额外保存 VNC WebSocket 端口。
- Web VNC 控制台在应用内打开与虚拟机管理平级的独立 Tab，不嵌入 VM 详情抽屉。
- Web VNC 控制台 Tab 标题优先展示传统 VNC 地址，例如 `172.168.131.92:5924`。
- Web VNC 控制台使用 noVNC 直接连接宿主机暴露的 VNC WebSocket 地址；radiaTest 后端
  不代理 VNC 图像流。
- Web VNC 控制台当前使用 `ws://<host>:<vnc_websocket_port>/`，不配置 `wss://` 或证书。
- Web VNC 控制台不设置独立 VNC 密码。
- Web VNC 控制台入口权限与 VM 凭据查看一致：`ADMIN` 可以打开任意 VM 控制台，
  `TE` 和 `TSE` 只能打开自己当前占用的 VM 控制台。
- 没有 VNC WebSocket 端口的旧 VM 不做自动迁移；用户点击打开控制台时返回未配置错误。
- Web VNC 控制台只支持 VM，不支持物理机 BMC KVM 控制台。
- Web VNC 控制台提供浏览器全屏按钮。
- Web VNC 控制台提供 `Ctrl+Alt` 组合键下拉发送控件，支持 F1-F6 和 Del，默认 F2。
- Web VNC 控制台打开或断连时按需查询一次 VM 电源状态，并复用状态标签显示“已关机”、
  “已销毁”或“已断开”；不增加后台轮询。
- 手动安装 VM 在安装器内触发重启时，libvirt domain 应重新启动，不应变为关闭状态。
- 申请记录展示申请状态，并提供详情入口查看错误原因、宿主尝试摘要和任务事件。
- 任务事件用于展示异步创建过程中的入队、worker 领取、宿主选择、宿主连接、
  宿主脚本阶段摘要、可复现的宿主外部命令、成功和失败等信息。
- VM 申请详情页默认隐藏低价值成功宿主命令，保留 `virsh`、`qemu-*`、`virt-install`
  等虚拟化关键命令，以及阶段摘要、失败命令、命令输出和错误。
- 任务事件不包含凭据或敏感 payload。
- Worker 应在宿主脚本运行中读取阶段事件并按生成顺序增量落库；任务事件页面使用手动刷新，
  不提供实时日志流。
- SSH 密码仍通过现有凭据查看 API 获取。
- 传统 VNC 继续展示宿主 IP 和端口，作为外部 VNC 客户端备用入口。
- radiaTest 不提供后端 Web VNC 图像流代理。

### 状态规则

- `management_status` 取值：`active`、`maintenance`、`disabled`。
- `connectivity_status` 取值：`unknown`、`reachable`、`unreachable`。
- `occupancy_status` 取值：`idle`、`occupied`、`expired`。
- 只有 `active` 且 `idle` 的资源可以被占用。
- `maintenance` 和 `disabled` 资源不能被任何角色占用。
- `ADMIN` 可以修改管理状态。
- `TSE` 只能编辑 active 资源，且不能编辑被别人占用的资源。

### 租约(Lease)

- 用户可以无需审批地占用 active idle 资源。
- 同一资源同时最多只有一个有效租约。
- 创建租约时记录用途、开始时间、预计结束时间和操作者。
- 租约用途必填。
- `TE` 和 `TSE` 的租约必须是有限期，最长 14 天；接口校验允许最多 1 分钟的提交时间误差，不改变租期上限。
- `ADMIN` 可以创建有限期或永久租约。
- 有限期租约只能由租约所有者续期。
- 续期目标时间必须晚于当前租约截止时间，且最晚为当前时间 7 天后；接口校验允许最多 1 分钟的提交时间误差。
- 永久租约不需要续期。
- `TE` 和 `TSE` 可以释放自己的租约。
- `TSE` 可以强制释放 `TE` 租约。
- `TSE` 不能强制释放 `ADMIN` 或其他 `TSE` 租约。
- `ADMIN` 可以强制释放任何租约。
- 租约操作应在适用场景使用 `lease_id`。
- 使用懒释放处理过期租约。
- 懒释放在资源列表/详情、占用、释放、续期和凭据查看前执行。
- VM 到期释放触发异步销毁任务。
- VM 销毁成功后才释放租约并软删除对应虚拟资源。
- VM 销毁对宿主连接类瞬时失败（如并发 SSH 超出 sshd `MaxStartups` 被重置）做有限次退避重试；重试事件追加记录（[ADR 0041](../adr/0041-vm-host-fact-reconciliation.md)）。
- VM 销毁脚本失败后回读宿主实际状态：确认 VM 与磁盘均已不存在时按宿主事实自动完成销毁落账（自动释放租约并软删除资源，事件注明收敛来源）；确认仍存在或回读失败时记销毁失败，事件携带宿主实际状态，不释放租约，VM 继续显示为需要处理，可再次触发释放（销毁脚本幂等续删）。
- VM 销毁中断的恢复同样先回读宿主：确认消失才落账收敛，仍存在则清除执行锁保持可重试，不自动删除 VM。
- 有期限租约按[通知管理规格](0004-notification-management.md)在到期前 3 天每天提醒当前占用人。

### 凭据(Credential)

- 物理资源必须有主 IP 和 SSH 凭据。
- 自动模式创建的虚拟资源保存默认 SSH 凭据。
- VM 创建出的虚拟资源默认保存 SSH 账号 `root` 和密码 `openEuler12#$`；自动和手动安装方式一致。
- 物理资源必须有 BMC 凭据。
- 虚拟资源没有 BMC 凭据。
- 凭据使用应用密钥加密保存。
- 凭据只能通过独立 API 查看。
- 凭据查看不写审计日志。
- 凭据新增、修改和清除写审计日志。
- 远程命令执行复用凭据查看权限，但执行行为必须写审计日志。
- 前端详情页按权限展示凭据；无权限时显示为 `***`，有权限时通过独立凭据接口获取明文。
- 前端不能持久化凭据明文。
- 关键资源只能由 `ADMIN` 占用。
- 关键资源凭据只能由 `ADMIN` 查看。

### 导入导出(Import/Export)

- 资源导入和租约导入支持 CSV。
- 租约导入依赖资源已存在，通过 `resource_code` 关联资源。
- 迁移旧平台数据时，先导入资源，再导入当前租约。
- 表格格式扩展为 XLSX 时，必须复用 CSV 的字段语义、校验、预览和提交流程。
- 导入仅 `ADMIN` 可用。
- 导入在提交前校验必填字段和唯一性。
- 物理资源导入必须提供设备整机 SN，缺失时该行校验失败。
- 导入支持写库前预览。
- 导入确认要求 `Idempotency-Key`。
- 导入结果按行返回成功和错误信息，不返回凭据明文。
- 未知列可以存入 `extra`。
- 导出支持 CSV。
- 不支持 XLSX 导出。
- 导出仅 `ADMIN` 可用。
- 导出包含 SSH/BMC 密码明文。
- 每次导出写审计日志，审计详情不包含密码明文。

### 过滤和搜索

- 资源列表支持后端分页。
- 资源列表支持选定通用字段、类型专属字段和当前租约字段的逐列文本模糊过滤。
- 资源列表过滤覆盖管理状态、占用状态、占用人、占用用途和使用场景。
- 资源列表和资源详情分别展示占用用途和使用场景，不合并两类文本。
- 多个过滤条件支持 `AND` 和 `OR` 模式。
- 在可行范围内，过滤大小写不敏感。
- 不支持 `extra` 字段过滤。

### 列表分页

- VM 列表、VM 申请记录、审计日志和租约日志使用服务端分页。
- 列表请求使用从 `1` 开始的 `page`，每页固定 50 条，不提供每页数量选择。
- 分页响应统一包含 `items`、`total`、`page` 和固定值 `50` 的 `page_size`。
- `total` 为应用当前权限和筛选条件后的记录总数。
- 页码超过最后一页时返回空 `items`，不自动改写页码。
- 筛选条件变化或重置后回到第 1 页。
- VM 列表和 VM 申请记录两个 Tab 分别维护页码。
- 各列表保留现有固定业务排序，并使用记录 ID 作为稳定次级排序键；不提供通用排序参数或表头排序。

### 连通性检查(Connectivity Check)

- 能查看资源的用户可以触发按需连通性检查。
- 检查主 IP ping 和 SSH 端口可达性。
- 连通性检查更新连通状态、上次检查时间和摘要。
- 连通性检查不改变占用状态。
- 不包含持续监控或告警。

### 日志

- 审计日志覆盖登录、用户管理、资源变更、导入导出、凭据修改、远程命令执行和其他敏感操作。
- 租约日志覆盖占用、续期、释放、自动释放和强制释放。
- 任务事件覆盖 VM 创建、VM 销毁、Mugen 同步和测试任务等异步流程。
- 任务事件默认保留 30 天；超过保留期后可以清理。
- VM 销毁成功后记录对应释放事件；销毁失败记录在虚拟资源错误信息中。
- 审计日志和租约日志归入“日志”一级菜单下的独立页面，不混入资源详情页。
- 租约日志展示资源类型、当前 OS IP 和资源编号，资源类型区分物理机与虚拟机。
- 审计日志页面仅 `ADMIN` 可用。
- 审计日志页面展示时间、操作者、操作类型、目标类型、目标 ID 和详情摘要。
- 审计日志页面支持按操作类型、操作者用户名、目标类型和时间范围过滤。
- 审计日志页面支持查看完整详情 JSON。
- 审计日志页面不支持新增、编辑、删除或导出。
- `ADMIN` 查看全部审计日志和租约日志。
- `TSE` 查看全部租约日志，不能访问审计日志页面。
- `TE` 查看自己的租约日志，不提供审计日志页面。
- 虚拟资源的租约日志提供任务事件入口，VM 软删除后仍可回看销毁过程。

### 仪表盘(Dashboard)

- 包含极简 Dashboard。
- Dashboard 展示资源按管理状态、连通状态和占用状态的数量。
- Dashboard 展示当前用户的有效租约和即将到期租约。
- 不包含趋势报表或大屏。

### 物理机 PXE 安装(Physical Machine PXE Install)

物理机 PXE 安装是原子能力，不集成 test job 编排。手动重装只选择并安装基础 PXE 镜像，
不提供 `-64k` 目标版本；Test Job 可在调用该能力时传递自身目标版本，并在基础安装后执行
受支持的内核后处理。安装源一律使用本地 OS 树（见 ADR 0040），不再向 PXE 服务器下载
整份 ISO；内核差异收敛为"装后换内核"。决策见 ADR 0014、ADR 0024、ADR 0038、ADR 0040。

#### 安装镜像模型

`physical_install_images` 表：`os_version`、`arch`（`aarch64`/`x86_64`）、`round`、
`kernel_variant`、`efi_url`（grub EFI 本地 URL）、`repo_url`（本地 repo 根，其下需有
`images/pxeboot/{vmlinuz,initrd.img}`）、`iso_url`（仅展示/兜底，不作为安装源）、
`swap_kernel_variant`（非空 = 装基础树后换内核到该变体）。

- RC 行的 `repo_url`/`efi_url` 由**登记扫描**（`install_sources`）按 94 本地
  `iteration.repo` 目录回填：变体自身 OS 树存在 → 指该树（直装，`swap_kernel_variant=NULL`）；
  变体树缺失 → 指 base 变体树 + 记录 `swap_kernel_variant`；base 树缺失 → 不登记（不可装）。
- `install_image_base_variants` 表存各发行版 base 内核变体（如 DevStation→6.6），前端
  ADMIN 可编辑，seed 默认。
- official 行（如 24.03-LTS-SP4）仍为 `efi_url`+`repo_url`，不经登记。

#### PXE 服务器

纳管为 `pxe-host` 标签的 PHYSICAL 资源（类比 `vm-host`），由 ADMIN 永久占用。PXE 服务器
就是现有 DHCP 服务器（`VM_DHCP_LEASES_URL` 指向的机器），同时承担 dhcpd/tftp/httpd 角色。
worker 通过 `run_host_script` 操控 PXE 服务器（复用现有宿主脚本契约 + `KRONOS_EVENT` 协议）。

#### 装机流程（单次 Celery 任务）

1. **采集网卡**：装机前（旧系统 SSH 可达）读取 `/sys/class/net/*/address` 全部 MAC。
2. **sync boot files**：worker 调 `run_host_script` 到 PXE 服务器 → 优先 official
   （`efi_url`+`repo_url`；rsync/wget pxeboot 到 tftp）→ 生成 ks（替换 `{os_repo}`、
   `{os_marker}` 占位符；`%post` 写 `/root/.kronos-install-marker`=`<os> <round>`）→
   生成 grub.cfg → 返回 EFI 相对路径。事件 `pxe_sync_files`。
3. **bind dhcp**：同一 PXE 服务器脚本内 → 备份 dhcpd.conf → 清理该 IP 旧绑定 →
   对**全部网卡 MAC** 追加 `host{filename,mac,ip}` → `systemctl restart dhcpd`
   （失败回滚 .bak）。事件 `pxe_bind_dhcp`。
4. **ipmi boot**：worker 容器内直连目标 BMC → `ipmitool chassis bootdev disk
   options=persistent && chassis bootdev pxe options=efiboot && power reset`。事件
   `pxe_ipmi_boot`。
5. **installing**：worker 循环 SSH 到目标 IP（每 10 秒，最长 30 分钟），用固定密码
   `openEuler12#$` 等待装机。事件 `pxe_installing`。
6. **校验**：SSH 通后校验 `os-release` 含目标版本 + `install-marker` 轮次一致；
   不符 → `pxe_failed`、恢复 `active`、**不回写 os_version**。事件 `pxe_verifying`。
7. **写回/换内核**：校验通过 → 回写 `ssh_password_ciphertext`（`openEuler12#$`）与
   `os_version`；`swap_kernel_variant` 非空 → 换内核（dailybuild 变体 repo，`uname -r`
   校验），失败宽容（保留基础系统、事件注明来源）。
8. **收尾**：best-effort 硬件探测回填；`management_status` 恢复 `active`；事件
   `pxe_finished`（成功）或 `pxe_failed`。

#### root 密码

固定默认 `openEuler12#$`（和 VM 默认一致）。ks 模板用对应 `rootpw --iscrypted` hash。验收后加密写入 `ssh_password_ciphertext`。不在任何文件存明文。

#### ks 模板

通用模板，`network --bootproto=dhcp` 不指定 `--device`，一套适配所有硬件。模板选择优先级：`{os_name}-{os_version}-ks.template` > `{os_name}-ks.template` > `common-ks.template`。

#### 进度跟踪

只用 `task_events`（`pxe_sync_files`/`pxe_bind_dhcp`/`pxe_ipmi_boot`/`pxe_installing`/`pxe_verifying`/`kernel_swap_*`/`pxe_finished`/`pxe_failed`）。资源 `management_status` 装机期间设 `maintenance`。不新建装机请求表。

#### 权限和入口

- `POST /api/v1/resources/{id}/install`（ADMIN only），body `{ "image_id": "..." }`。
  后端校验 `image.arch == resource.arch`，不符返回 400。
- 前端物理机详情页"重装系统"按钮：版本→轮次→内核三级；按机器架构过滤；轮次只列
  有安装源的行；内核项徽标 `[本地直装]` / `[装<base>+换内核]`；无源行不展示不可选。
- `GET /api/v1/resources/install-images`：先返回 DB 已有行，dailybuild 发现与本地登记
  在后台线程刷新（≤5 分钟节流）。
- `GET/PUT /api/v1/resources/install-image-base-variants`（ADMIN only）：读取/设置发行版
  base 内核变体。
- 前端物理机详情抽屉"刷新硬件"按钮（ADMIN + PHYSICAL + 有 `primary_ip`），触发
  `POST /api/v1/resources/{id}/probe` 同步 SSH 探测硬件回填。
- `POST /api/v1/resources/{id}/probe`（ADMIN only）：一次 SSH 跑 `lscpu`/`dmidecode`/`lsblk`/`uname`，解析后回填 `arch`/`kernel_version` + `cpu_model`/`cpu_count`/`memory_count`/`memory_spec`/`hdd_count`/`hdd_spec`/`ssd_count`/`ssd_spec`/`ssd_card_count`/`ssd_card_spec`/`board_sn`（探测值非 None 覆盖，`os_version` 不覆盖）。探测失败返回 502。
- 重装成功后自动 best-effort 探测回填（同字段，失败不阻断重装）。
- 目标资源必须是 PHYSICAL 类型、有 `bmc_ip`/`bmc_username`/`bmc_password_ciphertext`/`mac_address`/`primary_ip`。
- 装机期间资源不可被租约占用。

## API 需求

- API 前缀为 `/api/v1`。
- REST API 暴露与 Web 前端一致的业务能力。
- 后端生成 OpenAPI 文档。
- 错误响应和请求追踪遵循[平台运行时规格](./0005-platform-runtime.md)。
- 关键写接口要求 `Idempotency-Key`：
  - 占用。
  - 释放。
  - 续期。
  - 强制释放。
  - VM 申请。
  - VM 释放。
  - VM 电源操作。
  - 导入确认。
- 使用相同 idempotency key 和相同请求时，返回第一次响应。
- 使用相同 idempotency key 但参数不同时，返回稳定冲突错误。
- 已完成的幂等记录是短期缓存，默认保留 7 天；处理中记录不自动删除。
- `POST /api/v1/leases/{lease_id}/extend` 续期当前用户自己的有效有限期租约：
  - 需要 `Idempotency-Key`。
  - `expected_ends_at` 必须晚于当前租约截止时间。
  - `expected_ends_at` 按上述续期规则校验。
- `GET /api/v1/vm-images` 获取可申请 VM 镜像列表。
- `POST /api/v1/vm-requests` 提交 VM 申请：
  - 需要 `Idempotency-Key`。
  - 通过 `install_type` 区分自动和手动安装方式；不传时默认为 `auto`。
  - `auto` 模式要求 `dist`、`os_version`、`image_round` 和 `arch` 必填，后端重新查找镜像并写入实际 `image_url`。
  - `manual` 模式要求 `dist`、`os_version`、`arch` 和 ISO `image_url` 必填，`image_round` 可选。
  - `manual` 模式不调用镜像发现校验，后端只校验 `image_url` 为 HTTP/HTTPS URL。
  - 返回 VM 申请单。
  - 后端异步创建 VM。
- `POST /api/v1/vm-isos` 上传本地 ISO：
  - 要求登录，使用原始二进制请求体流式上传，不使用 multipart 临时文件。
  - 查询参数 `filename` 传原始文件名，请求体使用 `application/octet-stream`，并要求
    `Content-Length`；后端同时按实际接收字节校验大小。
  - 文件最大 20 GB；空间不足、磁盘使用率达到保护阈值或连接中断时失败并清理临时文件。
  - 返回相对下载 URL、SHA-256 和文件大小；前端使用当前站点 origin 生成完整 URL。
  - 上传成功写审计日志。
- `GET /api/v1/vm-requests` 获取 VM 申请单列表：
  - 默认只看当前用户。
  - 可以切换查看全部。
  - 使用统一分页响应。
- `GET /api/v1/vm-requests/{request_id}/events` 获取 VM 申请任务事件：
  - 返回脱敏事件时间线。
  - 宿主命令失败时，错误信息包含触发失败命令的有限 stderr 摘要。
  - 创建失败仍自动回滚；回滚前可以记录有限的 libvirt domain 诊断摘要。
  - 不需要 `Idempotency-Key`。
- `GET /api/v1/vms` 获取 VM 列表：
  - 默认只看当前用户申请的 VM。
  - 可以切换查看全部。
  - 支持 `search` 查询参数：对 name、primary_ip、os_version、arch、resource_code、management_status 做大小写不敏感模糊匹配（Python 层 `in` 过滤），受 `show_all` 约束（关闭时只搜自己的 VM）。
  - 使用统一分页响应。
- `GET /api/v1/vms/{resource_id}/events` 获取 VM 资源任务事件：
  - 当前用于查看销毁任务事件。
  - VM 资源软删除后仍可查询保留期内的销毁任务事件。
  - 不需要 `Idempotency-Key`。
- `GET /api/v1/vms/{resource_id}/power` 获取 VM 实时电源状态：
  - 当前占用人和 `ADMIN` 可调用。
  - VM 已软删除时返回 `power_state=destroyed`，供已打开的控制台识别销毁状态。
  - 不需要 `Idempotency-Key`。
- `POST /api/v1/vms/{resource_id}/power` 执行 VM 电源操作：
  - 当前占用人和 `ADMIN` 可调用。
  - `action` 取值为 `start`、`shutdown` 或 `reboot`。
  - 需要 `Idempotency-Key`，相同请求重试不重复执行宿主命令。
- `POST /api/v1/vms/{resource_id}/refresh-ip` 按 MAC 地址刷新 VM 的 OS IP：
  - 当前占用人和 `ADMIN` 可调用。
  - 从配置的 DHCP 租约地址读取最新租约。
  - 找到 IP 时更新 `primary_ip` 并返回 VM 资源。
  - 找不到 IP 时返回错误，不清空原 IP。
  - 不需要 `Idempotency-Key`。
- `GET /api/v1/vms/{resource_id}/console` 获取 Web VNC 控制台配置：
  - 权限与 VM 凭据查看一致。
  - 返回完整 WebSocket URL、传统 VNC 端口、VNC WebSocket 端口和密码字段。
  - `password` 当前固定为 `null`。
  - 没有 VNC WebSocket 端口时返回 409。
  - 不需要 `Idempotency-Key`。
- `GET /api/v1/audit-logs` 获取审计日志列表：
  - 仅 `ADMIN` 可调用。
  - 支持按 `action`、`actor_username`、`target_type`、`started_at` 和 `ended_at` 过滤。
  - 返回操作者用户名、操作类型、目标类型、目标 ID、详情 JSON 和创建时间。
  - 使用统一分页响应。
  - 不需要 `Idempotency-Key`。
- `GET /api/v1/lease-events` 获取租约日志列表：
  - `ADMIN` 和 `TSE` 查看全部，`TE` 只查看自己的租约日志。
  - 支持按 `event_type`、`actor_username`、`resource_type`、`primary_ip`、
    `resource_code`、`started_at` 和 `ended_at` 过滤。
  - 系统自动释放事件的操作者为空，前端显示为“系统”。
  - 使用统一分页响应。
  - 不需要 `Idempotency-Key`。
- `GET /api/v1/integrations/feishu/app` 获取当前环境飞书应用配置：
  - 仅 `ADMIN` 可调用。
  - 不返回 `app_secret` 明文。
- `PUT /api/v1/integrations/feishu/app` 创建或更新当前环境飞书应用配置：
  - 仅 `ADMIN` 可调用。
  - 写入 `app_id`、`app_secret` 和启用状态。
  - 响应不返回 `app_secret` 明文。
  - 写审计日志，审计详情不包含 `app_secret` 明文。
- `GET /api/v1/integrations/feishu/me/identity` 获取当前用户飞书身份绑定：
  - 返回当前用户绑定的 `open_id` 和可用时的 `union_id`。
  - 未绑定时返回空值。
- `GET /api/v1/integrations/feishu/me/bind-url` 获取当前用户飞书绑定授权链接：
  - 需要当前 radiaTest 用户已登录。
- `GET /api/v1/physical-install-images` 获取物理机安装镜像列表：
  - 仅 `ADMIN` 可调用。
  - 返回 `os_version`/`arch`/`efi_url`/`repo_url`。
- `POST /api/v1/physical-install-images` 创建物理机安装镜像：
  - 仅 `ADMIN` 可调用。
  - 需要 `Idempotency-Key`。
- `DELETE /api/v1/physical-install-images/{id}` 删除物理机安装镜像：
  - 仅 `ADMIN` 可调用。
- `POST /api/v1/resources/{resource_id}/install` 触发物理机 PXE 安装：
  - 仅 `ADMIN` 可调用。
  - Body: `{ "image_id": "..." }`。
  - 目标必须是 PHYSICAL 类型，有 BMC/MAC/IP 凭据。
  - 资源 `management_status` 设 `maintenance`，异步执行装机。
  - 需要 `Idempotency-Key`。
  - 请求参数 `redirect_uri` 必须指向当前环境的飞书 OAuth 回调 API。
  - 响应只返回飞书授权 URL。
- `GET /api/v1/integrations/feishu/oauth/callback` 处理飞书 OAuth 回调：
  - 校验 `state` 后换取飞书用户信息。
  - 绑定当前 radiaTest 用户与飞书 `open_id`/`union_id`。
  - 不保存飞书访问令牌。
  - 完成后跳回账号页并携带绑定结果。
- `POST /api/v1/vms/{resource_id}/release` 释放 VM：
  - 需要 `Idempotency-Key`。
  - 触发异步销毁任务。
- `POST /api/v1/resources/imports` 导入资源 CSV：
  - `dry_run=true` 时只校验并返回逐行结果，不写库。
  - `dry_run=false` 时创建校验通过的资源行。
  - 导入确认需要 `Idempotency-Key`。
  - 返回总行数、成功行数、失败行数和逐行结果。
- `GET /api/v1/resources/exports` 导出资源 CSV：
  - 仅 `ADMIN` 可调用。
  - 复用资源列表过滤条件。
  - 导出 SSH/BMC 密码明文。
  - 每次导出写审计日志，审计详情不包含密码明文。
- `POST /api/v1/leases/imports` 导入当前租约 CSV：
  - 使用 `resource_code` 查找资源。
  - 使用 `lease_owner` 查找本地用户。
  - `lease_type=permanent` 且 `expected_ends_at` 为空表示永久租约。
  - 导入确认需要 `Idempotency-Key`。
  - 返回总行数、成功行数、失败行数和逐行结果。

## 页面

页面：

- 登录。
- Dashboard。
- 物理机管理。
- 虚拟机管理。
- 资源详情。
- 物理机资源编辑。
- 资源新增。
- 资源池。
- 用户管理。
- PAT 管理。
- 导入导出。
- 审计日志。
- 租约日志。

物理机管理页面：

- 默认展示当前用户占用的物理资源。
- 提供切换查看全部的按钮。
- 资源详情展示 SSH/BMC 账号和密码；无权限查看密码时显示 `***`。

虚拟机管理页面：

- 包含 VM 列表和申请记录两个 Tab。
- 默认展示当前用户申请的 VM 和申请单。
- 提供切换查看全部的按钮。
- 只有释放和强制释放按租约规则限制；查看范围不按角色限制。
- VM 列表提供新增 VM 入口。
- VM 详情展示 MAC、SSH 账号和密码；无权限查看密码时显示 `***`。
- 具备资源编辑权限的用户可以在 VM 详情中修改 SSH 密码。
- VM 详情的 OS IP 后提供手动刷新按钮，按 MAC 从 DHCP 租约更新 OS IP。
- VM 详情提供打开 Web VNC 控制台的入口。
- Web VNC 控制台使用应用内独立 Tab，包含全屏按钮和 `Ctrl+Alt` 组合键下拉发送控件。
- 申请记录提供申请详情入口，用于查看状态、错误原因、宿主尝试摘要和任务事件。
- 申请成功后，申请详情提供跳转到对应 VM 详情的入口。

## 非目标(Non-Goals)

资源管理功能不包含：

- OAuth 或 SSO。
- Web 自助注册。
- 测试用例管理，见 [Spec 0002：测试管理功能规格](./0002-test-management.md)。
- 测试任务管理，见 [Spec 0002：测试管理功能规格](./0002-test-management.md)。
- 物理机电源控制。
- 交互式远程终端。
- radiaTest 后端 Web VNC 图像流代理。
- VM 镜像管理页面。
- 上传 ISO 的恶意内容扫描、镜像签名验证或文件系统内容解析。
- 持续监控或告警。
- 多租户组织权限。
- Kubernetes 部署。

## 验收标准(Acceptance Criteria)

- 新成员可以按运行手册部署远程 Linux `dev` 环境，执行后端迁移，并用 CLI 创建的管理员账号登录。
- `ADMIN` 可以在 Web 用户管理页创建 `te1` 和 `tse` 用户。
- `te1` 和 `tse` 可以使用管理员设置的密码登录。
- `TE` 和 `TSE` 看不到用户管理菜单，直接访问用户管理页面时显示无权限。
- `TE` 和 `TSE` 调用用户管理 API 返回 403。
- `ADMIN` 可以修改用户显示名、角色和启用状态。
- `ADMIN` 可以重置其他用户密码。
- `ADMIN` 不能禁用自己，不能把自己的角色改为 `TSE` 或 `TE`。
- 系统不能禁用或降级最后一个启用的 `ADMIN`。
- 用户管理操作写入审计日志，且不记录密码。
- 用户可以修改自己的密码。
- CLI `create-admin` 仍可用于创建第一个管理员。
- `ADMIN`、`TSE`、`TE` 权限有自动化后端测试覆盖。
- 可以创建并列出一台物理资源和一台虚拟资源。
- `ADMIN` 可以在 Web 物理机管理页新增物理资源。
- `TE`、`TSE` 和 `ADMIN` 可以提交 VM 申请。
- 已登录用户可以在手动安装表单上传不超过 20 GB 的本地 ISO，并用返回 URL 提交 VM
  申请；原始文件名不会影响服务器磁盘路径。
- 刷新页面、离开路由或网络断开会终止上传，临时文件不能通过下载地址访问，并按规则
  立即或懒清理。
- VM 申请异步执行，完成后生成虚拟资源和有效租约；登记前回读宿主确认 VM 真实存在。
- VM 申请详情能查看脱敏任务事件，用于定位创建失败或卡住的阶段。
- VM 释放会销毁 VM；销毁成功（含回读宿主确认消失后的收敛落账）后释放租约并软删除虚拟资源。
- VM 管理默认只展示当前用户的 VM 和申请单，并支持切换查看全部。
- 非关键的 active idle 资源可以按角色规则被占用、查看凭据、续期、释放和强制释放。
- `TSE` 和 `TE` 不能占用或查看关键资源凭据。
- 过期租约会在相关操作前被懒释放。
- CSV 导入预览会在提交前校验资源行和租约行。
- 资源导出会写审计日志，审计详情不包含密码明文。
- 自动化测试使用隔离测试数据，不连接 `kronos_dev` 或 `kronos_prod`；需要 PostgreSQL 集成测试时，通过 `TEST_DATABASE_URL` 指向独立测试库。
