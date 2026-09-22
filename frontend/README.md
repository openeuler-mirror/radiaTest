# radiaTest 前端

前端基于 Vben Admin 5.7.0 的 Ant Design Vue 应用精简而来，保留 Vben 的布局、权限、请求、状态管理和工程工具。

## 环境要求

- Node.js 22.18 或 24.x。
- pnpm 10.33.4，通过 Corepack 使用项目固定版本。

## 开发方式

前端只在远程 Linux `dev` 环境构建和运行。开发工作站修改代码并推送到 GitCode 后，在服务器 `/opt/kronos/dev/app` 执行 `./scripts/deploy.sh [分支名]` 部署并验证。

## 页面

- 登录页。
- Dashboard 工作台，展示当前用户和数据库状态。
- 我的账号页 `/account`，支持修改当前用户密码。
- 物理机管理页 `/resources`，展示物理资源列表、逐列文本模糊筛选、`AND`/`OR` 匹配、资源详情、管理员编辑物理机台账、占用、释放、强制释放、授权凭据查看、资源 CSV 导入和租约 CSV 导入。
- 虚拟机管理页 `/virtual-machines`，展示 VM 列表和申请记录，支持申请 VM、本地 ISO 上传、查看申请详情、宿主尝试摘要、任务事件、VM 凭据、Web VNC 控制台和释放 VM。
- 测试用例页 `/test-cases`，查询 Mugen suite/case 索引并支持管理员同步。
- 测试任务列表 `/test-jobs/list`，创建和查看测试任务。
- 任务模板页 `/test-jobs/templates`，创建、使用和管理共享任务模板。
- 测试任务详情页 `/test-jobs/<任务 ID>`，查看环境套、节点、用例结果及任务事件。
- 工单管理页 `/tickets`，提交、筛选和查看全部工单。
- 工单详情页 `/tickets/<工单 ID>`，编辑本人待处理工单、处理工单和发表评论。
- 审计日志页 `/audit-logs`，仅 `ADMIN` 可见。
- 租约日志页 `/lease-events`，`ADMIN` 和 `TSE` 查看全部日志，`TE` 查看自己的日志。
- 飞书集成页 `/integrations/feishu`，仅 `ADMIN` 可见。
- 用户管理页 `/users`，仅 `ADMIN` 可见，支持用户列表、新建、编辑和重置密码。

## 页面布局约定

管理页筛选区使用共享 `ManagementFilterPanel`，页面显式提供过滤字段并自行构造查询参数；不要从表格列自动生成过滤条件。新增、导入、导出等数据操作放在表格工具栏，不混入筛选区。

## 检查和构建

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm typecheck
pnpm lint
pnpm build
```

生产构建输出位于 `apps/web-antd/dist/`。

Vben Admin 按 MIT License 发布，原始许可见 [LICENSE](LICENSE)。
