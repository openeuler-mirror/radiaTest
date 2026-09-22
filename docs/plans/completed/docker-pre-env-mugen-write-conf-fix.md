<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: docker pre_env 补齐 mugen_commit_sha 冻结契约 + 删历史全局 sed

## 状态（2026-09-04 归档）

在 `fix/docker-pin-mugen-sha` 分支按 L2 方案实施：pre_env 里 clone mugen 后
显式 `git fetch --depth=1 origin $KRONOS_MUGEN_COMMIT_SHA` + `git checkout
$KRONOS_MUGEN_COMMIT_SHA`，任一失败即 `exit 1`；删除 step 10 那行历史遗留的
全局 `sed 's#< <(#<<<\$(#g'`；`build_env_file` 增加 `KRONOS_MUGEN_COMMIT_SHA`
字段供 pre_env `source kronos.env` 使用。3 条 TDD 断言（`test_seed_docker_..._pins_
mugen_commit_sha_with_fail_loud_guard` / `test_seed_docker_pre_env_drops_global_sed_
on_mugen_sh` / `test_build_env_file_includes_mugen_commit_sha`）先红后绿；backend
498 passed / 1 skipped，ruff 全通过。

Grill 定档 L2（radiaTest 侧 pin 契约回归），不做 L1 上游 PR、不做 L3 修改用例快照
语义。`--port 22` 显式补上属于"表意改动"，与 argparse `default=22` 等价，砍掉
保持 diff 最小。上游 mugen 侧 `deploy_conf "${*//-c/}"` 加引号是 mugen 自己
的 bug，不属于 radiaTest 需要解决的范围。

## 根因（诊断证据）

kimariyb 触发 `test-docker`（aarch64/x86_64）后 `run_hook(pre_env)` 最后
`mugen.sh -c` 挂：

```
usage: write_conf.py [-h] [--ip IP] [--password PASSWORD] [--port PORT]
                     [--user USER] [--run_remote] [--put_all]
write_conf.py: error: unrecognized arguments:  --ip 172.17.0.2 --password openEuler12#$ --user root
```

**主 bug**：`seed.py::DOCKER_PRE_ENV` step 9：

```sh
git clone --depth=1 https://atomgit.com/openeuler/mugen.git /tmp/mugen
docker cp /tmp/mugen openEuler_test:/home/
```

**从未使用 `TestJob.mugen_commit_sha`**，每次都拉 master tip。所有非-docker
模板（kernel/pkgcmd/pkgmanage/pkgserver）走 `prepare_mugen`，其脚本
`git clone --depth=1 --branch master <url>; git fetch --depth=1 origin <sha>; git
checkout <sha>` **兑现 pin 契约**；docker 因 `mugen_exec_command` 非空跳过
prepare_mugen → 手写的 clone 忘 pin → 破坏契约。

**引爆点**：mugen 上游 `eb987747b (2026-09-02, Fix ShellCheck warnings and
extra_test build issues)` 把 `mugen.sh:453` `deploy_conf ${*//-c/}` 改成
`deploy_conf "${*//-c/}"` **加引号** → word split 被抑制 → write_conf.py 收到整
条字符串作为 positional → argparse 报整套 flag unrecognized。

时间线：`ae2e4a96 (2026-08-25)` = 我们 pin 的 sha；`ae2e4a96` **早于**
`eb987747b`。docker 因为不 pin 拉到最新 master tip → 撞 breaking。非-docker
pin 到 ae2e4a96 → 无影响。

**次要 bug**：`DOCKER_PRE_ENV` step 10 那行全局 `sed 's#< <(#<<<\$(#g'
/home/mugen/mugen.sh` 命中 `mugen.sh:206/330/409` 三处 `mapfile < <(find ...)`。
`bash -n` 检查 sed 前后都合法（sed 不影响 `-c` 分支），但把 process
substitution 换成 here-string 语义不等价（多行 find 结果被合并到一行），是历史
对齐 EulerPipeline 的 dead patch。

## 范围（本次实施）

- **R1 修 pin 逻辑**：`build_env_file` 加 `KRONOS_MUGEN_COMMIT_SHA`，pre_env
  step 9 clone 后 `git fetch --depth=1 origin "$KRONOS_MUGEN_COMMIT_SHA"; git
  checkout "$KRONOS_MUGEN_COMMIT_SHA"`，任一失败即 `exit 1`（不 `|| true` 吞）。
- **R2 删 risky 全局 sed**：step 10 那行 sed 整条移除，pre_env step 10 名字改成
  `dep_install + mugen -c`。
- **R3 单测**：3 条契约字符串断言。
- **R4 kimariyb 端到端复验**（触发 docker 流水线，见下）——由用户在 push+部署后
  手工确认现象，本文档归档前跑完。

## 明确不做

- **L1 上游 PR 修 mugen.sh `deploy_conf "${*//-c/}"` 引号**：属 mugen 侧 bug，
  radiaTest 不承担修复责任；pin sha 后走 ae2e4a96 = 无引号版，本次不受影响。
- **L3 "跟 master 一起漂"**：违反 `TestJob.mugen_commit_sha` 冻结语义，破坏用例
  版本可复现，明确不做。
- **pre_env.sh 里显式补 `--port 22`**：`write_conf.py` argparse `default=22`，
  补与不补行为等价；radiaTest 全局硬编码 22 是既有事实，若要支持自定义端口需改
  `configure_mugen_node + run_ssh_command + build_env_file + create-vm.sh`
  四处的完整方案，不藏在 pre_env 里。
- **prepare_mugen 里 `git fetch ... || true`** 语义：非-docker 一直走这条且
  从未 observed 失败，本次不动。
- **数据模型/API/权限/前端**：不改。
- **post_env 撞"环境已被清理"次生 bug**（kernel 10173 `kronos.env: No such file`）：
  早于本次代码，属另一议题。

## 实施步骤

1. `backend/app/modules/test_management/frameworks/mugen_runner.py::build_env_file`
   加 `KRONOS_MUGEN_COMMIT_SHA: job.mugen_commit_sha` 一行
2. `backend/app/modules/pipelines/seed.py::DOCKER_PRE_ENV` step 9 用 fetch+
   checkout pin sha + guard 显式 `exit 1`；step 10 那行 sed 删掉
3. 单测（`tests/test_seed.py` 2 条 + `tests/test_test_management.py` 1 条）先
   红后绿
4. `./scripts/check.sh` 全量：backend 498 passed / 1 skipped（原 495 +
   3 新增），docs/scripts/frontend 全通过

## 验证标准（结果）

- 单测：
  - `test_build_env_file_includes_mugen_commit_sha`：`SimpleNamespace` 走
    `build_env_file`，输出含 `KRONOS_MUGEN_COMMIT_SHA=<sha>` ✓
  - `test_seed_docker_pre_env_pins_mugen_commit_sha_with_fail_loud_guard`：
    `git fetch --depth=1 origin "$KRONOS_MUGEN_COMMIT_SHA"` + `git checkout` +
    `exit 1` 三条字面存在 ✓
  - `test_seed_docker_pre_env_drops_global_sed_on_mugen_sh`：`s#< <(#<<<` 不再
    出现 ✓
- `./scripts/check.sh`：EXIT=0 ✓
- kimariyb 端到端（**用户在 push+部署后触发 `test-docker` 手工**）：
  - `test-docker` 触发后 `run_hook(pre_env)` **成功**，事件流出现
    `env_progress 1..10/10` + `pre_env_done`（而不是 `mugen.sh -c` 报
    `write_conf.py: unrecognized`）
  - `docker 容器内 /home/mugen/mugen.sh` 是 pin 到的 sha 版本
  - 至少 1 条 `case_started` 事件（表示进入 run_case 循环）
