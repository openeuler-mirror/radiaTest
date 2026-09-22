<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0027：RunJob 失败用例按选重跑

## 状态

已被 [ADR 0028](0028-rerun-cases-in-source-environment.md) 取代(Superseded)。

## 决策

- 已登录用户可在终态 Pipeline RunJob 中选择失败的 Mugen Case Run 重跑。
- 每次重跑创建同一 Run 下的新 RunJob，保存直接来源、根来源和 suite/case 选择快照；同名
  用例去重，支持再次重跑。
- 重跑从来源 Test Job 的持久化快照复制执行输入，只替换用例选择；原始执行事实不可变。
- 看板和 Run 状态使用每条重跑链的最新 RunJob，来源详情保留完整链路；每个执行的日志独立显示，
  并以时间和重跑次数分隔。

## 取舍

将重跑表示为新的 RunJob 而非更新原结果，保留可审查的失败事实，并复用既有队列、执行和日志
链路。只支持可直接映射 Mugen suite/case 的失败项，避免把环境错误或解析器派生结果误当作可执行
测试。
