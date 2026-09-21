<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0008：统一服务端分页契约

## 状态

已接受。

## 背景

VM、VM 申请记录、审计日志、租约日志、测试用例、测试任务、任务模板和工单列表需要服务端分页。
现有页面有的加载全量数据后使用 Ant Design Vue 前端分页，有的 API 使用 `limit/offset`，接口形状不一致。

## 决策

- 列表请求统一使用从 `1` 开始的 `page`，每页固定 50 条。
- 分页响应统一包含 `items`、`total`、`page` 和固定值 `50` 的 `page_size`。
- 后端提供薄公共 `PageParams` 和泛型 `PageResponse`。
- 前端提供薄公共分页响应类型和统一分页器配置。
- 各领域模块自行实现权限、过滤、总数查询和固定排序。
- 各查询使用记录 ID 作为稳定次级排序键。
- 不提供每页数量选择、通用排序参数或表头排序。
- 不抽象通用 Repository、SQL 查询构造器或列表状态 composable。
- 现有数组响应和 `limit/offset` 接口由前后端在同一次迁移中直接替换，不保留兼容格式。

## 原因

统一契约可以复用分页交互和 API 类型，同时保留各领域不同的权限、过滤与排序语义。
固定每页 50 条减少参数和页面状态；薄公共模块避免为少量列表引入通用查询框架。

## 影响

- VM、VM 申请记录、审计日志、租约日志、测试用例、测试任务、任务模板和工单列表采用同一分页格式。
- 调用方必须从分页响应的 `items` 读取记录，并使用 `total` 渲染分页器。
- 页码超出最后一页时返回空 `items`，不自动改写页码。
