<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0007：测试管理和 Mugen 执行(Test Management and Mugen Execution)

## 状态

已接受(Accepted)。

## 背景

radiaTest 已具备资源、VM 创建、Celery 异步任务和任务事件能力。测试任务需要创建测试环境、执行用例、记录结果和清理 VM；它和飞书远程命令不同，不能建模为一次性运维命令。

## 决策

- 测试任务(Test Job)独立建模，不升级或复用远程命令(Remote Command)作为产品概念。
- 测试任务复用 Celery、Redis、SSH 执行能力和通用任务事件(Task Event)。
- 后端以 `test_management` 作为产品深模块；VM 环境部署和 Mugen 框架执行分别作为模块内具名 adapter。
- 当前不引入泛型 framework/env registry 或基类；出现第二个测试框架或环境类型时再抽取正式接口。
- 普通测试任务支持 VM 环境执行；模型保留 `env_type`，普通任务的物理机环境执行不在范围内。Pipeline 内部 TestJob 的物理机执行是后续 [ADR 0015](0015-kernel-module-envtype-physical-reinstall-result-dispatch.md) 的例外，不扩展普通任务 API。
- 测试框架字段保留扩展空间，支持的框架为 Mugen。
- Mugen 用例以 Git 仓库 `https://atomgit.com/openeuler/mugen` 为事实来源；radiaTest 不编辑用例，只同步并缓存 `suite2cases` 索引。
- Mugen 同步由 `ADMIN` 手动触发，通过 Celery 异步执行，并使用互斥锁避免并发同步。
- 测试任务创建时固定当前 Mugen 索引 commit；执行时 checkout 该 commit。
- 测试任务创建时选择 suite/case，后端展开为 case run；执行时固定调用
  `bash mugen.sh -f <suite> -r <case> -x`。
- 测试任务自动创建 VM，不使用已有 VM；已有 VM 执行作为独立扩展能力处理。
- 测试任务由单个 Celery task 串行编排；当前不拆分 env set 级子任务。
- 测试任务复用 `VMRequest`、虚拟资源和租约语义，但在测试任务 task 内同步执行 VM 创建，不在 Celery task 内二次投递 VM 创建 task。
- 测试任务创建出的 VM 租约预计结束时间为任务创建后 15 小时。
- Mugen 约束中的额外网卡需求必须传递到 VM 创建层，作为主网卡之外的 `extra_nic_num`。
- 当前每套 env set 最多支持 2 个节点；超过 2 个节点的 case 不可创建测试任务。
- 单个 case 执行超时时间由 `CASE_TIMEOUT_SECONDS` 控制（默认 12 小时），受 15 小时任务总超时约束（`job_step_timeout` 取剩余时间的较小值）；case 超时记为测试未通过结果，使任务进入 `failed`。不再用 shell `timeout 1h` 包裹 mugen 命令，改由 `run_process` 的 `CASE_COMMAND_TIMEOUT_SECONDS` 控制。
- 测试任务支持 env set 级 `pre_env_script` 和 `post_env_script` hook；hook 在控制节点执行。
- `post_env_script` 填写后默认尝试执行，不由平台推断是否应跳过。
- hook 使用任务级 `kronos.env` 传递 job、env set 和节点信息，不写入 `/etc/profile` 或系统级环境文件。
- 测试任务不支持取消；普通测试任务不支持重跑。Pipeline RunJob 的失败用例按选重跑由
  ADR 0028 定义。
- 测试任务使用从 `10000` 开始的整数主键；测试任务模板使用独立表中从 `1` 开始的整数主键。
- 测试任务模板作为独立配置聚合建模，保存普通配置字段和结构化 suite/case 选择，不与创建出的任务建立持久关联。
- 模板保存明确的 case 名称，但不固定 Mugen commit；使用模板创建任务时按当前索引重新校验和推导资源，
  再由普通任务创建流程固定 commit。
- 使用模板只预填现有任务创建表单，不新增“从模板执行”接口。

## 取舍

独立测试任务模型比复用远程命令复杂，但能明确表达测试框架、用例、环境套、节点、结果和清理语义。底层执行能力继续复用，避免重复实现 SSH、Celery 和日志机制。

选择从 `suite2cases` 同步索引，而不是扫描 `testcases` 或解析 AtomGit 页面，是因为 `suite2cases` 已包含 suite/case 关系和资源约束，Git 仓库比网页结构稳定。

选择全部展开成 case 执行，而不是按 suite 整体执行，是为了得到 case 级结果、状态和摘要；suite 仍作为调度分片单位。

选择任务结束默认销毁 VM，是为了避免测试任务长期占用资源。`keep_failed_env` 只在用例失败时保留失败环境，平台异常或清理异常不称为测试失败。

选择任务级 `kronos.env`，而不是把变量写入 `/etc/profile`，是为了避免把数据库、JWT、飞书等平台 Secret 带入测试 VM，也避免污染用户手动 SSH 和其他调试进程。

选择具名 adapter 而不是泛型 registry，是为了先稳定 VM 和 Mugen 的真实接口边界，避免为了尚不存在的第二实现增加理解成本。

选择单个 Celery task 串行编排测试任务，是为了避免 Celery task 嵌套等待导致 worker 自锁，并让测试任务状态、事件和清理逻辑集中在一个 module。代价是单个长任务会占用 worker；当前通过 worker 并发数控制吞吐，等真实压力出现后再拆 env set 级子任务。

选择复用 `VMRequest` 但不二次投递 VM 创建 task，是为了复用现有 VM 申请记录、资源、租约和诊断事件，同时保持测试任务是唯一编排入口。

选择系统 `ssh`/`scp`/`timeout` 而不是 Paramiko，是因为当前只需要在 Linux worker 中执行可复现命令并截取摘要；引入 Python SSH 客户端会增加依赖和连接行为差异。

选择独立模板聚合而不是让任务引用模板，是因为模板是可变的共享输入，而任务必须保存提交时的完整执行快照。
模板修改或删除不会改变历史任务，也不需要维护模板版本。

选择普通列保存模板标量字段、使用 JSONB `case_selections` 保存明确展开的 suite/case，结构为
`[{"suite_name": "<suite>", "case_names": ["<case>"]}]`。标量需要直接校验和展示，而选择结构只在模板边界整体读写；
为当前用法引入多张关联表会增加写入和读取复杂度。

选择在使用模板时固定当前 Mugen commit，而不是在模板中固定 commit，是为了让模板表达可复用配置，
同时由创建任务这一刻形成可重现的执行快照。失效模板保留并显式标记，不静默改变所选 case。

选择两套独立整数序列，是为了让用户可读的任务和模板 ID 简短稳定；二者位于不同资源和 URL 空间，
无需共享编号或避免数值重叠。

## 影响

- 需要新增测试任务、测试环境套、测试环境节点、测试用例索引和用例执行结果等持久化模型。
- VM 创建脚本需要支持测试任务约束中的额外网卡数量。
- VM 创建模块需要暴露测试任务可复用的同步创建能力，但不把宿主脚本细节泄漏给测试任务调用方。
- Web 需要新增测试用例和测试任务页面。
- 测试任务和 Mugen 同步产生的阶段事件继续写入 `task_events`。
- 需要新增测试任务模板持久化模型和管理接口；模板变更写入审计日志，不写入任务事件。
- 切换测试任务主键类型的迁移不保留已有测试任务、环境套、节点和 case run，并删除
  `subject_type=test_job` 的任务事件及旧任务创建接口的幂等记录；迁移不销毁或删除已有 VM、资源和
  租约，遗留 VM 仍可按普通 VM 资源手动释放。
