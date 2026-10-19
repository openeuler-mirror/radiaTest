<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Kronos 前端固定快照迁移

## 范围

按已确认的 K 系列迁移范围，从 Kronos `b0e0bc2` 搬运 K4 清单的 36 个文件。
基线为上游 `devel` 的 `c661f651`；前端脚手架、锁文件及应用骨架已合入。
保留 Vue Composition API、现有 Vben/Ant Design Vue 组件、样式和交互。

## 明确不做

- 不引入快照之后的实现，不新增功能、接口、依赖、轮询或视觉设计。
- 不补开发上游缺失的审计路由或数据库迁移。
- 不在工作站启动应用或浏览器联调，不代用户创建和合入 PR。
- 不包含原工作区的 `.gitignore` 改动，不修改锁文件。

## 实施

1. 核对固定快照文件、已有导出入口和相对导入依赖。
2. 添加版权头，按完整文件和 SFC 区块拆分，每批单提交且增删合计小于 1000 行。
3. 复用原有测试，执行定向测试、SFC/TypeScript 语法检查和项目检查入口。
4. 与固定快照逐文件对照，检查最终差异、断言、依赖和敏感信息。
5. 审查通过后推送 fork 分支，提供 PR 描述、验证结果和依次合入顺序。

## 验证

- 除版权头及明确记录的门禁或兼容适配，最终文件与固定快照一致。
- 大组件只在完整区块之间拆分，不截断函数、标签或表达式。
- 原有 K4 测试通过；类型、lint 与完整检查的基线问题须如实列明。
- 分段中间态允许缺失后续页面或引用，必须在 PR 描述标明，并按顺序合入。
- 最终组合经独立只读审查；浏览器联调仍在远程 Linux 环境由用户操作。
