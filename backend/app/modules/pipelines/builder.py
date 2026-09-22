# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Pipeline TestJob builder。

绕开 create_test_job（其 env_type=vm 策略门和手动选 case API 不适配流水线），
直接拿 case_filter 产物 + 模板字段建 TestJob/EnvSet/Node/CaseRun，env_type 可为 physical。
case_filter 四分派：none / repodata_packages / repodata_union / service_test_cases。
"""

from __future__ import annotations

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.modules.pipelines.case_planner import plan_cases
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineExecution,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.pipelines.repodata import fetch_service_packages, fetch_update_packages
from app.modules.test_management.frameworks.dangerous_cases import (
    resolve_case_danger,
)
from app.modules.test_management.models import (
    MugenCase,
    TestCaseRun,
    TestCaseRunStatus,
    TestEnvNode,
    TestEnvNodeStatus,
    TestEnvSet,
    TestEnvSetStatus,
    TestEnvType,
    TestJob,
    TestJobStatus,
)
from app.modules.test_management.schemas import TestCaseSelection
from app.modules.test_management.service import (
    TestCaseSelectionError,
    create_job_env_sets,
    current_mugen_commit_sha,
    distribute_bundles,
    record_test_job_event,
    select_cases,
)


def _resolve_env_type(run_job: PipelineRunJob) -> TestEnvType:
    if run_job.env_type == TestEnvType.PHYSICAL.value:
        return TestEnvType.PHYSICAL
    return TestEnvType.VM




def _select_suite_cases(
    db: Session,
    *,
    suite_name: str,
    env_type: TestEnvType,
    case_names: list[str] | None = None,
) -> list[MugenCase]:
    bundles = select_cases(
        db,
        selections=[TestCaseSelection(suite_name=suite_name, case_names=case_names)],
        env_type=env_type,
    )
    return bundles[0] if bundles else []


def _fetch_mugen_cases(
    db: Session,
    matches: list[tuple[str, str]],
) -> list[MugenCase]:
    if not matches:
        return []
    rows = db.execute(
        select(MugenCase).where(
            tuple_(MugenCase.suite_name, MugenCase.case_name).in_(matches)
        )
    ).scalars().all()
    return rows


def _resolve_cases(
    db: Session,
    *,
    template: TestModuleTemplate,
    run_job: PipelineRunJob,
    config: PipelineConfig,
    version: str,
) -> tuple[list[MugenCase], list[str], list[str]]:
    """返回该 RunJob 的 (cases_to_run, no_case_packages, update_packages)。"""
    env_type = _resolve_env_type(run_job)

    if run_job.rerun_case_selections:
        matches = [
            (selection["suite_name"], selection["case_name"])
            for selection in run_job.rerun_case_selections
        ]
        return _fetch_mugen_cases(db, matches), [], []

    if template.case_filter == "repodata_packages":
        from app.core.config import get_settings

        packages = fetch_update_packages(
            repo_base_url=get_settings().vm_openeuler_update_repo_root,
            version=version,
        )
        plan = plan_cases(db, packages=packages)
        if template.env_type == "both":
            matched = plan.vm_cases + plan.physical_cases
        else:
            matched = (
                plan.vm_cases if env_type == TestEnvType.VM else plan.physical_cases
            )
        cases = _fetch_mugen_cases(
            db, [(m.suite_name, m.case_name) for m in matched]
        )
        return cases, plan.no_case_packages, packages

    if template.case_filter == "repodata_union":
        # pkgunion 专用：repodata 源包名路(pkgcmd)与 filelists 服务路(pkgserver)的
        # 并集。两路重叠的 service 用例只执行一次（按 (suite_name, case_name) 去重）。
        from app.core.config import get_settings

        packages = fetch_update_packages(
            repo_base_url=get_settings().vm_openeuler_update_repo_root,
            version=version,
        )
        plan = plan_cases(db, packages=packages)
        if template.env_type == "both":
            repodata_matched = plan.vm_cases + plan.physical_cases
        else:
            repodata_matched = (
                plan.vm_cases if env_type == TestEnvType.VM else plan.physical_cases
            )
        services = fetch_service_packages(
            repo_base_url=get_settings().vm_openeuler_update_repo_root,
            version=version,
            arch=run_job.arch,
        )
        service_case_names = {f"oe_test_{stype}_{sname}" for _, sname, stype in services}
        service_matched = (
            db.execute(
                select(MugenCase).where(MugenCase.case_name.in_(service_case_names))
            )
            .scalars()
            .all()
        )
        if template.env_type != "both":
            service_matched = [c for c in service_matched if c.env_type == env_type.value]
        merged: dict[tuple[str, str], MugenCase] = {}
        for case in _fetch_mugen_cases(
            db, [(m.suite_name, m.case_name) for m in repodata_matched]
        ):
            merged[(case.suite_name, case.case_name)] = case
        for case in service_matched:
            merged.setdefault((case.suite_name, case.case_name), case)
        # update_packages 取两路包名并集（保序去重），供 pre_env 补装 update 轮新增包。
        union_packages = list(
            dict.fromkeys([*packages, *(pname for pname, _, _ in services)])
        )
        return list(merged.values()), plan.no_case_packages, union_packages

    if template.case_filter == "service_test_cases":
        from app.core.config import get_settings

        services = fetch_service_packages(
            repo_base_url=get_settings().vm_openeuler_update_repo_root,
            version=version,
            arch=run_job.arch,
        )
        case_names = {f"oe_test_{stype}_{sname}" for _, sname, stype in services}
        matched = list(
            db.execute(
                select(MugenCase).where(MugenCase.case_name.in_(case_names))
            ).scalars().all()
        )
        # 返回去重的包名供 pre_env 安装（不是全部 update 包）
        pkg_names = list({pname for pname, _, _ in services})
        return matched, [], pkg_names

    # case_filter == "none"
    case_selections = config.config_data.get("case_selections")
    if case_selections is not None:
        # direct_run (release)：每架构一套环境跑全部选中 suite 的 case。
        # 空 case_names 等价全选。不按 env_type 过滤：vm 用例进 VM 环境集，
        # 物理机用例由 both 分支按 release_physical_enabled 决定执行（建物理
        # 环境集租用物理机）或 NOT_EXECUTED 跳过。
        selections = [
            TestCaseSelection(
                suite_name=cs.get("suite_name"),
                case_names=(cs.get("case_names") or None),
            )
            for cs in case_selections
        ]
        cases = _resolve_selections_cases(db, selections)
        return cases, [], []
    else:
        # update 的 none 模板（kernel/docker）：单 suite 全选或默认 case。
        case_names = ["oe_test_ltp"] if template.name == "kernel" else None
        cases = _select_suite_cases(
            db, suite_name=template.suite_name, env_type=env_type, case_names=case_names
        )
    return cases, [], []


def _resolve_selections_cases(
    db: Session, selections: list[TestCaseSelection]
) -> list[MugenCase]:
    """direct_run 用例解析：按选择展开全部 case，不做 env_type 过滤。

    vm 用例进 VM 环境集；物理机用例由 both 分支按 release_physical_enabled
    决定建可执行物理环境集还是 NOT_EXECUTED 跳过。suite/case 不存在仍抛
    TestCaseSelectionError（配置错误 fail-fast）。
    """
    from app.modules.test_management.service import cases_by_suite

    grouped = cases_by_suite(db)
    cases: list[MugenCase] = []
    for selection in selections:
        suite_cases = grouped.get(selection.suite_name)
        if not suite_cases:
            raise TestCaseSelectionError(f"Suite not found: {selection.suite_name}")
        if selection.case_names is None:
            cases.extend(suite_cases)
            continue
        by_name = {case.case_name: case for case in suite_cases}
        for case_name in selection.case_names:
            case = by_name.get(case_name)
            if case is None:
                raise TestCaseSelectionError(
                    f"Case not found: {selection.suite_name}/{case_name}"
                )
            cases.append(case)
    return cases


def build_test_job_for_run_job(
    db: Session,
    *,
    run_job: PipelineRunJob,
    config: PipelineConfig,
    template: TestModuleTemplate,
    version: str,
    actor_user_id: str,
) -> TestJob:
    env_type = _resolve_env_type(run_job)
    source_job: TestJob | None = None
    selected_source_cases: list[TestCaseRun] = []
    selected_root_cases: dict[str, TestCaseRun] = {}
    source_run_job: PipelineRunJob | None = None
    if run_job.rerun_source_run_job_id:
        source_run_job = db.get(PipelineRunJob, run_job.rerun_source_run_job_id)
        if source_run_job is not None and source_run_job.test_job_id is not None:
            source_job = db.get(TestJob, source_run_job.test_job_id)
    if source_job is not None:
        selected_ids = [
            item["case_run_id"] for item in run_job.rerun_case_selections
        ]
        root_run_job_id = (
            source_run_job.rerun_root_run_job_id or source_run_job.id
            if source_run_job is not None
            else run_job.rerun_root_run_job_id
        )
        chain_test_job_ids = list(
            db.execute(
                select(PipelineRunJob.test_job_id).where(
                    (PipelineRunJob.id == root_run_job_id)
                    | (PipelineRunJob.rerun_root_run_job_id == root_run_job_id),
                    PipelineRunJob.test_job_id.isnot(None),
                )
            ).scalars()
        )
        selected_source_cases = list(
            db.execute(
                select(TestCaseRun)
                .where(
                    TestCaseRun.id.in_(selected_ids),
                    TestCaseRun.job_id.in_(chain_test_job_ids),
                )
                .order_by(TestCaseRun.env_set_id, TestCaseRun.id)
            ).scalars()
        )
        if len(selected_source_cases) != len(set(selected_ids)):
            raise ValueError("Rerun source cases no longer match the rerun chain")
        root_case_ids = {
            item.rerun_root_case_run_id or item.id for item in selected_source_cases
        }
        root_cases_rows = (
            db.execute(
                select(TestCaseRun).where(TestCaseRun.id.in_(root_case_ids))
            ).scalars()
        )
        root_cases = {
            item.id: item
            for item in root_cases_rows
        }
        if len(root_cases) != len(root_case_ids):
            raise ValueError("Rerun root cases no longer exist")
        selected_root_cases = {
            item.id: root_cases[item.rerun_root_case_run_id or item.id]
            for item in selected_source_cases
        }
        cases: list[MugenCase] = []
        no_case_packages: list[str] = []
        packages = list(source_job.update_packages)
    else:
        cases, no_case_packages, packages = _resolve_cases(
            db, template=template, run_job=run_job, config=config, version=version
        )

    # 危险用例过滤：命中即不进执行清单(不生成 TestCaseRun),由执行事件留痕。
    # rerun 分支 cases 为空(复用来源执行记录),天然无危险用例。
    blocked: list[tuple[MugenCase, str]] = []
    safe_cases: list[MugenCase] = []
    for case in cases:
        reason = resolve_case_danger(
            case.case_name, scanned_reason=case.dangerous_reason
        )
        if reason:
            blocked.append((case, reason))
        else:
            safe_cases.append(case)
    cases = safe_cases

    # 解析 image_round：trigger 级(execution.image_round)覆盖 config 级。
    # 沿 run_job → run → execution 取覆盖值；execution.image_round 为 None
    # (未传 trigger 级覆盖)时回退到 config。
    resolved_image_round = config.image_round
    run = db.get(PipelineRun, run_job.pipeline_run_id)
    if run is not None and run.execution_id is not None:
        execution = db.get(PipelineExecution, run.execution_id)
        if execution is not None and execution.image_round:
            resolved_image_round = execution.image_round
    if not resolved_image_round:
        resolved_image_round = "official"

    # release (direct_run) 内核参数快照入 pipeline_extras；rerun 复用来源环境不建新 VM → None。
    # update 的 config_data 无 case_selections → extras=None，行为不变。
    if source_job is None and config.config_data.get("case_selections") is not None:
        kernel_variant = config.config_data.get("kernel_variant")
        kernel_rpm_url = config.config_data.get("kernel_rpm_url")
        extras: dict[str, object] | None = {}
        if kernel_variant:
            extras["kernel_variant"] = kernel_variant
        if kernel_rpm_url:
            extras["kernel_rpm_url"] = kernel_rpm_url
        extras = extras or None
    else:
        extras = None

    job = TestJob(
        creator_user_id=actor_user_id,
        name=(
            f"{source_job.name}-rerun-{run_job.id[:8]}"
            if source_job is not None
            else
            f"pipeline-{config.pipeline_type}-{template.name}-"
            f"{run_job.arch}-{run_job.env_type or 'vm'}-{version}"
        ),
        status=TestJobStatus.PENDING.value,
        framework=source_job.framework if source_job else template.test_framework,
        env_type=source_job.env_type if source_job else env_type.value,
        dist=source_job.dist if source_job else config.dist,
        os_version=source_job.os_version if source_job else version,
        image_round=source_job.image_round if source_job else resolved_image_round,
        arch=source_job.arch if source_job else run_job.arch,
        mugen_commit_sha=(
            source_job.mugen_commit_sha if source_job else current_mugen_commit_sha(db)
        ),
        env_set_num=(
            len({item.env_set_id for item in selected_root_cases.values()})
            if source_job
            else template.env_set_num
        ),
        keep_failed_env=source_job.keep_failed_env if source_job else False,
        keep_env=source_job.keep_env if source_job else True,
        pre_env_script=source_job.pre_env_script if source_job else template.pre_env_script,
        rerun_env_script=(
            source_job.rerun_env_script if source_job else template.rerun_env_script
        ),
        post_env_script=source_job.post_env_script if source_job else template.post_env_script,
        rerun_source_job_id=source_job.id if source_job else None,
        physical_usage_scenario=(
            source_job.physical_usage_scenario
            if source_job
            else f"{template.name}-update"
        ),
        mugen_exec_command=(
            source_job.mugen_exec_command if source_job else template.mugen_exec_command
        ),
        result_parser=source_job.result_parser if source_job else template.result_parser,
        update_packages=packages,
        task_id=run_job.task_id,
        pipeline_extras=extras,
    )
    db.add(job)
    db.flush()

    if blocked:
        record_test_job_event(
            db,
            job=job,
            phase="cases_filtered",
            level="warning",
            message=(
                f"危险用例规则跳过 {len(blocked)} 个："
                + "、".join(f"{case.case_name}({reason})" for case, reason in blocked)
            ),
        )

    if source_job is not None:
        source_env_set_ids = {item.env_set_id for item in selected_root_cases.values()}
        source_env_sets_rows = (
            db.execute(
                select(TestEnvSet).where(TestEnvSet.id.in_(source_env_set_ids))
            ).scalars()
        )
        source_env_sets = {
            item.id: item
            for item in source_env_sets_rows
        }
        for source_env_set in sorted(
            source_env_sets.values(), key=lambda item: item.set_index
        ):
            env_set = TestEnvSet(
                job=job,
                set_index=source_env_set.set_index,
                node_num=source_env_set.node_num,
                env_type=source_env_set.env_type,
                add_disk_num=source_env_set.add_disk_num,
                add_nic_num=source_env_set.add_nic_num,
                rerun_source_env_set_id=source_env_set.id,
            )
            db.add(env_set)
            db.flush()
            for source_node in source_env_set.nodes:
                db.add(
                    TestEnvNode(
                        env_set=env_set,
                        node_index=source_node.node_index,
                        role=source_node.role,
                        status=TestEnvNodeStatus.READY.value,
                        vm_request_id=source_node.vm_request_id,
                        resource_id=source_node.resource_id,
                        primary_ip=source_node.primary_ip,
                    )
                )
            for source_case in selected_source_cases:
                if selected_root_cases[source_case.id].env_set_id != source_env_set.id:
                    continue
                db.add(
                    TestCaseRun(
                        job=job,
                        env_set=env_set,
                        suite_name=source_case.suite_name,
                        case_name=source_case.case_name,
                        rerun_source_case_run_id=source_case.id,
                        rerun_root_case_run_id=(
                            source_case.rerun_root_case_run_id or source_case.id
                        ),
                    )
                )
    # both 模块:按 env_type 分 VM/physical 两组 env_set;其余:按 env_set_num 分配
    elif template.env_type == "both":
        vm_cases = [c for c in cases if c.env_type == TestEnvType.VM.value]
        physical_cases = [c for c in cases if c.env_type == "physical"]
        # release 默认关闭物理执行（跳过为 NOT_EXECUTED），由配置开关显式开启；
        # update 模块维持默认开启的原有行为。
        physical_default = template.name != "release"
        physical_enabled = config.config_data.get(
            f"{template.name}_physical_enabled", physical_default
        )
        assigned: list[list[MugenCase]] = []
        if vm_cases:
            assigned.append(vm_cases)
        if physical_cases and physical_enabled:
            assigned.append(physical_cases)
        create_job_env_sets(db, job=job, assigned_cases=assigned)
        # 物理 flag off: 照建 physical env_set（可见）+ case_runs NOT_EXECUTED + 不建 node
        if physical_cases and not physical_enabled:
            phys_env_set = TestEnvSet(
                job=job,
                set_index=len(job.env_sets) + 1,
                node_num=0,
                env_type="physical",
                add_disk_num=0,
                add_nic_num=0,
                status=TestEnvSetStatus.NOT_EXECUTED.value,
            )
            db.add(phys_env_set)
            db.flush()
            for case in physical_cases:
                db.add(
                    TestCaseRun(
                        job=job,
                        env_set=phys_env_set,
                        suite_name=case.suite_name,
                        case_name=case.case_name,
                        status=TestCaseRunStatus.NOT_EXECUTED.value,
                    )
                )
    else:
        bundles = [[case] for case in cases]
        assigned = distribute_bundles(bundles, env_set_num=template.env_set_num)
        create_job_env_sets(db, job=job, assigned_cases=assigned)

    # pkgcmd no_case 包建 NO_CASE TestCaseRun（挂到第一个 env_set，run_case 跳过 NO_CASE）
    if no_case_packages and job.env_sets:
        env_set = job.env_sets[0]
        for pkg in no_case_packages:
            db.add(
                TestCaseRun(
                    job=job,
                    env_set=env_set,
                    suite_name=pkg,
                    case_name=pkg,
                    status=TestCaseRunStatus.NO_CASE.value,
                )
            )

    db.flush()
    run_job.test_job_id = job.id
    db.flush()
    return job
