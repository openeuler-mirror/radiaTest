# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pagination import PAGE_SIZE, PageParams
from app.modules.audit.service import record_audit_log
from app.modules.test_management.models import MugenCase, TestJobTemplate
from app.modules.test_management.schemas import (
    TestCaseSelection,
    TestJobConfig,
    TestJobTemplateCreate,
    TestJobTemplateRead,
    TestJobTemplateUpdate,
)
from app.modules.test_management.service import (
    TestManagementPolicyError,
    image_matches_test_job_config,
    resolve_test_job_config,
)
from app.modules.users.models import User, UserRole
from app.modules.vms.image_discovery import ImageDiscoveryError, VMImage, discover_images

TEMPLATE_TARGET_TYPE = "test_job_template"

# 测试任务模板服务：模板 CRUD 与可用性校验。模板在更新执行相关字段(arch/
# cases/dist 等)时会重新校验用例与镜像，保证存档配置在当前索引下仍可用。


class TestJobTemplateNotFoundError(Exception):
    """模板不存在。"""


class TestJobTemplateConflictError(Exception):
    """模板名称(大小写不敏感)冲突。"""


@dataclass(frozen=True)
class TemplateAvailabilityContext:
    cases: dict[tuple[str, str], MugenCase]
    mugen_index_available: bool
    images_by_dist: dict[str, list[VMImage] | None]


def template_cases(template: TestJobTemplate) -> list[TestCaseSelection]:
    return [TestCaseSelection.model_validate(item) for item in template.case_selections]


def template_create_payload(template: TestJobTemplate) -> TestJobTemplateCreate:
    return TestJobTemplateCreate(
        name=template.name,
        framework=template.framework,
        env_type=template.env_type,
        dist=template.dist,
        os_version=template.os_version,
        image_round=template.image_round,
        arch=template.arch,
        env_set_num=template.env_set_num,
        keep_failed_env=template.keep_failed_env,
        pre_env_script=template.pre_env_script,
        post_env_script=template.post_env_script,
        cases=template_cases(template),
    )


def validate_template_config(
    db: Session,
    config: TestJobConfig,
) -> list[TestCaseSelection]:
    resolved = resolve_test_job_config(db, config)
    return [
        TestCaseSelection(
            suite_name=bundle[0].suite_name,
            case_names=[case.case_name for case in bundle],
        )
        for bundle in resolved.bundles
    ]


def get_test_job_template(db: Session, template_id: int) -> TestJobTemplate:
    template = db.get(TestJobTemplate, template_id)
    if template is None:
        raise TestJobTemplateNotFoundError("Test job template not found")
    return template


def require_template_manager(template: TestJobTemplate, actor: User) -> None:
    """模板管理鉴权：仅创建者本人或 ADMIN 可改/删。"""
    if actor.role != UserRole.ADMIN.value and template.creator_user_id != actor.id:
        raise TestManagementPolicyError("Only the creator or ADMIN can manage this template")


def ensure_template_name_available(
    db: Session,
    *,
    name: str,
    exclude_id: int | None = None,
) -> None:
    statement = select(TestJobTemplate.id).where(func.lower(TestJobTemplate.name) == name.lower())
    if exclude_id is not None:
        statement = statement.where(TestJobTemplate.id != exclude_id)
    if db.execute(statement).scalar_one_or_none() is not None:
        raise TestJobTemplateConflictError("Template name already exists")


def flush_template(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise TestJobTemplateConflictError("Template name already exists") from exc


def create_test_job_template(
    db: Session,
    *,
    actor: User,
    payload: TestJobTemplateCreate,
) -> TestJobTemplate:
    ensure_template_name_available(db, name=payload.name)
    expanded_cases = validate_template_config(db, payload)
    template = TestJobTemplate(
        creator_user_id=actor.id,
        name=payload.name,
        framework=payload.framework.value,
        env_type=payload.env_type.value,
        dist=payload.dist,
        os_version=payload.os_version,
        image_round=payload.image_round,
        arch=payload.arch,
        env_set_num=payload.env_set_num,
        keep_failed_env=payload.keep_failed_env,
        pre_env_script=payload.pre_env_script,
        post_env_script=payload.post_env_script,
        case_selections=[item.model_dump(exclude_none=True) for item in expanded_cases],
    )
    db.add(template)
    flush_template(db)
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="test_job_template.create",
        target_type=TEMPLATE_TARGET_TYPE,
        target_id=str(template.id),
        detail={"template_id": template.id, "name": template.name},
    )
    return template


def update_test_job_template(
    db: Session,
    *,
    actor: User,
    template: TestJobTemplate,
    payload: TestJobTemplateUpdate,
) -> TestJobTemplate:
    """部分更新模板。先合并老值与 patch，再校验名称可用性。

    只有 execution_fields(arch/cases/dist/env_type/framework/image_round/os_version)
    变化时才重新解析用例并校验镜像——纯改名等不影响执行的字段跳过昂贵校验。
    无变化直接返回原模板。
    """
    require_template_manager(template, actor)
    old_payload = template_create_payload(template)
    merged = old_payload.model_dump(mode="json")
    merged.update(payload.model_dump(mode="json", exclude_unset=True))
    next_payload = TestJobTemplateCreate.model_validate(merged)
    ensure_template_name_available(db, name=next_payload.name, exclude_id=template.id)

    old_values = old_payload.model_dump(mode="json")
    candidate_values = next_payload.model_dump(mode="json")
    execution_fields = {
        "arch",
        "cases",
        "dist",
        "env_type",
        "framework",
        "image_round",
        "os_version",
    }
    if any(
        old_values.get(field) != candidate_values.get(field)
        for field in execution_fields
    ):
        next_payload.cases = validate_template_config(db, next_payload)

    next_values = next_payload.model_dump(mode="json")
    changed_fields = sorted(
        field for field, value in next_values.items() if old_values.get(field) != value
    )
    if not changed_fields:
        return template

    for field in (
        "name",
        "dist",
        "os_version",
        "image_round",
        "arch",
        "env_set_num",
        "keep_failed_env",
        "pre_env_script",
        "post_env_script",
    ):
        setattr(template, field, getattr(next_payload, field))
    template.framework = next_payload.framework.value
    template.env_type = next_payload.env_type.value
    template.case_selections = [
        item.model_dump(exclude_none=True) for item in next_payload.cases
    ]
    flush_template(db)
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="test_job_template.update",
        target_type=TEMPLATE_TARGET_TYPE,
        target_id=str(template.id),
        detail={
            "template_id": template.id,
            "name": template.name,
            "changed_fields": changed_fields,
        },
    )
    return template


def delete_test_job_template(
    db: Session,
    *,
    actor: User,
    template: TestJobTemplate,
) -> None:
    require_template_manager(template, actor)
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="test_job_template.delete",
        target_type=TEMPLATE_TARGET_TYPE,
        target_id=str(template.id),
        detail={"template_id": template.id, "name": template.name},
    )
    db.delete(template)
    db.flush()


def paginate_test_job_templates(
    db: Session,
    *,
    pagination: PageParams,
) -> tuple[list[TestJobTemplate], int]:
    statement = (
        select(TestJobTemplate)
        .order_by(TestJobTemplate.updated_at.desc(), TestJobTemplate.id)
        .offset(pagination.offset)
        .limit(PAGE_SIZE)
    )
    items = list(db.execute(statement).scalars().all())
    total = db.scalar(select(func.count(TestJobTemplate.id))) or 0
    return items, total


def build_availability_context(
    db: Session,
    templates: list[TestJobTemplate],
) -> TemplateAvailabilityContext:
    """一次性预取全部用例、mugen 版本与各 dist 镜像，供列表页批量判可用性。

    集中预取避免模板列表里逐条查镜像索引。镜像索引不可读时该 dist 记 None，
    在 template_unavailable_reason 里转为"无法读取镜像索引"。
    """
    rows = list(db.execute(select(MugenCase)).scalars().all())
    commits = set(db.execute(select(distinct(MugenCase.commit_sha))).scalars().all())
    images_by_dist: dict[str, list[VMImage] | None] = {}
    for dist in {template.dist for template in templates}:
        try:
            images_by_dist[dist] = discover_images(dist=dist)
        except ImageDiscoveryError:
            images_by_dist[dist] = None
    return TemplateAvailabilityContext(
        cases={(case.suite_name, case.case_name): case for case in rows},
        mugen_index_available=len(commits) == 1,
        images_by_dist=images_by_dist,
    )


def template_unavailable_reason(
    template: TestJobTemplate,
    context: TemplateAvailabilityContext,
) -> str | None:
    """逐项校验模板可用性，返回首个不可用原因或 None(可用)。

    顺序：镜像索引可读→镜像存在→mugen 索引版本唯一→所选用例存在且
    env_type/node_num 与当前索引一致。返回首个失败原因，供页面提示。
    """
    images = context.images_by_dist.get(template.dist)
    if images is None:
        return "无法读取镜像索引"
    config = template_create_payload(template)
    if not any(image_matches_test_job_config(image, config) for image in images):
        return "所选镜像不存在"
    if not context.mugen_index_available:
        return "Mugen 用例索引不可用"
    for selection in config.cases:
        for case_name in selection.case_names or []:
            case = context.cases.get((selection.suite_name, case_name))
            if case is None:
                return f"用例不存在：{selection.suite_name}/{case_name}"
            if case.env_type != config.env_type.value or case.node_num > 2:
                return f"用例当前不可用：{selection.suite_name}/{case_name}"
    return None


def serialize_test_job_template(
    db: Session,
    *,
    template: TestJobTemplate,
    actor: User,
    context: TemplateAvailabilityContext,
) -> TestJobTemplateRead:
    creator = db.get(User, template.creator_user_id)
    cases = template_cases(template)
    reason = template_unavailable_reason(template, context)
    return TestJobTemplateRead(
        id=template.id,
        creator_user_id=template.creator_user_id,
        creator_username=creator.username if creator else None,
        name=template.name,
        framework=template.framework,
        env_type=template.env_type,
        dist=template.dist,
        os_version=template.os_version,
        image_round=template.image_round,
        arch=template.arch,
        env_set_num=template.env_set_num,
        keep_failed_env=template.keep_failed_env,
        pre_env_script=template.pre_env_script,
        post_env_script=template.post_env_script,
        cases=cases,
        suite_count=len(cases),
        case_count=sum(len(item.case_names or []) for item in cases),
        is_available=reason is None,
        unavailable_reason=reason,
        can_manage=(
            actor.role == UserRole.ADMIN.value or template.creator_user_id == actor.id
        ),
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def serialize_test_job_templates(
    db: Session,
    *,
    templates: list[TestJobTemplate],
    actor: User,
) -> list[TestJobTemplateRead]:
    context = build_availability_context(db, templates)
    return [
        serialize_test_job_template(db, template=template, actor=actor, context=context)
        for template in templates
    ]
