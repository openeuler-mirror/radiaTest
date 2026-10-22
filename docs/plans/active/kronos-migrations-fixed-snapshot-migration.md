<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Kronos 迁移脚本合入计划

## 范围

以 Kronos 固定快照 `b0e0bc2` 的 `backend/alembic/versions/` 为依据，补齐 radiaTest `devel`
尚未合入的迁移脚本，使 Alembic 迁移链恢复为可解析的单一头。当前 `devel` 缺 35 个脚本时，
任何 `alembic` 命令都会因悬空 `down_revision` 直接失败。

- 交付范围分四批，每批单提交且增删合计小于 1000 行，按 revision 编号顺序合入。
- 本域 27 个流水线与测试管理迁移分三批；另有 8 个 VM/物理机迁移属另一轨清单，单独一批
  提交并在 PR 描述中注明为代提，对方先提交时该批直接丢弃。
- `backend/tests/test_migration_0035.py`、`test_migration_0036.py` 在含 `0035`/`0036`
  的迁移批次合入后单独提交。

## 明确不做

- 不改任何 `revision` 或 `down_revision`，不改迁移脚本内容和执行顺序。
- 不新增迁移，不 squash 或合并既有迁移，不提供 `downgrade` 内容。
- 不改应用代码、前端及其余测试文件。
- 不在远程数据库实跑 `alembic upgrade`：生产迁移只前进不回退，升级属部署动作。
- 代提的 8 个脚本不计入本域贡献，只在 PR 描述注明来源与原因。

## 实施步骤

1. 每批从 `upstream/devel` 当前头创建独立分支；各批文件互不重叠，因此每批相对 `devel`
   都是单提交且只含本批文件。
2. 按 `migration_<序号>_<描述>.py` 重命名，逐字节复制快照内容，并在文件头加 8 行版权注释。
3. 验证版权头、改名规则、行宽与分批行数上限，运行 Ruff 和 `py_compile`。
4. 在仓库外的临时目录汇总全部 51 个脚本，用 `alembic heads` 与 `alembic history` 校验链
   是否收敛为单一头；同时记录各批合入后的中间态悬空引用。
5. 推送分支，由用户按编号顺序创建并合入 PR。

## 验证标准

- 与快照的差异仅为版权头与文件名；`revision` 与 `down_revision` 逐字节一致。
- 每批相对 `devel` 为单提交，增删合计小于 1000 行。
- Ruff、`py_compile` 与迁移自检脚本通过。
- 全部 35 个脚本到齐后，`alembic heads` 为单一头 `20260911_0047`，`alembic history` 可
  从 `<base>` 走到该头；`test_migration_0035.py` 与 `test_migration_0036.py` 通过。
- 数据库联调遵循远程 Linux 环境边界。
