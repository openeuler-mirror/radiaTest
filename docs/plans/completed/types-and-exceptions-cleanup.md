<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 前端 any/断言收敛 + 后端宽异常收敛 + router docstring 补齐

## 状态

实施与定向验证已完成（`25d6019 refactor: 收敛前端 any/断言、后端宽异常与 router docstring` 已合入 `main`）；`a788699` 之后重跑 `./scripts/check.sh` 全量通过（backend 495 passed / 1 skipped，docs/scripts/frontend 全绿），MR 审查记录以 merge commit 作为代理。计划归档到 `docs/plans/completed/`。清单的勾选表示该项已经完成实现或边界核对；实际改动以 `Implementation Outcome` 为准。

## Goal

1. 前端：消除 radiaTest 自身业务代码中的 `any` 类型与过度类型断言，改用具体类型。
2. 后端：服务/领域逻辑层的 `except Exception` 改为具体异常类型；顶层/外部边界保留宽捕获但确保日志不吞错。
3. 后端：为全部 router endpoint 补齐 Google-style docstring。

## Confirmed Decisions

1. 前端范围仅限 `frontend/apps/web-antd/`（约 11 处 `any`/断言，集中在 `views/pipelines/` 与 `adapter/component/index.ts`）。**不触碰** `frontend/packages/`（Vben Admin 上游框架代码），避免破坏后续升级。
2. 后端异常分两组处置：
   - **A 组（服务/领域逻辑，改具体异常）**：`tickets/commands.py`、`idempotency/service.py`、`vms/image_discovery.py`、`vms/service.py`、`test_management/service.py`、`test_management/execution.py`、`pipelines/service.py`、`leases/service.py`、`core/api_runtime.py`、`feishu/card_actions.py`。具体类型按上下文选用 `subprocess.CalledProcessError`、`asyncio.TimeoutError`、`httpx.HTTPError`、`OSError`、自定义领域异常等。
   - **B 组（顶层/外部边界，保留 `except Exception` 但带日志不吞错）**：`worker.py`、`feishu/bot_runtime.py`、`notifications/tasks.py`、`pipelines/tasks.py`、`test_management/tasks.py`、`tasks/recovery.py`、`hang_detector.py`、`test_management/remote.py`、`mugen_runner.py`、`vms/pxe_install.py`、`test_management/envs/vm.py`。多为 `# noqa: BLE001` 有意兜底，逐处确认有日志；无日志的补上。
   - `vms/pxe_install.py`（3 处）与个别文件混合 A/B 语义，实现时按每处上下文判定归属。
3. 全部 71 个 router endpoint 补齐为 Google-style docstring（一行 summary + `Args` + `Returns` + `Raises`（若有）），不论是否已有，统一标准。
4. 分支 `refactor/types-and-exceptions`，从 `main` 创建。前置 WIP 已 `git stash -u` 暂存于 `feat/case-rerun-env-reuse`。

## Non-Goals

- 不重构 Vben Admin 框架代码（`frontend/packages/`）。
- 不改变异常处理的控制流语义（不新增/移除重试、轮询、后台任务）。
- 不改动 router endpoint 的业务逻辑或签名，仅补 docstring。
- 不为 B 组顶层兜底强行换成具体异常（会破坏长驻/任务兜底语义）。
- 不新增抽象、依赖或配置。

## Task Checklist

### Task 1: 前端 — any 与类型断言收敛（apps/web-antd）

- [x] `src/views/pipelines/types.vue`
- [x] `src/views/pipelines/config-detail.vue`
- [x] `src/views/pipelines/index.vue`
- [x] `src/adapter/component/index.ts`
- 逐处用具体类型替换 `any`；移除不必要 `as` 断言；无法推断时补最小接口而非 `any`。

### Task 2: 后端 — A 组异常收敛

- [x] `app/core/api_runtime.py`
- [x] `app/modules/tickets/commands.py`
- [x] `app/modules/idempotency/service.py`
- [x] `app/modules/vms/image_discovery.py`
- [x] `app/modules/vms/service.py`（6 处）
- [x] `app/modules/test_management/service.py`（2 处）
- [x] `app/modules/test_management/execution.py`（3 处）
- [x] `app/modules/pipelines/service.py`（5 处）
- [x] `app/modules/leases/service.py`
- [x] `app/modules/feishu/card_actions.py`
- [x] `app/modules/vms/pxe_install.py`（按处判定 A/B）

### Task 3: 后端 — B 组顶层兜底补日志

- [x] 逐处确认有日志、不静默吞错；缺日志的补 `logger.exception`/`logger.error`。
- [x] 不改变捕获范围，保留 `except Exception` + `# noqa: BLE001`。

### Task 4: 后端 — router endpoint docstring

- [x] `modules/notifications/router.py`
- [x] `modules/resources/router.py`
- [x] `modules/users/router.py`
- [x] `modules/audit/router.py`
- [x] `modules/auth/router.py`
- [x] `modules/feishu/router.py`
- [x] `modules/pipelines/router.py`
- [x] `modules/tickets/router.py`
- [x] `api/v1/health.py`

## Verification

- `./scripts/check.sh backend` — ruff + pytest（含 `backend/tests/test_api_runtime.py` 等路由测试）
- `./scripts/check.sh frontend` — typecheck + lint + build（验证 any 清理不破坏类型）
- 抽查：A 组无残留 `except Exception`；B 组每处有日志；router 每个端点有 Google-style docstring。

## Implementation Outcome

分支：`refactor/types-and-exceptions`（从 `main` 创建；`feat/case-rerun-env-reuse` 的 WIP 已 `git stash -u` 暂存）。

- Task 1（前端 any 收敛）：改 `api/core/pipelines.ts`(4×`Record<string,any>`→`unknown`)、`views/pipelines/types.vue`、`config-detail.vue`、`index.vue`、`adapter/component/index.ts`。5 处 `catch(error:any)` 改用既有 `parseAPIError(error)` 类型安全助手；config-detail 的 409 分支用 `apiError.code==='conflict'` 复活了原死代码 `error?.response?.status` 访问。adapter 中 4 处 `any`(attrs/slots/emit 包、ref 回调、`as any`)因 Vue 动态契约强制保留并加 `ponytail:` 注释说明上限。
- Task 2（A 组异常收敛）：实际为 **9 处**，不是预估的 20——分析后发现多数 `except Exception` 实为事务/清理守卫(B-guard)或外部边界。已转换：`vms/service.py`(309,331)、`test_management/service.py`(152,184)、`pipelines/service.py`(109)→`(OperationalError, OSError)`；`pipelines/service.py:916`→`OSError`；`test_management/remote.py`(208,259)→`(OSError, subprocess.SubprocessError)`；`vms/image_discovery.py:56`→`OSError`。`resources/router.py:330` 归 B(外部探针→502 边界，非静默)。`api_runtime.py:299` 归 B(顶层中间件，已有 `logger.exception`)。
- Task 3（B 组日志）：为非轮询的静默吞错处补 `logger.debug`(默认不噪)/`logger.warning`(清理泄漏)：`hang_detector.py`(守护线程)、`pipelines/service.py`(env 清理 warning×2、日志读 debug)、`pipelines/tasks.py`×2、`mugen_runner.py`×6、`remote.py`×2、`pxe_install.py`×1。**轮询循环**(reboot/reachability SSH 轮询)保留静默——吞错即"未就绪"信号，逐次日志是噪声。
- Task 4（router docstring）：4 个并行子代理共加 **62 个** Google-style docstring，6 个已有保留(pipelines 2、auth login、health 2、feishu bind)。

## Verification Results

- 后端：ruff ✓、compileall ✓、pytest 416 passed/1 skipped；**3 failed** = `test_create_vm_concurrent`（`create-vm.sh` 依赖 `flock`/libvirt，macOS 无此命令，**环境限制**，非本次改动——测试仅 subprocess 跑 bash 脚本，不触及 enqueue/send_task/OperationalError）。
- 前端：typecheck ✓、lint ✓（oxfmt/stylelint/eslint 全绿；附带用 `--fix` 修复了 main 上既有的 `log-viewer.vue` CSS 顺序+格式违例以解锁检查）、build ✓(`✓ built in 2.08s`)；vitest 63 passed/**2 failed** = `vm-request-form.test.ts`（imageRound 校验测试与实现不符，**main 上既有**，与本次无关——该文件未被本次改动且不导入任何改动文件）。

## Restore stashed WIP

回到 `feat/case-rerun-env-reuse` 后：`git stash pop` 恢复之前的 case-rerun WIP。
