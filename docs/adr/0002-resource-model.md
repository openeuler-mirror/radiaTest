<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0002：资源模型(Resource Model)

## 状态

已接受(Accepted)。

## 背景

radiaTest 需要同时管理物理机器和按需创建的虚拟机。它们共享租约、凭据、资源池、标签、连通性检查、日志和 API 语义，但类型专属字段不同。物理机有 BMC 和硬件规格；虚拟机有宿主、VNC 端口、VNC WebSocket 端口、系统盘、数据盘和虚拟硬件规格。

## 决策

采用公共资源主表和类型规格扩展表：

```text
resources
physical_resource_specs
virtual_resource_specs
```

每个资源包含：

- 内部主键(Primary Key)：`id`，类型为 UUID。
- 对外业务身份：`resource_code`，不可变字符串。
- 资源类型：`resource_type`，取值为 `PHYSICAL` 或 `VIRTUAL`。

`resource_code` 规则：

- 物理资源：设备整机 SN。
- 虚拟资源：VM UUID。
- 用于公开 API、导入导出和用户识别。
- 创建后默认不可修改。
- 管理员可以通过独立的强审计操作修正。

## 状态字段

使用独立状态字段：

- `management_status`：`active`、`maintenance`、`disabled`。
- `connectivity_status`：`unknown`、`reachable`、`unreachable`。
- `occupancy_status`：`idle`、`occupied`、`expired`。

不要用一个字段混合表达维护、连通性和租约状态。

## 资源池(Resource Pool)

资源池用于按实验室、网络区域、用途或类似维度对资源分类。资源池不参与权限控制。

## 标签和扩展字段

使用：

- `tags TEXT[]` 保存简单标签。
- `extra JSONB` 保存非核心迁移字段或临时字段。

核心规则、权限、状态和凭据不能依赖 `extra`。

## 影响

- 通用 API 和租约逻辑可以基于 `resources` 工作。
- 物理字段和虚拟字段保持干净，避免大量无意义空列。
- 详情页根据 `resource_type` 加载对应类型规格。
- VM 申请成功后创建 `VIRTUAL` 资源和租约；VM 释放成功后释放租约并软删除资源。
- VM 生命周期功能可以建立在虚拟资源规格之上，而不改变租约语义。
