<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Spec 0002：测试管理功能规格(Test Management)

## 状态

有效(Active)。

## 目标

radiaTest 提供基于 VM 的 Mugen **普通测试任务**能力。用户可以同步 Mugen 用例索引、筛选并选择 suite/case，创建自动化测试任务，平台自动创建 VM 环境、执行用例、记录 case 结果并按规则销毁或保留环境。Pipeline 在其内部创建物理或 VM TestJob 的编排规则由 [测试流水线功能规格](0003-test-pipeline.md) 定义，不改变本规格中普通测试任务 API 只开放 VM 的边界。

## 用户和角色

`ADMIN`：

- 同步 Mugen 用例索引。
- 创建测试任务。
- 查看全部测试任务。
- 查看任务详情、任务事件和关联 VM。
- 查看、创建和使用全部测试任务模板。
- 编辑和删除任意测试任务模板。
- 删除任意测试任务，支持单条和批量删除。

`TSE` 和 `TE`：

- 查看 Mugen 用例索引。
- 创建测试任务。
- 默认查看自己的测试任务，可以切换查看全部。
- 查看任务详情、任务事件和关联 VM。
- 查看、创建和使用全部测试任务模板。
- 编辑和删除自己创建的测试任务模板。

任务创建出的 VM 归任务创建人占用。凭据和 VNC 入口继续使用资源管理中的资源权限规则。

### 任务来源

- 测试任务分两类来源：普通任务和流水线任务。流水线任务由测试流水线编排创建，关联关系由
  Pipeline 侧持有（[测试流水线功能规格](0003-test-pipeline.md)）。
- 任务列表展示来源列：普通任务显示"普通"；流水线任务显示流水线模块与架构，可点击跳转
  RunJob 详情；流水线执行已删除的存量孤儿任务显示"流水线(执行已删除)"。
- 流水线执行删除时级联删除其下全部测试任务及子记录，不再产生新的孤儿任务。

### 测试任务删除

- 仅 `ADMIN` 可以删除测试任务；后端鉴权是最终边界，前端仅对 `ADMIN` 展示删除操作。
- 仅终态任务（`succeeded`、`failed`、`error`）可以删除；非终态任务删除返回 `409 Conflict`。
- 任务仍占用测试资源（节点引用的资源处于占用状态）时删除返回 `409 Conflict`，提示
  先释放对应环境；节点行的状态是执行期快照，以资源行的实际占用状态为准；删除动作
  不隐式释放资源。
- 任务仍被流水线执行引用时删除返回 `409 Conflict`，提示先删除对应的流水线执行。
- 删除是硬删除，同一事务中清理全部子记录（环境集、节点、case run、子用例结果、任务事件、
  日志产物登记）；删除后的任务 ID 不复用。共享卷上的日志文件不随删除清理。
- 支持单条删除（`DELETE /api/v1/test-jobs/{任务 ID}`）和批量删除
  （`POST /api/v1/test-jobs/batch-delete`，请求体为 ID 列表）。批量删除逐条应用与单条
  相同的校验，部分失败不中断整批，响应逐条返回成功或失败原因。
- 删除操作写入审计日志，动作为 `test_job.delete`；批量删除逐条记录。

## 功能需求

### 标识和路由

- 测试任务使用从 `10000` 开始递增的整数 ID。
- 测试任务模板使用从 `1` 开始递增的整数 ID。
- 两类 ID 由独立的数据表和序列生成，彼此不冲突；删除后不复用，序列出现空缺属于正常行为。
- 测试任务详情使用可直接分享的 URL：`/test-jobs/<任务 ID>`。

### Mugen 用例索引

- radiaTest 从 `https://atomgit.com/openeuler/mugen` 同步 Mugen 仓库。
- 用例索引以 `suite2cases/*.json` 为来源。
- JSON 文件名去掉 `.json` 后作为 suite 名。
- `cases[].name` 作为 case 名。
- 同步任务保存本次同步的 commit SHA。
- radiaTest 不编辑 Mugen 用例，不保存用例正文。
- 同步时按 suite 文档 `path` 字段定位仓库内用例脚本，对脚本内容做危险操作扫描（伪造 initrd 环境、显式关机/重启类命令），命中即在索引行记录危险标记与原因；扫描不改变脚本本身，也不影响用例在索引页的展示。
- Mugen 同步由 `ADMIN` 手动触发。
- Mugen 同步通过 Celery 异步执行，并写入 `task_events`。
- Mugen 同步使用互斥锁；已有同步正在运行时，再次触发返回 `409 Conflict`，用户稍后手动重试。
- Mugen 同步不新增独立同步任务表；同步事件使用固定 subject 记录。
- 用例索引页面默认不带筛选条件，用户可以按 suite、case 和环境类型筛选。
- 用例索引使用服务端分页，每页固定 50 条。
- 创建测试任务只能选择已同步索引中的 suite/case。

资源约束解析：

- case 约束优先于 suite 顶层约束。
- `machine num` 缺省为 1。
- `machine type` 缺省为 `vm`。
- `kvm`、`vm` 和空值归一化为 `vm`。
- `physical`、`baremetal`、`bare-metal` 归一化为 `physical`。
- 其他 `machine type` 归一化为 `unknown`，不可用于创建任务。
- `add disk` 表示额外数据盘约束。
- `add network interface` 表示额外网卡约束。

### 测试任务创建

- 测试任务字段：
  - 名称。
  - 测试框架 `framework`，只允许 `mugen`。
  - 环境类型 `env_type`，只开放 `vm`。
  - 发行版 `dist`。
  - OS 版本 `os_version`。
  - 镜像轮次 `image_round`。
  - 架构 `arch`。
  - 环境套数 `env_set_num`。
  - 是否保留失败环境 `keep_failed_env`。
  - 环境准备脚本 `pre_env_script`。
  - 环境清理脚本 `post_env_script`。
  - 选择的 suite/case。
- 测试任务只支持自动 qcow2 镜像，不支持手动 ISO。
- `env_set_num` 取值范围为 1 到 20。
- 实际创建的环境套数为 `min(env_set_num, suite_bundle_num)`。
- 测试任务超时为 15 小时，属于整个任务级超时。
- 测试任务创建时固定当前唯一 Mugen 索引 commit；执行时 checkout 该 commit。
- 当前没有 Mugen 索引，或索引不是唯一 commit 时，拒绝创建任务。
- 选择的 suite/case 中只要存在 `node_num > 2` 的 case，拒绝创建任务。
- 测试任务不支持取消。
- 普通测试任务页面不提供重跑；Pipeline RunJob 的用例重跑遵循
  [`0003-test-pipeline.md`](0003-test-pipeline.md) 与 [ADR 0028](../adr/0028-rerun-cases-in-source-environment.md)。

### 测试任务模板

测试任务模板(Test Job Template)保存可重复使用的任务配置，不直接创建或执行任务。

- 模板全局共享，所有已登录用户都可以查看、创建和使用。
- 模板创建人和 `ADMIN` 可以编辑、删除模板；`ADMIN` 编辑模板时不改变创建人。
- 模板硬删除，删除前必须确认；删除后的名称可以重新使用，ID 不复用。
- 模板名称长度为 1 到 64 个字符，只允许 ASCII 字母、数字、`.`、`-` 和 `_`，匹配
  `^[A-Za-z0-9._-]+$`。
- 模板名称全局唯一且不区分大小写；创建或重命名冲突时返回 `409 Conflict`。
- 模板保存测试框架、环境类型、发行版、OS 版本、镜像轮次、架构、环境套数、是否保留失败环境、
  环境准备脚本、环境清理脚本和明确展开的 suite/case 选择。
- 模板不保存任务名称、Mugen commit，也不保存由用例索引推导出的节点数、额外数据盘数和额外网卡数。
- 保存模板时必须至少选择一个 case；`env_set_num` 取值范围为 1 到 20。
- 创建和更新模板时，所选镜像必须存在于当前镜像索引，suite/case 必须存在于当前 Mugen 索引，
  且所有 case 必须满足 `env_type=vm` 和 `node_num <= 2`。
- 模板保存明确的 case 名称；Mugen 后续新增 case 不会自动扩大模板范围。
- 模板 hook 对所有能够查看和使用模板的已登录用户可见。

模板可用性：

- 列表每次按当前镜像索引和 Mugen 索引计算模板是否可用。
- 索引变化导致镜像或 case 不再存在时，模板继续保留并展示不可用原因，不静默删除或修改字段。
- 镜像索引暂时无法读取时，模板列表仍可加载，模板标记为不可用并显示“无法读取镜像索引”。
- 不可用模板不能用于创建任务，但创建人和 `ADMIN` 仍可编辑或删除；刷新后重新计算可用性。

使用模板：

- “使用模板”打开现有任务创建表单并填入模板配置，所有字段仍可编辑。
- 默认任务名称为 `<模板名>-<当前时间>`，用户可以修改。
- 提交前按当前索引重新校验镜像和 suite/case，重新推导资源约束，并固定当前 Mugen commit。
- 提交后创建普通、完整的测试任务；任务与模板之间不保存关联，模板后续编辑或删除不影响任务。
- 使用模板仍调用现有测试任务创建接口，并继续要求 `Idempotency-Key`。

模板接口：

- `GET /api/v1/test-job-templates`
- `POST /api/v1/test-job-templates`
- `GET /api/v1/test-job-templates/{template_id}`
- `PATCH /api/v1/test-job-templates/{template_id}`
- `DELETE /api/v1/test-job-templates/{template_id}`

模板接口不要求 `Idempotency-Key`。重复名称由唯一约束返回 `409 Conflict`，相同 PATCH 结果稳定，
重复删除返回 `404 Not Found`。

模板创建、更新和删除写入审计日志，动作分别为 `test_job_template.create`、
`test_job_template.update` 和 `test_job_template.delete`。审计日志不记录 hook 脚本正文；更新日志只记录
模板 ID、名称和发生变化的字段名。模板变更不写入任务事件。

VM 规格：

- 测试任务自动创建的 VM 默认规格为 4 vCPU、8 GB 内存和 1 块额外数据盘。
- 数据盘大小固定 50 GB。
- 每个 env set 根据分配到的 suite bundle 计算资源约束。
- env set 内的 `node_num`、额外数据盘数量和额外网卡数量取所选 case 约束最大值。
- `add_nic_num` 表示主网卡之外的额外网卡数量；创建 VM 时转换为 VM 创建层的 `extra_nic_num`。
- 额外网卡使用与主网卡相同的网桥配置。
- 不同 env set 可以创建不同规格的 VM。

### suite/case 选择

- 测试用例页面和任务创建页面支持按 suite 名、case 名和 `env_type` 过滤。
- 用户可以勾选整个 suite，也可以勾选 suite 下的单个 case。
- 后端保存任务时把 suite 展开为具体 case。
- suite bundle 是调度分片单位；如果用户只选择 suite 下部分 case，该 suite bundle 只包含被选择的 case。
- 按 suite bundle 轮询分配到 env set。
- env set 内按 suite bundle 顺序执行；suite bundle 内按 case 顺序执行。

### 任务执行

- 测试任务由一个 Celery task 串行编排执行；当前不拆分 env set 级子任务。
- worker 按任务记录的 Mugen commit SHA 在控制节点 checkout 对应代码。
- 每套 env set 创建 `node_num` 台 VM。
- 每套 env set 当前最多创建 2 台 VM。
- 每套 env set 的第一台 VM 是控制节点(Control Node)，第二台 VM 是辅助节点(Peer Node)。
- 测试任务复用 `VMRequest`、虚拟资源和租约语义，但测试任务内部同步执行 VM 创建，不在 Celery task 内二次投递 VM 创建 task。
- 测试任务创建出的 VM 租约预计结束时间为任务创建后 15 小时。
- Mugen 只在控制节点部署和执行。
- VM 创建后需要等待 SSH ready：
  - 使用默认账号 `root` 和密码 `openEuler12#$`。
  - 每 10 秒重试一次。
  - 最多等待 10 分钟。
- 控制节点每次执行前重建 `/opt/mugen`，并 checkout 任务固定的 Mugen commit。
- 控制节点执行 `bash dep_install.sh` 安装 Mugen 依赖。
- 控制节点先为本端执行：

```bash
bash mugen.sh -c --ip <control_ip> --password <control_password> --user root --port 22
```

- `node_num=2` 时，控制节点再为辅助节点执行一次：

```bash
bash mugen.sh -c --ip <peer_ip> --password <peer_password> --user root --port 22
```

- 如果用户填写 `pre_env_script`，每套 env set 在本环境分配的所有 case 开始前，在控制节点执行一次环境准备脚本。
- 每个 case 执行：

```bash
bash mugen.sh -f <suite> -r <case> -x
```

- 如果用户填写 `post_env_script`，每套 env set 总是尝试在控制节点执行一次环境清理脚本；是否跳过某些步骤由用户脚本自行判断。
- radiaTest 不额外指定 Mugen 日志路径。
- case 结果根据退出码和执行超时判断：
  - 退出码为 0：`passed`。
  - 退出码非 0：`failed`。
- case 执行超过 `CASE_TIMEOUT_SECONDS`（默认 12 小时，受 15 小时任务总超时约束）：`timeout`。
- case `failed` 或 `timeout` 不中断同一 env set 的后续 case；平台链路异常才中断该 env set。
- radiaTest 保存 case 执行的退出码、stdout 摘要、stderr 摘要和开始/结束时间。
- stdout 摘要和 stderr 摘要各最多保存 16 KB。
- 完整 Mugen 日志保留在控制节点上的 Mugen 默认路径。

环境 hook：

- hook 在 env set 控制节点上执行。
- hook 脚本不作为 Mugen case，不计入 case 通过/失败统计。
- `pre_env_script` 在 Mugen 环境配置完成后、本环境分配的所有 case 开始前执行。
- `pre_env_script` 失败时，不执行该 env set 的 case，任务进入 `error`，仍然尝试执行 `post_env_script`。
- `post_env_script` 填写后总是尝试执行；`keep_failed_env`、`pre_env_script` 结果和 case 结果不影响该 hook 是否执行。
- `post_env_script` 失败时，任务进入 `error`。
- hook 失败属于任务异常，不属于测试失败。
- 每个 hook 独立超时时间为 30 分钟，并计入任务 15 小时总超时。
- hook stdout/stderr 只保存摘要，不保存完整日志。
- hook 使用任务级环境文件，不读取 radiaTest 平台配置：

```text
/root/kronos/jobs/<job_id>/env-<index>/kronos.env
/root/kronos/jobs/<job_id>/env-<index>/pre_env.sh
/root/kronos/jobs/<job_id>/env-<index>/post_env.sh
```

- worker 执行 hook 时显式加载 `kronos.env`：

```bash
set -a
source /root/kronos/jobs/<job_id>/env-<index>/kronos.env
set +a
bash /root/kronos/jobs/<job_id>/env-<index>/pre_env.sh
```

- `kronos.env` 只包含当前 job、env set 和节点信息，不包含数据库、JWT、飞书等平台 Secret。
- `kronos.env` 内容不写入 `task_events`。

### 状态语义

测试任务状态：

- `pending`：已创建，等待 worker 执行。
- `preparing`：正在同步执行准备工作或创建环境。
- `running`：正在执行 Mugen case。
- `succeeded`：所有 case 通过，环境清理完成。
- `failed`：至少一个 case 执行失败。
- `error`：平台链路异常，包括 VM 创建失败、SSH ready 超时、Mugen clone 或依赖安装失败、hook 失败、任务超时、环境销毁失败等。

测试环境套状态：

- `pending`。
- `creating_vms`。
- `running`。
- `succeeded`。
- `failed`。
- `error`。
- `destroying`。
- `destroyed`。

测试用例执行状态：

- `pending`。
- `running`。
- `passed`。
- `failed`。
- `timeout`。
- `error`。

测试任务失败和任务异常必须区分：

- case 退出码非 0 导致的失败和 case 执行超时称为测试失败。
- 平台、环境、编排、SSH、任务总超时和销毁问题称为任务异常。

### 环境清理

- 任务结束默认销毁该任务创建的全部 VM。
- `keep_failed_env=false` 时，测试失败环境也销毁。
- `keep_failed_env=true` 时：
  - 成功环境销毁。
  - 用例失败或超时的环境保留。
  - 保留 VM 继续归任务创建人占用。
- 平台异常环境默认尝试销毁；销毁失败时任务进入 `error`。

### 页面

测试用例页面：

- 展示当前 Mugen 索引 commit。
- 展示 suite/case 列表。
- 支持按 suite、case 和 `env_type` 过滤。
- 展示推导出的 `node_num`、额外数据盘数量、额外网卡数量和可选状态。
- `ADMIN` 可以触发同步 Mugen 用例。
- 同步详情可以查看任务事件。

测试任务页面：

- 使用“任务列表”和“任务模板”两个二级 tab。
- `/test-jobs` 重定向到 `/test-jobs/list`。
- `/test-jobs/list` 默认展示当前用户创建的测试任务，提供“查看全部”切换和创建测试任务入口。
- 任务列表支持按名称模糊搜索、按状态筛选；“查看全部”视图下额外支持按创建人筛选
  （精确匹配用户名）。筛选条件应用在当前权限范围内，我的任务视图忽略创建人条件。
- 任务列表首列提供复选框（仅 `ADMIN` 可见），配合操作列的单条删除和工具栏的批量删除。
- `/test-jobs/templates` 展示全部共享模板，按更新时间倒序排列，不提供搜索或筛选。
- 测试任务列表和模板列表使用服务端分页，每页固定 50 条。
- 模板列表展示 ID、名称、镜像版本、架构、环境套数、suite/case 数量、可用状态、创建人、更新时间和操作。
- 模板列表提供“使用模板”；创建人和 `ADMIN` 额外看到编辑、删除操作。页面右上角提供创建模板入口。
- 模板创建和编辑使用同一配置表单，不提供单独的模板详情页。
- `/test-jobs/<任务 ID>` 展示完整任务详情，Vben 页签标题为 `任务 #<任务 ID>`，页面正文展示完整任务名称。
- 任务详情提供固定返回 `/test-jobs/list` 的“返回任务列表”入口，并展示：
  - 基本信息。
  - env set 列表。
  - node 列表。
  - case run 结果表。
  - 任务事件。
  - 保留环境关联 VM 入口。

列表分页：

- 用例索引、测试任务列表和任务模板列表请求使用从 `1` 开始的 `page`。
- 分页响应统一包含 `items`、`total`、`page` 和固定值 `50` 的 `page_size`。
- `total` 为应用当前权限和筛选条件后的记录总数。
- 页码超过最后一页时返回空 `items`，不自动改写页码。
- 筛选条件或“查看全部”范围变化后回到第 1 页。- 各列表保留现有固定业务排序，并使用记录 ID 作为稳定次级排序键；不提供通用排序参数或表头排序。
- 任务详情页底部只提供一个刷新按钮，同时刷新基本信息、env set、node、case run 和任务事件。
- 测试任务页面不自动轮询。

任务创建交互：

- suite/case 选择使用左右分栏。
- 左侧展示 suite 列表并支持 suite 过滤。
- 右侧展示当前 suite 下 case 列表并支持 case 过滤。
- 支持勾选整个 suite 或单个 case。
- 展示已选择 suite/case 数量和推导资源约束。

## 非目标(Non-Goals)

不包含：

- 物理机测试任务执行。
- 手动 ISO 测试任务。
- Web 编辑 Mugen 用例。
- case 级动态抢占式调度。
- 任务取消。
- 任务详情页删除入口。
- 共享卷上日志产物文件的清理。
- 普通测试任务重跑（Pipeline RunJob 用例重跑除外）。
- 集中归档完整 Mugen 日志。
- 把 hook 环境变量写入 `/etc/profile` 或系统级环境文件。
- 独立测试报告页面。
- LLM 自然语言筛选用例。
- 模板复制或“另存为模板”。
- 单独的模板详情页。
- 在测试任务中保留来源模板关联。
- 在模板中固定 Mugen commit。
- 模板搜索和筛选。

## 验收标准(Acceptance Criteria)

- `ADMIN` 可以触发 Mugen 用例同步。
- Mugen 同步完成后可以看到同步 commit、suite/case 列表和资源约束。
- Mugen 同步运行中再次触发返回 `409 Conflict`。
- 非 `ADMIN` 不能触发 Mugen 同步。
- 用户可以创建 `framework=mugen`、`env_type=vm` 的测试任务。
- 创建测试任务时会固定当前 Mugen 索引 commit。
- 未同步 Mugen 索引时不能创建测试任务。
- 用户可以通过 suite/case 分栏选择多个 suite/case。
- 后端可以根据 `suite2cases` 推导 `node_num`、额外数据盘数量和额外网卡数量。
- 选择包含 `node_num > 2` 的 suite/case 时，后端拒绝创建任务。
- `env_set_num` 大于 suite bundle 数量时不会创建空 env set。
- 测试任务会自动创建 VM，并在控制节点部署 Mugen。
- 测试任务创建的 VM 租约预计结束时间为任务创建后 15 小时。
- case 执行结果按退出码生成 `passed` 或 `failed`，超过 `CASE_TIMEOUT_SECONDS`（默认 12 小时）生成 `timeout`。
- 任意 case `failed` 或 `timeout` 时，测试任务状态为 `failed`。
- VM 创建、SSH ready、Mugen 准备、hook、任务超时或环境销毁失败时，测试任务状态为 `error`。
- 用户填写的 `pre_env_script` 和 `post_env_script` 会在每套 env set 的控制节点上执行。
- `pre_env_script` 失败、case 失败或 case 超时时，已填写的 `post_env_script` 仍会执行。
- hook 执行时可以读取任务级 `kronos.env`，但 task events 不记录该文件内容。
- 默认任务结束销毁所有 VM。
- 启用 `keep_failed_env` 且 case 失败或超时时，对应环境 VM 被保留并归任务创建人占用。
- 测试任务和 Mugen 同步都写入 `task_events`。
- 测试任务 ID 从 `10000` 开始，模板 ID 从 `1` 开始；两者独立递增且删除后不复用。
- 用户可以通过 `/test-jobs/<任务 ID>` 直接打开和分享完整任务详情。
- 任务详情页的单个刷新操作会更新详情和事件，页面不自动轮询。
- 所有已登录用户可以查看、创建和使用共享模板；只有创建人和 `ADMIN` 可以编辑或删除。
- 模板名称校验、大小写不敏感唯一约束和权限错误由后端强制执行。
- 模板保存明确的 suite/case 和 hook；使用模板时重新校验当前索引、推导资源并固定当前 Mugen commit。
- 模板失效或镜像索引不可用时仍保留并展示原因，但不能用于创建任务。
- 使用模板只预填普通任务创建表单，已创建任务不依赖模板后续状态。
- 模板创建、更新和删除写入审计日志，且不记录 hook 正文。
- 任务列表支持名称模糊搜索、状态筛选和“查看全部”视图下的创建人筛选，筛选后分页计数正确。
- 仅 `ADMIN` 可以删除测试任务；非终态、存在未销毁环境或被流水线执行引用的任务删除返回
  `409 Conflict`，缺失任务返回 `404 Not Found`。
- 删除任务后其环境集、节点、case run、子用例结果、任务事件和日志产物登记同时清除，
  任务 ID 不复用。
- 批量删除逐条校验并返回逐条结果，部分失败不影响已成功的删除。
- 删除测试任务写入 `test_job.delete` 审计日志。
- 任务列表展示来源列：普通任务、流水线任务（可跳转 RunJob 详情）和执行已删除的流水线
  孤儿任务可区分。
- 流水线执行删除后，其下全部测试任务及子记录一并删除。
