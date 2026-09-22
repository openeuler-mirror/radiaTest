<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# radiaTest 贡献流程

## 分支生命周期

功能和修复应在独立分支完成，本地合入 `main` 并推送后及时删除已完成的分支。持续开发中的
分支保留，例如 `feat/rerun-failed-cases`。分支使用 `类型/简短-kebab-case-描述` 格式，
类型采用常见的 Conventional Commits 词汇：

| 类型 | 适用范围 | 示例 |
| --- | --- | --- |
| `feat/` | 新增用户可见能力 | `feat/rerun-failed-cases` |
| `fix/` | 修复缺陷 | `fix/test-job-pipeline-seam` |
| `perf/` | 改善已测量的性能问题 | `perf/pipeline-summary-query` |
| `refactor/` | 不改变外部行为的代码重组 | `refactor/test-job-artifacts` |
| `docs/` | 仅文档改动 | `docs/contribution-workflow` |
| `test/` | 仅测试或测试基础设施改动 | `test/pipeline-retry-coverage` |
| `build/` | 构建、依赖或包管理配置 | `build/upgrade-python-dependencies` |
| `ci/` | 持续集成配置或脚本 | `ci/backend-check-cache` |
| `chore/` | 不属于上述类型的维护性工作 | `chore/remove-obsolete-script` |
| `security/` | 安全修复或安全配置调整 | `security/credential-access-check` |
| `hotfix/` | 需要优先处理的线上修复 | `hotfix/resource-lease-release` |

不使用无意义名称、个人姓名、日期或模糊词汇，如 `test`、`update`、`new-feature`。分支名称不写入
真实凭据、内网地址、工单中的敏感信息或客户数据。

| 阶段 | 要求 |
| --- | --- |
| 开始 | 先同步 `main`，再按上述类型创建分支。 |
| 规划 | 命中 `AGENTS.md` 的 Grill 场景时，确认方案并建立计划。 |
| 实现 | 保持改动最小，遵循 `AGENTS.md`；重要架构决策写入 ADR。 |
| 验证 | 运行受影响测试和项目检查，记录通过项、未执行项及环境限制。 |
| 合入 | 待合入分支已提交、验证和审查通过，在本地将分支合入 `main`，完成的计划随即移入 `docs/plans/completed/`；推送 `main` 按授权执行。 |
| 收尾 | 确认推送后的 `origin/main` 已包含该提交后，删除本地和远程已完成的工作分支。 |

## 合入与清理

合入前确认工作区状态和提交基线，工作分支保持可快进（不落后 `main`）；合入动作使用 `git merge --no-ff <type>/<name> -m "<merge commit message>"` 生成 merge commit。功能改动的审查记录写在合入 main 的 merge commit message 中，包含背景、影响范围、迁移或回滚方式、验证结果及审查结论。

确认远程 `main` 已包含分支提交后：

```bash
git branch -d <type>/<name>
git push origin --delete <type>/<name>
```

不得删除尚未合入 `main` 的分支。删除远程分支前先确认其存在；本地或远程分支不存在时，不将该操作视为失败。`main`、发布分支和仍在开发的分支不属于自动清理对象。

## 记录方式

- Git commit：记录具体改动，正文包含问题、处理方式和验证结果。
- 文档记录的分工以 `AGENTS.md` 的“文档责任边界”为准：计划写入 `docs/plans/`，架构与安全取舍写入 `docs/adr/`，产品行为与验收标准写入 `docs/spec/`。
