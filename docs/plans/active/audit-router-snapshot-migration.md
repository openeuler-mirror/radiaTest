<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 审计查询路由固定快照补迁

## 范围

补迁 Kronos 固定提交 `b0e0bc2` 的 `backend/app/modules/audit/router.py`，
解除 API 路由聚合入口和已有审计测试的缺失模块导入阻塞。
保留原有路径、ADMIN 权限边界、过滤条件、固定分页和响应格式。

## 明确不做

- 不新增产品能力，不修改审计服务、数据模型或数据库迁移。
- 不补搬其他领域路由，不运行应用、数据库或部署。
- 不修改已有合入历史，不发布依赖尚未合入分支的后续批次。

## 实施步骤

1. 基于已合入的上游 `devel`，用现有审计测试复现缺失模块错误。
2. 搬入固定快照路由，补齐版权头；复用已有 `AuditLogListParams`
   依赖参数模型，等价替换超过门禁参数数量限制的独立查询参数。
3. 验证原有过滤、鉴权和分页测试，以及查询参数的 OpenAPI 声明。
4. 检查最终差异并记录审查结果；仅准备一个供用户创建 PR 的分支。

## 验证标准

- 已有审计测试由收集失败恢复为通过。
- 五个过滤字段仍为可选 query 参数，GET 请求不要求请求体。
- 未认证访问拒绝；非 ADMIN 拒绝；无效时间参数返回 422。
- 定向 lint、静态门禁自检和项目检查有实际结果；基线失败明确记录。
- 相对已合入上游基线的新增行加删除行严格小于 1000。
- 用户创建 PR 后复核平台实际差异；确认该 PR 合入后才发布下一批。
