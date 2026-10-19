<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Kronos 测试迁移计划

## 范围

以 Kronos 固定快照 `b0e0bc2` 和 `kronos-migration/pr-file-map.md` 为依据，
按 K2 清单分批提交测试，每批审查、验证并合入上游 `devel` 后再继续。
当前批次迁移 `backend/tests/test_case_log_upload.py`。
用户已确认直接向 fork 提交、推送并创建上游 PR 的流程。

## 明确不做

- 不引入快照之后的改动，不修改生产行为或补开发功能。
- K4 前端迁移等待 F0a、F0b、F1 前置代码合入。
- 用户已有的 `.gitignore` 未提交改动不纳入迁移。

## 实施步骤

1. 从已包含共享签名适配的上游 `devel` 创建独立测试分支。
2. 搬运固定快照文件，添加版权头，按清单执行格式与签名兼容适配。
3. 验证测试替身使用当前 `RemoteTarget` 参数，运行定向测试和项目检查。
4. 审查最终 diff，在 PR 描述中记录来源、适配、验证和审查结论。
5. 单提交推送至 fork，创建 PR；确认上游合入后推进下一批。

## 验证标准

- 文件与固定快照的差异仅为版权头、门禁规则和现有接口兼容适配。
- 用例日志测试、Python 编译和迁移门禁自检通过。
- 运行 `./scripts/check.sh`；如遇无关基线问题，记录首个失败并验证受影响模块。
- 最终 diff 通过正确性、安全、设计、测试和可读性审查。
- 生产行为已先前合入，本批迁移既有测试，不改动生产实现以制造失败。
- 应用、数据库和浏览器联调遵循远程 Linux 环境边界。
