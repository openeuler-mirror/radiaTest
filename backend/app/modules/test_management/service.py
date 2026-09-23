# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

from redis import Redis
from sqlalchemy import delete, distinct, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings
from app.core.pagination import PAGE_SIZE, PageParams
from app.modules.audit.service import record_audit_log
from app.modules.resources.models import OccupancyStatus, Resource
from app.modules.tasks.models import TaskEvent
from app.modules.tasks.service import list_task_events, record_task_event
from app.modules.test_management.errors import TestJobDeleteError
from app.modules.test_management.frameworks.mugen import parse_suite_documents
from app.modules.test_management.models import (
    MugenCase,
    TestCaseRun,
    TestCaseRunDetail,
    TestEnvNode,
    TestEnvSet,
    TestEnvType,
    TestFramework,
    TestJob,
    TestJobStatus,
    TestLogArtifact,
)
from app.modules.test_management.pipeline_reads import (
    is_test_job_referenced_by_pipeline,
    resolve_pipeline_origins,
)
from app.modules.test_management.schemas import (
    MugenCaseSyncRead,
    MugenCaseSyncRequest,
    PipelineOriginRead,
    TestCaseSelection,
    TestJobBatchDeleteResult,
    TestJobConfig,
    TestJobCreate,
    TestJobDetailRead,
    TestJobRead,
)
from app.modules.users.models import User, UserRole
from app.modules.vms.image_discovery import ImageDiscoveryError, VMImage, discover_images
from app.worker import celery_app

# 测试管理领域服务：Mugen 用例索引同步、测试任务(TestJob)创建与入队、
# 用例选择与环境集分配。权限规则集中在此处，路由只做请求解析与状态码映射。

# 任务事件归类常量，写入 task_events 用于页面详情与中断恢复。
TASK_TYPE_MUGEN_SYNC = "mugen_sync"
TASK_TYPE_TEST_JOB = "test_job"
SUBJECT_TYPE_MUGEN_SYNC = "mugen_sync"
SUBJECT_TYPE_TEST_JOB = "test_job"
SUBJECT_ID_MUGEN_SYNC = "mugen"
CONTROL_NODE_ROLE = "control"
PEER_NODE_ROLE = "peer"
# Mugen 同步互斥锁：同一时刻只允许一个同步任务，靠 Redis SET NX + TTL 抢锁，
# 用 Lua 比对 token 再释放，避免持有者过期后误删别人的锁。
MUGEN_SYNC_LOCK_KEY = "kronos:mugen-sync"
RELEASE_MUGEN_SYNC_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""


class TestManagementPolicyError(Exception):
    """测试管理权限或业务规则被违反(如非 ADMIN 触发 Mugen 同步)。"""


class TestCaseSelectionError(Exception):
    """用例选择不合法(用例不存在、与 env_type 不匹配、节点数超限)。"""


class TestJobQueueUnavailableError(Exception):
    """Celery broker 未配置或投递失败，测试任务无法入队。"""


class TestJobImageIndexUnavailableError(Exception):
    """镜像索引不可读，无法校验所选镜像。"""


class TestJobImageSelectionError(Exception):
    """所选镜像不在当前镜像索引中。"""


class MugenSyncConflictError(Exception):
    """已有 Mugen 同步在运行，抢锁失败。"""


class MugenSyncQueueUnavailableError(Exception):
    """Celery broker 未配置，Mugen 同步无法入队。"""


@dataclass(frozen=True)
class ResolvedTestJobConfig:
    mugen_commit_sha: str
    bundles: list[list[MugenCase]]


def require_mugen_sync_admin(actor: User) -> None:
    """Mugen 同步入口鉴权：仅 ADMIN 可触发，否则抛 TestManagementPolicyError。"""
    if actor.role != UserRole.ADMIN.value:
        raise TestManagementPolicyError("Only ADMIN can manage Mugen sync")


def redis_client() -> Redis:
    settings = get_settings()
    if not settings.celery_broker_url:
        raise MugenSyncQueueUnavailableError("Celery broker is not configured")
    return Redis.from_url(settings.celery_broker_url)


def release_mugen_sync_lock(token: str) -> None:
    """释放 Mugen 同步锁。broker 不可用时静默返回，保证 finally 不抛二次异常。"""
    try:
        client = redis_client()
    except MugenSyncQueueUnavailableError:
        return
    client.eval(RELEASE_MUGEN_SYNC_LOCK_SCRIPT, 1, MUGEN_SYNC_LOCK_KEY, token)


def acquire_mugen_sync_lock(token: str | None = None) -> str:
    """以 token 抢 Mugen 同步锁(SET NX + TTL)。抢失败抛 MugenSyncConflictError。

    返回的 token 必须原样传给 release，Lua 脚本据此比对，确保不会误删
    因 TTL 过期后由其他进程重新获取的锁。
    """
    token = token or str(uuid4())
    settings = get_settings()
    acquired = redis_client().set(
        MUGEN_SYNC_LOCK_KEY,
        token,
        nx=True,
        ex=settings.mugen_sync_lock_ttl_seconds,
    )
    if not acquired:
        raise MugenSyncConflictError("Mugen sync is already running")
    return token


def enqueue_mugen_case_sync(db: Session, *, actor: User) -> str:
    """入队 Mugen 用例同步任务。仅 ADMIN 可调用。

    先抢锁再投递 Celery；投递失败时立即释放锁并把异常转为
    MugenSyncQueueUnavailableError，避免锁泄漏。投递成功后写一条 queued 事件。
    """
    require_mugen_sync_admin(actor)
    task_id = str(uuid4())
    token = acquire_mugen_sync_lock(task_id)
    try:
        celery_app.send_task(
            "app.modules.test_management.tasks.sync_mugen_cases",
            args=[actor.id, token],
            task_id=task_id,
        )
    except Exception as exc:  # noqa: BLE001
        release_mugen_sync_lock(token)
        raise MugenSyncQueueUnavailableError(str(exc)) from exc

    record_task_event(
        db,
        task_type=TASK_TYPE_MUGEN_SYNC,
        subject_type=SUBJECT_TYPE_MUGEN_SYNC,
        subject_id=SUBJECT_ID_MUGEN_SYNC,
        celery_task_id=task_id,
        phase="queued",
        message="Mugen 用例同步已进入异步队列",
    )
    db.flush()
    return task_id


def list_mugen_sync_events(db: Session, *, actor: User) -> list[TaskEvent]:
    require_mugen_sync_admin(actor)
    return list_task_events(
        db,
        subject_type=SUBJECT_TYPE_MUGEN_SYNC,
        subject_id=SUBJECT_ID_MUGEN_SYNC,
    )


def enqueue_test_job(job: TestJob) -> str:
    """把测试任务投递到 Celery。broker 未配置或投递失败时抛 TestJobQueueUnavailableError。"""
    if not get_settings().celery_broker_url:
        raise TestJobQueueUnavailableError("Celery broker is not configured")
    try:
        task = celery_app.send_task("app.modules.test_management.tasks.run_test_job", args=[job.id])
    except Exception as exc:  # noqa: BLE001
        raise TestJobQueueUnavailableError(str(exc)) from exc
    return str(task.id)


def sync_mugen_cases(
    db: Session,
    payload: MugenCaseSyncRequest,
    *,
    dangerous_reasons: dict[tuple[str, str], str] | None = None,
) -> MugenCaseSyncRead:
    """全量替换 Mugen 用例索引：先清空 mugen_cases 再批量写入本次解析结果。

    全量替换是有意的——同步是整库快照，commit_sha 统一为本次抓取的版本，
    避免新旧用例混存导致选择时拿到跨版本数据。ltp(kernel) suite 在 radiaTest
    中是物理机专用，即便 mugen 元数据标注 vm 也强制覆盖为 physical。

    dangerous_reasons 是同步任务扫描仓库脚本产出的危险标记(只含脚本扫描
    结果)；名字规则在过滤时动态计算，不落库。
    """
    definitions = parse_suite_documents(payload.suites)
    scan_reasons = dangerous_reasons or {}
    db.execute(delete(MugenCase))
    for definition in definitions:
        # ltp (kernel) suite is physical-only in radiaTest; mugen metadata may say
        # vm, override so the kernel physical RunJob can select these cases.
        env_type = (
            "physical" if definition.suite_name == "ltp" else definition.env_type
        )
        scan_reason = scan_reasons.get(
            (definition.suite_name, definition.case_name)
        )
        db.add(
            MugenCase(
                suite_name=definition.suite_name,
                case_name=definition.case_name,
                env_type=env_type,
                node_num=definition.node_num,
                add_disk_num=definition.add_disk_num,
                add_nic_num=definition.add_nic_num,
                raw_data=definition.raw_data,
                commit_sha=payload.commit_sha,
                dangerous=scan_reason is not None,
                dangerous_reason=scan_reason,
            )
        )
    db.flush()
    return MugenCaseSyncRead(commit_sha=payload.commit_sha, case_count=len(definitions))


def current_mugen_commit_sha(db: Session) -> str:
    """返回当前 Mugen 索引的唯一 commit_sha。

    不变量：索引中只允许存在一个 commit 版本。为空或多版本都视为索引不可用，
    抛 TestCaseSelectionError——此时无法确定用例归属，必须先重新同步。
    """
    commits = list(db.execute(select(distinct(MugenCase.commit_sha))).scalars().all())
    if not commits:
        raise TestCaseSelectionError("Mugen 用例索引为空")
    if len(commits) != 1:
        raise TestCaseSelectionError("Mugen 用例索引包含多个提交版本")
    return commits[0]


def list_mugen_cases(
    db: Session,
    *,
    suite: str | None = None,
    case: str | None = None,
    env_type: str | None = None,
) -> list[MugenCase]:
    statement = select(MugenCase)
    conditions = _mugen_case_conditions(suite=suite, case=case, env_type=env_type)
    if conditions:
        statement = statement.where(*conditions)
    statement = statement.order_by(MugenCase.suite_name.asc(), MugenCase.case_name.asc())
    return list(db.execute(statement).scalars().all())


def _mugen_case_conditions(
    *,
    suite: str | None,
    case: str | None,
    env_type: str | None,
) -> list[ColumnElement[bool]]:
    conditions = []
    if suite:
        conditions.append(MugenCase.suite_name.ilike(f"%{suite.strip()}%"))
    if case:
        conditions.append(MugenCase.case_name.ilike(f"%{case.strip()}%"))
    if env_type:
        conditions.append(MugenCase.env_type == env_type.strip())
    return conditions


def paginate_mugen_cases(
    db: Session,
    *,
    pagination: PageParams,
    suite: str | None = None,
    case: str | None = None,
    env_type: str | None = None,
) -> tuple[list[MugenCase], int]:
    statement = select(MugenCase)
    count_statement = select(func.count(MugenCase.id))
    conditions = _mugen_case_conditions(suite=suite, case=case, env_type=env_type)
    if conditions:
        statement = statement.where(*conditions)
        count_statement = count_statement.where(*conditions)
    statement = (
        statement.order_by(
            MugenCase.suite_name.asc(),
            MugenCase.case_name.asc(),
            MugenCase.id,
        )
        .offset(pagination.offset)
        .limit(PAGE_SIZE)
    )
    items = list(db.execute(statement).scalars().all())
    total = db.scalar(count_statement) or 0
    return items, total


def paginate_test_jobs(
    db: Session,
    *,
    actor: User,
    show_all: bool,
    pagination: PageParams,
    name: str | None = None,
    status: str | None = None,
    creator: str | None = None,
) -> tuple[list[TestJob], int]:
    """按权限范围和筛选条件分页返回任务。

    权限边界：show_all=False 时强制只返回 actor 自己的任务，creator 筛选仅
    在 show_all=True 时生效，防止普通用户借 creator 参数越权枚举他人任务。
    """
    statement = select(TestJob)
    count_statement = select(func.count(TestJob.id))
    conditions: list[ColumnElement[bool]] = []
    if not show_all:
        conditions.append(TestJob.creator_user_id == actor.id)
    else:
        if creator:
            creator_user = (
                db.execute(select(User).where(User.username == creator)).scalar_one_or_none()
            )
            # 指定创建人不存在时返回空集，而不是退化为全量列表。
            conditions.append(TestJob.creator_user_id == (creator_user.id if creator_user else ""))
    if name:
        # 转义 LIKE 通配符，让名称按字面量匹配用户输入。
        escaped = (
            name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        conditions.append(TestJob.name.ilike(f"%{escaped}%", escape="\\"))
    if status:
        conditions.append(TestJob.status == status)
    for condition in conditions:
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    statement = (
        statement.order_by(TestJob.created_at.desc(), TestJob.id)
        .offset(pagination.offset)
        .limit(PAGE_SIZE)
    )
    items = list(db.execute(statement).scalars().all())
    total = db.scalar(count_statement) or 0
    return items, total


def get_test_job(db: Session, job_id: int) -> TestJob | None:
    statement = (
        select(TestJob)
        .options(
            selectinload(TestJob.env_sets).selectinload(TestEnvSet.nodes),
            selectinload(TestJob.env_sets).selectinload(TestEnvSet.case_runs),
            selectinload(TestJob.case_runs),
        )
        .where(TestJob.id == job_id)
    )
    return db.execute(statement).scalars().one_or_none()


def serialize_test_job(
    db: Session,
    job: TestJob,
    *,
    pipeline_origin: PipelineOriginRead | None = None,
    pipeline_origin_deleted: bool = False,
) -> TestJobRead:
    creator = db.get(User, job.creator_user_id)
    return TestJobRead(
        id=job.id,
        creator_user_id=job.creator_user_id,
        creator_username=creator.username if creator else None,
        name=job.name,
        status=job.status,
        framework=job.framework,
        env_type=job.env_type,
        dist=job.dist,
        os_version=job.os_version,
        image_round=job.image_round,
        arch=job.arch,
        mugen_commit_sha=job.mugen_commit_sha,
        env_set_num=job.env_set_num,
        keep_failed_env=job.keep_failed_env,
        pre_env_script=job.pre_env_script,
        post_env_script=job.post_env_script,
        task_id=job.task_id,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        pipeline_origin=pipeline_origin,
        pipeline_origin_deleted=pipeline_origin_deleted,
    )


def serialize_test_job_detail(db: Session, job: TestJob) -> TestJobDetailRead:
    base = serialize_test_job(db, job).model_dump()
    return TestJobDetailRead(
        **base,
        env_sets=job.env_sets,
        case_runs=job.case_runs,
    )


def attach_pipeline_origins(
    db: Session, jobs: Sequence[TestJob]
) -> dict[int, tuple[PipelineOriginRead | None, bool]]:
    """批量解析任务来源流水线（实现由装配层注册，见 pipeline_reads 注入缝）。"""
    return resolve_pipeline_origins(db, [job.id for job in jobs])


TEST_JOB_TARGET_TYPE = "test_job"
# 只有流水线 builder 会把 keep_env 置 True；普通任务创建接口不暴露该字段。
TEST_JOB_TERMINAL_STATUSES = {
    TestJobStatus.SUCCEEDED.value,
    TestJobStatus.FAILED.value,
    TestJobStatus.ERROR.value,
}


def _has_retained_env(db: Session, job: TestJob) -> bool:
    """任务是否仍占用测试资源（决定能否删除，见 ADR 0050）。

    节点行的 status/resource_id 是执行期快照：VM 可能经人工批量释放、
    流水线 destroy-envs 等链路释放而不回写节点状态。因此以资源行的实际
    占用状态为准——资源行不存在或未被占用即视为无保留环境；只有资源
    仍被占用才阻止删除，避免过期快照把可清理的历史任务永远挡住。
    """
    resource_ids = (
        db.execute(
            select(TestEnvNode.resource_id)
            .join(TestEnvSet, TestEnvNode.env_set_id == TestEnvSet.id)
            .where(
                TestEnvSet.job_id == job.id,
                TestEnvNode.resource_id.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    if not resource_ids:
        return False
    occupied_count = (
        db.execute(
            select(func.count(Resource.id)).where(
                Resource.id.in_(resource_ids),
                Resource.occupancy_status == OccupancyStatus.OCCUPIED.value,
            )
        ).scalar()
        or 0
    )
    return occupied_count > 0


def _is_referenced_by_pipeline(db: Session, job: TestJob) -> bool:
    """任务是否仍被现存 RunJob 引用（实现由装配层注册，见 pipeline_reads 注入缝）。"""
    return is_test_job_referenced_by_pipeline(db, job.id)


def delete_test_job_child_records(db: Session, *, job_ids: Sequence[int]) -> None:
    """批量清理任务全部子记录：case_run_details、case_runs、env_nodes、env_sets、
    task_events、log_artifacts。

    不依赖数据库层 ondelete=CASCADE（保证在未强制外键的 SQLite 测试与生产
    PostgreSQL 上行为一致）。供单条任务删除与流水线执行级联删除共用，
    见 ADR 0050。
    """
    if not job_ids:
        return
    db.execute(
        delete(TestCaseRunDetail).where(
            TestCaseRunDetail.case_run_id.in_(
                select(TestCaseRun.id).where(TestCaseRun.job_id.in_(job_ids))
            )
        )
    )
    db.execute(delete(TestCaseRun).where(TestCaseRun.job_id.in_(job_ids)))
    db.execute(
        delete(TestEnvNode).where(
            TestEnvNode.env_set_id.in_(
                select(TestEnvSet.id).where(TestEnvSet.job_id.in_(job_ids))
            )
        )
    )
    db.execute(delete(TestEnvSet).where(TestEnvSet.job_id.in_(job_ids)))
    db.execute(
        delete(TaskEvent).where(
            TaskEvent.subject_type == SUBJECT_TYPE_TEST_JOB,
            TaskEvent.subject_id.in_([str(job_id) for job_id in job_ids]),
        )
    )
    db.execute(delete(TestLogArtifact).where(TestLogArtifact.job_id.in_(job_ids)))


def delete_test_job(db: Session, *, actor: User, job: TestJob) -> None:
    """硬删除终态测试任务及其全部子记录。语义见 ADR 0050。

    校验顺序：权限（仅 ADMIN）→ 终态 → 无保留环境 → 无流水线 RunJob 引用。
    子记录经 delete_test_job_child_records 显式清理；共享卷上的日志文件不在
    此清理。
    """
    if actor.role != UserRole.ADMIN.value:
        raise TestJobDeleteError("forbidden", "只有管理员可以删除测试任务")
    if job.status not in TEST_JOB_TERMINAL_STATUSES:
        raise TestJobDeleteError("not_terminal", "只能删除已完成（成功/失败/异常）的任务")
    if _has_retained_env(db, job):
        raise TestJobDeleteError(
            "retained_env", "任务仍占用测试资源，请先释放对应环境再删除"
        )
    if _is_referenced_by_pipeline(db, job):
        raise TestJobDeleteError(
            "pipeline_referenced", "任务仍被流水线执行引用，请先删除对应的流水线执行"
        )
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="test_job.delete",
        target_type=TEST_JOB_TARGET_TYPE,
        target_id=str(job.id),
        detail={"job_id": job.id, "name": job.name},
    )
    delete_test_job_child_records(db, job_ids=[job.id])
    db.delete(job)
    db.flush()


def batch_delete_test_jobs(
    db: Session, *, actor: User, job_ids: list[int]
) -> list[TestJobBatchDeleteResult]:
    """批量删除任务：逐条应用单条删除校验，失败项记录原因，不中断整批。"""
    results: list[TestJobBatchDeleteResult] = []
    for job_id in job_ids:
        job = db.get(TestJob, job_id)
        if job is None:
            results.append(
                TestJobBatchDeleteResult(id=job_id, success=False, detail="任务不存在")
            )
            continue
        try:
            delete_test_job(db, actor=actor, job=job)
        except TestJobDeleteError as exc:
            results.append(
                TestJobBatchDeleteResult(id=job_id, success=False, detail=str(exc))
            )
        else:
            results.append(TestJobBatchDeleteResult(id=job_id, success=True))
    return results


def record_test_job_event(
    db: Session,
    *,
    job: TestJob,
    phase: str,
    message: str,
    level: str = "info",
    error_code: str | None = None,
) -> TaskEvent:
    return record_task_event(
        db,
        task_type=TASK_TYPE_TEST_JOB,
        subject_type=SUBJECT_TYPE_TEST_JOB,
        subject_id=str(job.id),
        celery_task_id=job.task_id,
        phase=phase,
        message=message,
        level=level,
        error_code=error_code,
    )


def list_test_job_events(db: Session, job: TestJob) -> list[TaskEvent]:
    return list_task_events(db, subject_type=SUBJECT_TYPE_TEST_JOB, subject_id=str(job.id))


def cases_by_suite(db: Session) -> dict[str, list[MugenCase]]:
    rows = list_mugen_cases(db)
    grouped: dict[str, list[MugenCase]] = defaultdict(list)
    for row in rows:
        grouped[row.suite_name].append(row)
    return grouped


def select_cases(
    db: Session,
    *,
    selections: list[TestCaseSelection],
    env_type: TestEnvType,
) -> list[list[MugenCase]]:
    """按选择项解析用例并校验，返回每个 suite 的一组 MugenCase(bundle)。

    校验：suite 存在、用例存在、用例 env_type 与目标环境一致。任一不满足
    抛 TestCaseSelectionError。case_names 为 None 表示取该 suite 全部用例。
    """
    grouped = cases_by_suite(db)
    bundles: list[list[MugenCase]] = []
    for selection in selections:
        suite_cases = grouped.get(selection.suite_name)
        if not suite_cases:
            raise TestCaseSelectionError(f"Suite not found: {selection.suite_name}")
        if selection.case_names is None:
            selected = suite_cases
        else:
            by_name = {case.case_name: case for case in suite_cases}
            selected = []
            for case_name in selection.case_names:
                case = by_name.get(case_name)
                if case is None:
                    raise TestCaseSelectionError(
                        f"Case not found: {selection.suite_name}/{case_name}"
                    )
                selected.append(case)
        unsupported = [case for case in selected if case.env_type != env_type.value]
        if unsupported:
            first = unsupported[0]
            raise TestCaseSelectionError(
                f"Case is not available for env_type={env_type.value}: "
                f"{first.suite_name}/{first.case_name}"
            )
        bundles.append(selected)
    return bundles


def distribute_bundles(
    bundles: list[list[MugenCase]],
    *,
    env_set_num: int,
) -> list[list[MugenCase]]:
    """把 bundle 轮询(round-robin)分配到 env_set，返回实际分得的结果。

    env_set_num 大于 bundle 数时按 bundle 数收缩，避免产生空环境集。
    """
    actual_env_set_num = min(env_set_num, len(bundles))
    distributed: list[list[MugenCase]] = [[] for _ in range(actual_env_set_num)]
    for index, bundle in enumerate(bundles):
        distributed[index % actual_env_set_num].extend(bundle)
    return distributed


def reject_unsupported_node_num(bundles: list[list[MugenCase]]) -> None:
    for bundle in bundles:
        for case in bundle:
            if case.node_num > 2:
                raise TestCaseSelectionError(
                    f"用例需要超过 2 个节点：{case.suite_name}/{case.case_name}"
                )


def image_matches_test_job_config(image: VMImage, config: TestJobConfig) -> bool:
    return (
        image.dist == config.dist
        and image.os_version == config.os_version
        and image.image_round == config.image_round
        and image.arch == config.arch
    )


def validate_test_job_image(config: TestJobConfig) -> None:
    try:
        images = discover_images(dist=config.dist, force_refresh=True)
    except ImageDiscoveryError as exc:
        raise TestJobImageIndexUnavailableError("无法读取镜像索引") from exc
    if not any(image_matches_test_job_config(image, config) for image in images):
        raise TestJobImageSelectionError("所选镜像不在当前镜像索引中")


def resolve_test_job_config(
    db: Session,
    config: TestJobConfig,
) -> ResolvedTestJobConfig:
    """校验测试任务配置并解析出 mugen commit_sha 与用例 bundle。

    目前仅支持 Mugen + VM 环境；校验索引版本唯一性、用例可选、节点数≤2、
    镜像在索引中。任一不满足抛对应策略异常。
    """
    if config.framework != TestFramework.MUGEN:
        raise TestManagementPolicyError("目前仅支持 Mugen 测试框架")
    if config.env_type != TestEnvType.VM:
        raise TestManagementPolicyError("目前仅支持虚拟机环境")
    mugen_commit_sha = current_mugen_commit_sha(db)
    bundles = select_cases(db, selections=config.cases, env_type=config.env_type)
    reject_unsupported_node_num(bundles)
    validate_test_job_image(config)
    return ResolvedTestJobConfig(
        mugen_commit_sha=mugen_commit_sha,
        bundles=bundles,
    )


def create_job_env_sets(
    db: Session, *, job: TestJob, assigned_cases: list[list[MugenCase]]
) -> None:
    """按分配结果创建环境集、节点和用例运行记录。

    每个 env_set 取其 bundle 内最大 node_num 决定节点数；node_index 0 为
    control，其余为 peer。case_run 记录 suite/case 名供执行阶段定位。
    """
    for env_index, cases in enumerate(assigned_cases, start=1):
        node_num = max(case.node_num for case in cases)
        env_set = TestEnvSet(
            job=job,
            set_index=env_index,
            node_num=node_num,
            env_type=cases[0].env_type if cases else None,
            add_disk_num=max(case.add_disk_num for case in cases),
            add_nic_num=max(case.add_nic_num for case in cases),
        )
        db.add(env_set)
        db.flush()
        for node_index in range(node_num):
            db.add(
                TestEnvNode(
                    env_set=env_set,
                    node_index=node_index,
                    role=CONTROL_NODE_ROLE if node_index == 0 else PEER_NODE_ROLE,
                )
            )
        for case in cases:
            db.add(
                TestCaseRun(
                    job=job,
                    env_set=env_set,
                    suite_name=case.suite_name,
                    case_name=case.case_name,
                )
            )


def create_test_job(db: Session, *, actor: User, payload: TestJobCreate) -> TestJob:
    """创建测试任务及其环境集/节点/用例记录。创建后处于 pending，待 queue_test_job 入队。"""
    resolved = resolve_test_job_config(db, payload)
    assigned_cases = distribute_bundles(
        resolved.bundles,
        env_set_num=payload.env_set_num,
    )
    job = TestJob(
        creator_user_id=actor.id,
        name=payload.name,
        status=TestJobStatus.PENDING.value,
        framework=payload.framework.value,
        env_type=payload.env_type.value,
        dist=payload.dist,
        os_version=payload.os_version,
        image_round=payload.image_round,
        arch=payload.arch,
        mugen_commit_sha=resolved.mugen_commit_sha,
        env_set_num=len(assigned_cases),
        keep_failed_env=payload.keep_failed_env,
        pre_env_script=payload.pre_env_script,
        post_env_script=payload.post_env_script,
    )
    db.add(job)
    db.flush()
    create_job_env_sets(db, job=job, assigned_cases=assigned_cases)
    record_test_job_event(db, job=job, phase="created", message="测试任务已创建")
    db.flush()
    return job


def queue_test_job(db: Session, job: TestJob) -> TestJob:
    """把 pending 的测试任务投递到 Celery 并记录 queued 事件。入队失败由调用方处理。"""
    job.task_id = enqueue_test_job(job)
    record_test_job_event(
        db,
        job=job,
        phase="queued",
        message="测试任务已进入异步队列",
    )
    db.flush()
    return job
