# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.modules.audit.service import record_audit_log
from app.modules.feishu.cards import (
    build_account_help_card,
    build_home_card,
    build_not_found_card,
    build_physical_menu_card,
    build_remote_command_form_card,
    build_remote_command_result_card,
    build_resource_detail_card,
    build_resource_list_card,
    build_unbound_card,
    build_vm_create_card,
    build_vm_menu_card,
    build_vm_request_detail_card,
    button,
    card,
    primary_button,
    text_block,
    vm_arch_value,
    vm_image_value,
)
from app.modules.feishu.pipeline_cards import (
    build_pipeline_configs_card,
    build_pipeline_execution_detail_card,
    build_pipeline_executions_card,
    build_pipeline_menu_card,
    build_pipeline_permission_card,
    build_pipeline_run_job_card,
    build_pipeline_started_card,
    build_pipeline_trigger_confirm_card,
    build_pipeline_trigger_error_card,
    build_pipeline_trigger_form_card,
)
from app.modules.feishu.remote_command import (
    RemoteCommandRequest,
    RemoteCommandUnavailableError,
    execute_remote_command,
)
from app.modules.feishu.service import get_bound_user_for_feishu_actor
from app.modules.idempotency.service import (
    IdempotentRequest,

    IdempotencyConflictError,
    IdempotencyInProgressError,
    abandon_idempotency_on_error,
    begin_idempotent_request,
    hash_request_body,
    record_idempotency_response,
)
from app.modules.leases.service import (
    CredentialPolicyError,
    CredentialReadError,
    read_resource_credentials,
    read_resource_ssh_credentials,
    release_expired_leases,
)
from app.modules.pipelines.models import PipelineConfig, PipelineExecution, TestModuleTemplate
from app.modules.pipelines.service import (
    compute_execution_status,
    enqueue_run_jobs,
    execution_config_name,
    get_execution_summary,
    get_pipeline_config,
    get_run_job_detail,
    latest_execution_for_config,
    list_pipeline_configs,
    list_pipeline_executions,
    trigger_pipeline,
)
from app.modules.resources.models import ResourceType
from app.modules.resources.schemas import ResourceListParams, ResourceRead
from app.modules.resources.service import (
    get_resource,
    list_resources,
    serialize_resource,
    serialize_resources,
)
from app.modules.users.models import User, UserRole
from app.modules.vms import image_discovery as vm_images
from app.modules.vms import service as vm_service
from app.modules.vms.image_discovery import ImageDiscoveryError, VMImage
from app.modules.vms.schemas import VMRequestCreate

# 飞书卡片动作处理：把按钮/表单动作翻译成对应卡片并落库执行。
# 表单草稿(VM 创建、远程命令、流水线触发)用进程内 dict 暂存(open_id 键)，
# 仅用于多步表单的中间状态，不持久化——Bot 单进程内存即足够，重启丢弃
# 只影响未提交的草稿。提交动作一律走幂等闭环(event_id/form_id 作 key，
# record_idempotency_response 后才 commit)，防卡片重复点击重复执行。

VM_DEFAULT_STATE = {
    "vcpu_count": "2",
    "memory_gb": "4",
    "data_disk_count": "0",
    "extra_nic_num": "0",
    "lease_days": "1",
    "purpose": "飞书申请 VM",
}
VM_INPUT_FIELDS = {
    "vcpu_count",
    "memory_gb",
    "data_disk_count",
    "extra_nic_num",
    "lease_days",
    "purpose",
}
VM_FIELD_LABELS = {
    "vcpu_count": "vCPU",
    "memory_gb": "内存 GB",
    "data_disk_count": "额外数据盘数量",
    "extra_nic_num": "额外网卡数量",
    "lease_days": "租期天数",
}
_VM_CREATE_STATE: dict[str, dict[str, str]] = {}
_REMOTE_COMMAND_STATE: dict[str, dict[str, str]] = {}
_REMOTE_COMMAND_PENDING: dict[str, str] = {}
_PIPELINE_TRIGGER_STATE: dict[str, dict[str, str]] = {}
REMOTE_COMMAND_MAX_LENGTH = 1000
FEISHU_VM_CREATE_PATH = "/feishu/card-actions/vm-create"
FEISHU_REMOTE_COMMAND_PATH = "/feishu/card-actions/remote-command"
FEISHU_PIPELINE_TRIGGER_PATH = "/feishu/card-actions/pipeline-trigger"


@dataclass(frozen=True)
class FeishuCardAction:
    action: str
    value: dict[str, Any]
    open_id: str | None
    union_id: str | None
    event_id: str | None = None


def reset_vm_create_state() -> None:
    _VM_CREATE_STATE.clear()
    _REMOTE_COMMAND_STATE.clear()
    _REMOTE_COMMAND_PENDING.clear()
    _PIPELINE_TRIGGER_STATE.clear()


def int_value(value: object, *, default: int = 0) -> int:
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def parse_int_field(state: dict[str, str], field: str, *, minimum: int, maximum: int) -> int:
    raw_value = state.get(field, "").strip()
    label = VM_FIELD_LABELS.get(field, field)
    if not raw_value.isdigit():
        raise ValueError(f"{label}必须是数字")
    value = int(raw_value)
    if value < minimum or value > maximum:
        raise ValueError(f"{label}必须在 {minimum}-{maximum} 之间")
    return value


def card_error(title: str, message: str, *, retry_action: str = "vm_create_form") -> dict[str, Any]:
    return card(
        title,
        [
            text_block(message),
            {
                "tag": "action",
                "actions": [
                    primary_button("重新创建", retry_action),
                    button("返回 VM 管理", "vm_menu"),
                ],
            },
        ],
        template="red",
    )


def remote_command_state_key(open_id: str, resource_id: str) -> str:
    return f"{open_id}:{resource_id}"


def pending_remote_command_key(open_id: str) -> str:
    return f"{open_id}:pending"


def parse_remote_command_input_name(name: object) -> str | None:
    if not isinstance(name, str):
        return None
    prefix = "remote_command|"
    if not name.startswith(prefix):
        return None
    resource_id = name.removeprefix(prefix)
    return resource_id or None


def get_remote_command_state(
    open_id: str,
    resource_id: str,
    *,
    reset: bool = False,
) -> dict[str, str]:
    key = remote_command_state_key(open_id, resource_id)
    if reset or key not in _REMOTE_COMMAND_STATE:
        _REMOTE_COMMAND_STATE[key] = {"command": ""}
    return _REMOTE_COMMAND_STATE[key]


def set_pending_remote_command(open_id: str, resource_id: str) -> None:
    _REMOTE_COMMAND_PENDING[pending_remote_command_key(open_id)] = resource_id


def get_pending_remote_command(open_id: str) -> str | None:
    return _REMOTE_COMMAND_PENDING.get(pending_remote_command_key(open_id))


def clear_pending_remote_command(open_id: str, resource_id: str) -> None:
    key = pending_remote_command_key(open_id)
    if _REMOTE_COMMAND_PENDING.get(key) == resource_id:
        _REMOTE_COMMAND_PENDING.pop(key, None)


def update_remote_command_state(open_id: str, action: FeishuCardAction) -> None:
    resource_id = parse_remote_command_input_name(action.value.get("name"))
    input_value = action.value.get("input_value")
    if resource_id is None or not isinstance(input_value, str):
        return
    state = get_remote_command_state(open_id, resource_id)
    state["command"] = input_value.strip()


def normalize_form_text(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("value", "text", "input_value"):
            text = normalize_form_text(value.get(key))
            if text is not None:
                return text
    if isinstance(value, list):
        for item in value:
            text = normalize_form_text(item)
            if text is not None:
                return text
    return None


def pipeline_state_key(open_id: str, config_id: str) -> str:
    return f"{open_id}:{config_id}"


def pipeline_control_parts(name: object) -> tuple[str, str] | None:
    if not isinstance(name, str) or "|" not in name:
        return None
    field, config_id = name.split("|", 1)
    if field not in {"pipeline_version", "pipeline_arch", "pipeline_image_round"}:
        return None
    if not config_id:
        return None
    return field.removeprefix("pipeline_"), config_id


def get_pipeline_trigger_state(
    open_id: str,
    config: PipelineConfig,
    *,
    reset: bool = False,
) -> dict[str, str]:
    key = pipeline_state_key(open_id, config.id)
    if reset or key not in _PIPELINE_TRIGGER_STATE:
        _PIPELINE_TRIGGER_STATE[key] = {
            "version": config.versions[0] if config.versions else "",
            "arch": config.archs[0] if config.archs else "",
            "image_round": config.image_round or "",
        }
    return _PIPELINE_TRIGGER_STATE[key]


def update_pipeline_trigger_state(
    open_id: str, action: FeishuCardAction
) -> str | None:
    parts = pipeline_control_parts(action.value.get("name"))
    if parts is None:
        return None
    field, config_id = parts
    config_state = _PIPELINE_TRIGGER_STATE.get(pipeline_state_key(open_id, config_id))
    if config_state is None:
        return config_id
    raw_value = (
        action.value.get("option")
        if action.value.get("tag") == "select_static"
        else action.value.get("input_value")
    )
    value = normalize_form_text(raw_value)
    if value is not None:
        config_state[field] = value
    return config_id


def remote_command_value_from_form(action_value: dict[str, Any], resource_id: str) -> str | None:
    input_name = f"remote_command|{resource_id}"
    form_value = action_value.get("form_value")
    if isinstance(form_value, dict):
        text = normalize_form_text(form_value.get(input_name))
        if text is not None:
            return text
    return normalize_form_text(action_value.get(input_name))


def default_vm_create_state(images: list[VMImage]) -> dict[str, str]:
    state = {"form_id": str(uuid4()), **VM_DEFAULT_STATE}
    if images:
        first_image = sorted(
            images,
            key=lambda item: (item.dist, item.os_version, item.image_round, item.arch),
        )[0]
        state["image"] = vm_image_value(first_image)
        state["arch"] = vm_arch_value(first_image.arch)
    return state


def get_vm_create_state(
    open_id: str,
    images: list[VMImage],
    *,
    reset: bool = False,
) -> dict[str, str]:
    if reset or open_id not in _VM_CREATE_STATE:
        _VM_CREATE_STATE[open_id] = default_vm_create_state(images)
    return _VM_CREATE_STATE[open_id]


def update_vm_create_state(open_id: str, action: FeishuCardAction) -> None:
    state = _VM_CREATE_STATE.get(open_id)
    if state is None:
        return
    tag = action.value.get("tag")
    if tag == "select_static":
        option = action.value.get("option")
        if isinstance(option, str):
            if option.startswith("image|"):
                state["image"] = option
            elif option.startswith("arch|"):
                state["arch"] = option
        return

    if tag == "input":
        name = action.value.get("name")
        input_value = action.value.get("input_value")
        if isinstance(name, str) and name in VM_INPUT_FIELDS and isinstance(input_value, str):
            state[name] = input_value.strip()


def selected_vm_image(images: list[VMImage], state: dict[str, str]) -> VMImage | None:
    image_value = state.get("image")
    arch_value = state.get("arch")
    arch = arch_value.removeprefix("arch|") if arch_value else ""
    candidates = [image for image in images if vm_image_value(image) == image_value]
    for image in images:
        if vm_image_value(image) == image_value and image.arch == arch:
            return image
    return sorted(candidates, key=lambda item: item.arch)[0] if candidates else None


def build_vm_request_payload(actor: User, image: VMImage, state: dict[str, str]) -> VMRequestCreate:
    """从草稿表单状态构造 VM 申请，并做数值范围校验。

    普通用户(非 ADMIN)租期不能为 0(永久)，仅 ADMIN 可申请永久 VM。
    memory_gb 转 memory_mb。校验失败抛 ValueError，由上层回显表单错误。
    """
    vcpu_count = parse_int_field(state, "vcpu_count", minimum=1, maximum=16)
    memory_gb = parse_int_field(state, "memory_gb", minimum=1, maximum=32)
    data_disk_count = parse_int_field(state, "data_disk_count", minimum=0, maximum=4)
    extra_nic_num = parse_int_field(state, "extra_nic_num", minimum=0, maximum=4)
    lease_days = parse_int_field(state, "lease_days", minimum=0, maximum=14)
    if actor.role != UserRole.ADMIN.value and lease_days == 0:
        raise ValueError("TE/TSE VM 租期不能为永久")

    purpose = state.get("purpose", "").strip() or VM_DEFAULT_STATE["purpose"]
    expected_ends_at = None
    if lease_days > 0:
        expected_ends_at = datetime.now(UTC) + timedelta(days=lease_days)

    return VMRequestCreate(
        dist=image.dist,
        os_version=image.os_version,
        image_round=image.image_round,
        arch=image.arch,
        vcpu_count=vcpu_count,
        memory_mb=memory_gb * 1024,
        data_disk_count=data_disk_count,
        extra_nic_num=extra_nic_num,
        purpose=purpose,
        expected_ends_at=expected_ends_at,
    )


def current_user(db: Session, action: FeishuCardAction) -> User | None:
    if not action.open_id:
        return None
    return get_bound_user_for_feishu_actor(
        db,
        open_id=action.open_id,
        union_id=action.union_id,
    )


def list_physical_resources(db: Session) -> list[ResourceRead]:
    resources = list_resources(
        db,
        params=ResourceListParams(resource_type=ResourceType.PHYSICAL.value),
        offset=0,
        limit=500,
    )
    return serialize_resources(db, resources)


def list_my_physical_resources(db: Session, user: User) -> list[ResourceRead]:
    return [
        resource
        for resource in list_physical_resources(db)
        if resource.current_lease_user_id == user.id
    ]


def resource_detail_card(
    db: Session,
    *,
    user: User,
    resource_id: str,
    return_action: str,
    page: int,
) -> dict[str, Any]:
    resource = get_resource(db, resource_id)
    if resource is None:
        return build_not_found_card()

    credentials = None
    credential_error = None
    can_run_remote_command = False
    try:
        credentials = read_resource_credentials(db, resource=resource, actor=user)
    except CredentialPolicyError:
        credentials = None
    except CredentialReadError:
        credential_error = "无法解密，请检查 RESOURCE_SECRET_KEY 或重新录入密码。"
    try:
        ssh_credentials = read_resource_ssh_credentials(db, resource=resource, actor=user)
        can_run_remote_command = bool(ssh_credentials.ssh_password)
    except (CredentialPolicyError, CredentialReadError):
        can_run_remote_command = False

    return build_resource_detail_card(
        resource=serialize_resource(db, resource),
        credentials=credentials,
        can_run_remote_command=can_run_remote_command,
        credential_error=credential_error,
        return_action=return_action,
        page=page,
    )


@dataclass(frozen=True)
class RemoteCommandAuditDraft:
    """远程命令审计草稿。"""

    user: User
    resource_id: str
    primary_ip: str | None
    ssh_username: str
    command: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool
    stdout_length: int = 0
    stderr_length: int = 0
    output_truncated: bool = False
    error: str | None = None


def record_remote_command_audit(
    db: Session,
    *,
    draft: RemoteCommandAuditDraft,
) -> None:
    user = draft.user
    resource_id = draft.resource_id
    primary_ip = draft.primary_ip
    ssh_username = draft.ssh_username
    command = draft.command
    exit_code = draft.exit_code
    duration_ms = draft.duration_ms
    timed_out = draft.timed_out
    stdout_length = draft.stdout_length
    stderr_length = draft.stderr_length
    output_truncated = draft.output_truncated
    error = draft.error
    detail: dict[str, object] = {
        "command": command,
        "primary_ip": primary_ip,
        "ssh_username": ssh_username,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "stdout_length": stdout_length,
        "stderr_length": stderr_length,
        "output_truncated": output_truncated,
    }
    if error:
        detail["error"] = error
    record_audit_log(
        db,
        actor_user_id=user.id,
        action="feishu.remote_command",
        target_type="resource",
        target_id=resource_id,
        detail=detail,
    )


@dataclass(frozen=True)
class RemoteCommandFormRequest:
    """远程命令表单卡片入参。"""

    action: FeishuCardAction
    user: User
    resource_id: str
    return_action: str
    page: int
    reset: bool = False
    error: str | None = None


def remote_command_form_card(
    db: Session,
    *,
    request: RemoteCommandFormRequest,
) -> dict[str, Any]:
    action = request.action
    user = request.user
    resource_id = request.resource_id
    return_action = request.return_action
    page = request.page
    reset = request.reset
    error = request.error
    if not action.open_id:
        return build_unbound_card()

    resource = get_resource(db, resource_id)
    if resource is None:
        return build_not_found_card()

    try:
        credentials = read_resource_ssh_credentials(db, resource=resource, actor=user)
    except CredentialPolicyError:
        return card(
            "远程命令",
            [
                text_block("没有权限在该资源上执行命令。"),
                {
                    "tag": "action",
                    "actions": [
                        button(
                            "返回详情",
                            "resource_detail",
                            value={
                                "resource_id": resource_id,
                                "return_action": return_action,
                                "page": page,
                            },
                        )
                    ],
                },
            ],
            template="red",
        )
    except CredentialReadError:
        return card(
            "远程命令",
            [
                text_block("无法解密 SSH 凭据，请检查 RESOURCE_SECRET_KEY 或重新录入密码。"),
                {
                    "tag": "action",
                    "actions": [
                        button(
                            "返回详情",
                            "resource_detail",
                            value={
                                "resource_id": resource_id,
                                "return_action": return_action,
                                "page": page,
                            },
                        )
                    ],
                },
            ],
            template="red",
        )

    if not credentials.ssh_password:
        error = error or "该资源没有 SSH 密码。"

    state = get_remote_command_state(action.open_id, resource_id, reset=reset)
    set_pending_remote_command(action.open_id, resource_id)
    if reset or "return_action" not in state:
        state["return_action"] = return_action
        state["page"] = str(page)
    effective_return_action = state.get("return_action", return_action)
    effective_page = int_value(state.get("page"), default=page)
    return build_remote_command_form_card(
        resource=serialize_resource(db, resource),
        command=state.get("command", ""),
        return_action=effective_return_action,
        page=effective_page,
        error=error,
    )


@dataclass(frozen=True)
class RemoteCommandExecuteRequest:
    """远程命令执行卡片入参。"""

    action: FeishuCardAction
    user: User
    resource_id: str
    command: str
    return_action: str
    page: int


def execute_remote_command_card(
    db: Session,
    *,
    request: RemoteCommandExecuteRequest,
) -> dict[str, Any]:
    action = request.action
    user = request.user
    resource_id = request.resource_id
    command = request.command
    return_action = request.return_action
    page = request.page
    """执行远程命令并回写审计，返回结果卡。

    权限与凭据走 read_resource_ssh_credentials(复用 leases 的鉴权边界)。
    命令长度上限 1000 字符。执行前后均记审计日志(含退出码/耗时/截断)，
    便于事后定位。成功后清理草稿状态与 pending 标记。
    """
    if not action.open_id:
        return build_unbound_card()

    resource = get_resource(db, resource_id)
    if resource is None:
        return build_not_found_card()

    if not command:
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=return_action,
                   page=page,
                   error="命令不能为空。",
                   ),
               )
    if len(command) > REMOTE_COMMAND_MAX_LENGTH:
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=return_action,
                   page=page,
                   error=f"命令不能超过 {REMOTE_COMMAND_MAX_LENGTH} 字符。",
                   ),
               )

    try:
        credentials = read_resource_ssh_credentials(db, resource=resource, actor=user)
    except CredentialPolicyError:
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=return_action,
                   page=page,
                   error="没有权限在该资源上执行命令。",
                   ),
               )
    except CredentialReadError:
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=return_action,
                   page=page,
                   error="无法解密 SSH 凭据，请检查 RESOURCE_SECRET_KEY 或重新录入密码。",
                   ),
               )

    if not credentials.ssh_password:
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=return_action,
                   page=page,
                   error="该资源没有 SSH 密码。",
                   ),
               )
    if not resource.primary_ip:
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=return_action,
                   page=page,
                   error="该资源没有 OS IP。",
                   ),
               )

    try:
        result = execute_remote_command(
            request=RemoteCommandRequest(
                host=resource.primary_ip,
                username=credentials.ssh_username,
                password=credentials.ssh_password,
                command=command,
            ),
        )
    except RemoteCommandUnavailableError as exc:
        record_remote_command_audit(
            db,
            draft=RemoteCommandAuditDraft(
            user=user,
            resource_id=resource.id,
            primary_ip=resource.primary_ip,
            ssh_username=credentials.ssh_username,
            command=command,
            exit_code=None,
            duration_ms=0,
            timed_out=False,
            error=str(exc),
            ),
        )
        db.commit()
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=return_action,
                   page=page,
                   error=str(exc),
                   ),
               )
    except Exception as exc:  # noqa: BLE001
        error_message = f"远程命令执行失败：{exc}"
        record_remote_command_audit(
            db,
            draft=RemoteCommandAuditDraft(
            user=user,
            resource_id=resource.id,
            primary_ip=resource.primary_ip,
            ssh_username=credentials.ssh_username,
            command=command,
            exit_code=None,
            duration_ms=0,
            timed_out=False,
            error=error_message,
            ),
        )
        db.commit()
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=return_action,
                   page=page,
                   error=error_message,
                   ),
               )

    record_remote_command_audit(
        db,
        draft=RemoteCommandAuditDraft(
        user=user,
        resource_id=resource.id,
        primary_ip=resource.primary_ip,
        ssh_username=credentials.ssh_username,
        command=command,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        timed_out=result.timed_out,
        stdout_length=result.stdout_length,
        stderr_length=result.stderr_length,
        output_truncated=result.output_truncated,
        ),
    )
    db.commit()
    _REMOTE_COMMAND_STATE.pop(remote_command_state_key(action.open_id, resource_id), None)
    clear_pending_remote_command(action.open_id, resource_id)
    return build_remote_command_result_card(
        resource=serialize_resource(db, resource),
        command=command,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        duration_ms=result.duration_ms,
        stdout=result.stdout,
        stderr=result.stderr,
        output_truncated=result.output_truncated,
        return_action=return_action,
        page=page,
    )


def remote_command_submit_card(
    db: Session,
    *,
    action: FeishuCardAction,
    user: User,
) -> dict[str, Any]:
    if not action.open_id:
        return build_unbound_card()

    page = int_value(action.value.get("page"))
    return_action = str(action.value.get("return_action") or "home")
    resource_id = action.value.get("resource_id")
    if not isinstance(resource_id, str) or not resource_id:
        return build_not_found_card()

    state = get_remote_command_state(action.open_id, resource_id)
    command = remote_command_value_from_form(action.value, resource_id)
    if command is None:
        command = state.get("command", "").strip()
    else:
        state["command"] = command

    if not action.event_id:
        return execute_remote_command_card(
                   db,
                   request=RemoteCommandExecuteRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   command=command,
                   return_action=return_action,
                   page=page,
                   ),
               )

    request_hash = hash_request_body(
        {
            "resource_id": resource_id,
            "command": command,
            "return_action": return_action,
            "page": page,
        }
    )
    try:
        decision = begin_idempotent_request(
                       db,
                       request=IdempotentRequest(
                       actor=user,
                       method="POST",
                       path=FEISHU_REMOTE_COMMAND_PATH,
                       key=action.event_id,
                       request_hash=request_hash,
                       ),
                   )
    except IdempotencyInProgressError:
        return card_error("远程命令", "该命令正在执行，请稍后查看结果。")
    except (IdempotencyConflictError, ValueError):
        return card_error("远程命令", "无法确认该操作是否已执行，请重新打开卡片。")

    if decision.replay is not None:
        response_body, _ = decision.replay
        return response_body
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    response_body = execute_remote_command_card(
                        db,
                        request=RemoteCommandExecuteRequest(
                        action=action,
                        user=user,
                        resource_id=resource_id,
                        command=command,
                        return_action=return_action,
                        page=page,
                        ),
                    )
    record_idempotency_response(
        db,
        record=decision.record,
        response_body=response_body,
        status_code=200,
    )
    db.commit()
    return response_body


def remote_command_text_card(
    db: Session,
    *,
    open_id: str,
    union_id: str | None,
    command: str,
) -> dict[str, Any] | None:
    resource_id = get_pending_remote_command(open_id)
    if not resource_id:
        return None
    user = get_bound_user_for_feishu_actor(db, open_id=open_id, union_id=union_id)
    if user is None:
        return build_unbound_card()
    state = get_remote_command_state(open_id, resource_id)
    return_action = state.get("return_action", "home")
    page = int_value(state.get("page"))
    action = FeishuCardAction(
        action="remote_command_text",
        value={},
        open_id=open_id,
        union_id=union_id,
    )
    state["command"] = command.strip()
    return execute_remote_command_card(
               db,
               request=RemoteCommandExecuteRequest(
               action=action,
               user=user,
               resource_id=resource_id,
               command=state["command"],
               return_action=return_action,
               page=page,
               ),
           )


def load_vm_images() -> list[VMImage]:
    return vm_images.discover_images()


def vm_create_card(
    action: FeishuCardAction,
    *,
    reset: bool = False,
    error: str | None = None,
) -> dict[str, Any]:
    if not action.open_id:
        return build_unbound_card()
    try:
        images = load_vm_images()
    except ImageDiscoveryError as exc:
        return card_error("创建 VM", f"读取镜像列表失败：{exc}")
    state = get_vm_create_state(action.open_id, images, reset=reset)
    return build_vm_create_card(images=images, state=state, error=error)


def vm_create_submit_card(
    db: Session,
    *,
    action: FeishuCardAction,
    user: User,
) -> dict[str, Any]:
    if not action.open_id:
        return build_unbound_card()

    form_id = action.value.get("form_id")
    if not isinstance(form_id, str) or not form_id:
        return card_error("创建 VM", "卡片状态无效，请重新打开创建 VM。")

    request_hash = hash_request_body({"form_id": form_id})
    try:
        decision = begin_idempotent_request(
                       db,
                       request=IdempotentRequest(
                       actor=user,
                       method="POST",
                       path=FEISHU_VM_CREATE_PATH,
                       key=form_id,
                       request_hash=request_hash,
                       ),
                   )
    except IdempotencyInProgressError:
        return card_error("创建 VM", "该申请正在提交，请稍后查看申请记录。")
    except (IdempotencyConflictError, ValueError):
        return card_error("创建 VM", "无法确认该申请是否已提交，请重新打开创建 VM。")

    if decision.replay is not None:
        response_body, _ = decision.replay
        return response_body
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    try:
        with abandon_idempotency_on_error(db, decision.record):
            state = _VM_CREATE_STATE.get(action.open_id)
            if state is None or state.get("form_id") != form_id:
                raise ValueError("卡片状态已失效，请重新打开创建 VM。")

            images = load_vm_images()
            image = selected_vm_image(images, state)
            if image is None:
                raise ValueError("请选择有效的镜像版本和架构。")
            payload = build_vm_request_payload(user, image, state)
    except ValueError as exc:
        return vm_create_card(action, error=str(exc))
    except ImageDiscoveryError as exc:
        return card_error("创建 VM", f"读取镜像列表失败：{exc}")

    try:
        request = vm_service.submit_vm_request(db, actor=user, payload=payload)
        response_body = build_vm_request_detail_card(vm_service.serialize_vm_request(db, request))
    except (vm_service.VMImageNotFoundError, vm_service.VMPolicyError) as exc:
        response_body = vm_create_card(action, error=str(exc))
    except vm_service.VMQueueUnavailableError as exc:
        response_body = vm_create_card(action, error=f"队列不可用：{exc}")

    record_idempotency_response(
        db,
        record=decision.record,
        response_body=response_body,
        status_code=200,
    )
    db.commit()

    _VM_CREATE_STATE.pop(action.open_id, None)
    return response_body


def vm_request_detail_card(db: Session, *, user: User, request_id: str) -> dict[str, Any]:
    request = vm_service.get_vm_request(db, request_id)
    if request is None:
        return build_not_found_card()
    if request.requester_user_id != user.id and user.role != UserRole.ADMIN.value:
        return build_not_found_card()
    if request.status == "succeeded" and request.resource_id:
        return resource_detail_card(
            db,
            user=user,
            resource_id=request.resource_id,
            return_action="vm_mine",
            page=0,
        )
    return build_vm_request_detail_card(vm_service.serialize_vm_request(db, request))


def pipeline_trigger_form_card(
    db: Session,
    *,
    action: FeishuCardAction,
    user: User,
    reset: bool = True,
) -> dict[str, Any]:
    if user.role != UserRole.ADMIN.value:
        return build_pipeline_permission_card()
    config_id = action.value.get("config_id")
    if not isinstance(config_id, str):
        return build_pipeline_trigger_error_card("流水线参数无效。")
    config = get_pipeline_config(db, config_id)
    if config is None:
        return build_pipeline_trigger_error_card("流水线不存在或已被删除。")
    if not config.versions or not config.archs:
        return build_pipeline_trigger_error_card(
            "流水线尚未配置版本或架构。", config_id=config.id
        )
    if not action.open_id:
        return build_unbound_card()
    state = get_pipeline_trigger_state(action.open_id, config, reset=reset)
    return build_pipeline_trigger_form_card(config, state=state)


def pipeline_configs_card(db: Session, *, user: User) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for config in list_pipeline_configs(db):
        latest = latest_execution_for_config(db, config.id)
        items.append(
            {
                "id": config.id,
                "name": config.name,
                "pipeline_type": config.pipeline_type,
                "versions": config.versions,
                "archs": config.archs,
                "latest": (
                    {
                        "id": latest.id,
                        "status": compute_execution_status(db, latest),
                    }
                    if latest
                    else None
                ),
            }
        )
    return build_pipeline_configs_card(
        items,
        is_admin=user.role == UserRole.ADMIN.value,
    )


def pipeline_executions_card(
    db: Session, *, running_only: bool
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for execution in list_pipeline_executions(db, limit=20):
        status = compute_execution_status(db, execution)
        if running_only and status not in {"pending", "running"}:
            continue
        items.append(
            {
                "id": execution.id,
                "config_name": execution_config_name(db, execution),
                "status": status,
                "versions": execution.versions,
                "archs": execution.archs,
                "triggered_by": execution.triggered_by,
                "triggered_at": execution.triggered_at,
            }
        )
    return build_pipeline_executions_card(items, running_only=running_only)


def pipeline_execution_detail_card(
    db: Session, *, execution_id: object
) -> dict[str, Any]:
    if not isinstance(execution_id, str) or not execution_id:
        return build_pipeline_trigger_error_card("执行记录参数无效。")
    summary = get_execution_summary(db, execution_id)
    if summary is None:
        return build_pipeline_trigger_error_card("执行记录不存在或已被删除。")
    execution = db.get(PipelineExecution, execution_id)
    if execution is not None:
        summary["config_name"] = execution_config_name(db, execution)
    return build_pipeline_execution_detail_card(summary)


def pipeline_run_job_detail_card(
    db: Session, *, run_job_id: object, execution_id: object
) -> dict[str, Any]:
    if not isinstance(run_job_id, str) or not run_job_id:
        return build_pipeline_trigger_error_card("RunJob 参数无效。")
    detail = get_run_job_detail(db, run_job_id)
    if detail is None:
        return build_pipeline_trigger_error_card("RunJob 不存在或已被删除。")
    template_id = detail.get("module_template_id")
    if isinstance(template_id, str):
        template = db.get(TestModuleTemplate, template_id)
        if template is not None:
            detail["module_name"] = template.display_name
    return build_pipeline_run_job_card(
        detail,
        execution_id=execution_id if isinstance(execution_id, str) else None,
    )


def pipeline_trigger_form_update_card(
    db: Session, *, action: FeishuCardAction, user: User
) -> dict[str, Any]:
    if user.role != UserRole.ADMIN.value:
        return build_pipeline_permission_card()
    if not action.open_id:
        return build_unbound_card()
    config_id = update_pipeline_trigger_state(action.open_id, action)
    if not config_id:
        return build_pipeline_trigger_error_card("流水线参数无效。")
    return pipeline_trigger_form_card(
        db,
        action=FeishuCardAction(
            action="pipeline_trigger_form",
            value={"config_id": config_id},
            open_id=action.open_id,
            union_id=action.union_id,
        ),
        user=user,
        reset=False,
    )


def pipeline_trigger_confirm_card(
    db: Session, *, action: FeishuCardAction, user: User
) -> dict[str, Any]:
    if user.role != UserRole.ADMIN.value:
        return build_pipeline_permission_card()
    config_id = action.value.get("config_id")
    if not isinstance(config_id, str):
        return build_pipeline_trigger_error_card("流水线参数无效。")
    config = get_pipeline_config(db, config_id)
    if config is None:
        return build_pipeline_trigger_error_card("流水线不存在或已被删除。")
    if not action.open_id:
        return build_unbound_card()
    state = get_pipeline_trigger_state(action.open_id, config)
    version = state.get("version")
    arch = state.get("arch")
    image_round = state.get("image_round")
    if version not in config.versions:
        return build_pipeline_trigger_form_card(
            config, state=state, error="请选择有效版本。"
        )
    if arch not in config.archs:
        return build_pipeline_trigger_form_card(
            config, state=state, error="请选择有效架构。"
        )
    return build_pipeline_trigger_confirm_card(
        config,
        version=version,
        arch=arch,
        image_round=image_round,
    )


def pipeline_trigger_submit_card(
    db: Session, *, action: FeishuCardAction, user: User
) -> dict[str, Any]:
    if user.role != UserRole.ADMIN.value:
        return build_pipeline_permission_card()
    values = action.value
    config_id = values.get("config_id")
    confirmation_id = values.get("confirmation_id")
    version = values.get("version")
    arch = values.get("arch")
    image_round = values.get("image_round")
    required_values = (config_id, confirmation_id, version, arch)
    if not all(isinstance(value, str) and value for value in required_values):
        return build_pipeline_trigger_error_card("确认信息无效，请重新选择流水线。")
    config = get_pipeline_config(db, config_id)
    if config is None:
        return build_pipeline_trigger_error_card("流水线不存在或已被删除。")
    if version not in config.versions or arch not in config.archs:
        return build_pipeline_trigger_error_card(
            "流水线配置已经变化，请重新选择参数。", config_id=config.id
        )
    normalized_round = image_round.strip() if isinstance(image_round, str) else None
    request_body = {
        "config_id": config.id,
        "version": version,
        "arch": arch,
        "image_round": normalized_round,
    }
    try:
        decision = begin_idempotent_request(
                       db,
                       request=IdempotentRequest(
                       actor=user,
                       method="POST",
                       path=FEISHU_PIPELINE_TRIGGER_PATH,
                       key=confirmation_id,
                       request_hash=hash_request_body(request_body),
                       ),
                   )
    except IdempotencyInProgressError:
        return build_pipeline_trigger_error_card("该流水线正在启动，请稍后查询执行状态。")
    except (IdempotencyConflictError, ValueError):
        return build_pipeline_trigger_error_card("无法确认该操作是否已执行，请重新选择流水线。")
    if decision.replay is not None:
        response_body, _ = decision.replay
        return response_body
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    with abandon_idempotency_on_error(db, decision.record):
        execution, run_jobs = trigger_pipeline(
            db,
            config,
            versions=[version],
            archs=[arch],
            image_round=normalized_round or None,
            triggered_by=user.id,
        )
        response_body = build_pipeline_started_card(config, execution)
        record_audit_log(
            db,
            actor_user_id=user.id,
            action="feishu.pipeline.trigger",
            target_type="pipeline_execution",
            target_id=execution.id,
            detail=request_body,
        )
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response_body,
            status_code=200,
        )
        db.commit()
    enqueue_run_jobs(db, run_jobs, user.id)
    if action.open_id:
        _PIPELINE_TRIGGER_STATE.pop(
            pipeline_state_key(action.open_id, config.id),
            None,
        )
    return response_body


def handle_bound_action(db: Session, *, action: FeishuCardAction, user: User) -> dict[str, Any]:
    if action.action == "assistant_help":
        from app.modules.feishu.assistant_cards import build_assistant_help_card

        return build_assistant_help_card()
    if action.action == "pipeline_menu":
        return build_pipeline_menu_card()
    if action.action == "pipeline_configs":
        return pipeline_configs_card(db, user=user)
    if action.action == "pipeline_executions_running":
        return pipeline_executions_card(db, running_only=True)
    if action.action == "pipeline_executions_recent":
        return pipeline_executions_card(db, running_only=False)
    if action.action == "pipeline_execution_detail":
        return pipeline_execution_detail_card(
            db, execution_id=action.value.get("execution_id")
        )
    if action.action == "pipeline_run_job_detail":
        return pipeline_run_job_detail_card(
            db,
            run_job_id=action.value.get("run_job_id"),
            execution_id=action.value.get("execution_id"),
        )
    if action.action == "pipeline_trigger_form":
        return pipeline_trigger_form_card(db, action=action, user=user)
    if action.action == "pipeline_trigger_form_update":
        return pipeline_trigger_form_update_card(db, action=action, user=user)
    if action.action == "pipeline_trigger_confirm":
        return pipeline_trigger_confirm_card(db, action=action, user=user)
    if action.action == "pipeline_trigger_submit":
        return pipeline_trigger_submit_card(db, action=action, user=user)
    page = int_value(action.value.get("page"))
    if release_expired_leases(db):
        db.commit()

    if action.action == "physical_menu":
        return build_physical_menu_card()
    if action.action == "vm_menu":
        return build_vm_menu_card()
    if action.action == "physical_mine":
        return build_resource_list_card(
            title="我的物理机",
            resources=list_my_physical_resources(db, user),
            action="physical_mine",
            page=page,
            empty_text="当前没有占用中的物理机。",
            kind="physical",
        )
    if action.action == "physical_all":
        return build_resource_list_card(
            title="所有物理机",
            resources=list_physical_resources(db),
            action="physical_all",
            page=page,
            empty_text="没有可显示的物理机。",
            kind="physical",
        )
    if action.action == "vm_mine":
        return build_resource_list_card(
            title="我的 VM",
            resources=vm_service.list_vms(db, actor=user, show_all=False),
            action="vm_mine",
            page=page,
            empty_text="当前没有创建中的 VM。",
            kind="vm",
        )
    if action.action == "resource_detail":
        resource_id = action.value.get("resource_id")
        if not isinstance(resource_id, str) or not resource_id:
            return build_not_found_card()
        return resource_detail_card(
            db,
            user=user,
            resource_id=resource_id,
            return_action=str(action.value.get("return_action") or "home"),
            page=page,
        )
    if action.action == "remote_command_form":
        resource_id = action.value.get("resource_id")
        if not isinstance(resource_id, str) or not resource_id:
            return build_not_found_card()
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=str(action.value.get("return_action") or "home"),
                   page=page,
                   reset=True,
                   ),
               )
    if action.action == "remote_command_form_update":
        if action.open_id:
            update_remote_command_state(action.open_id, action)
        resource_id = parse_remote_command_input_name(action.value.get("name"))
        if resource_id is None:
            return build_not_found_card()
        return remote_command_form_card(
                   db,
                   request=RemoteCommandFormRequest(
                   action=action,
                   user=user,
                   resource_id=resource_id,
                   return_action=str(action.value.get("return_action") or "home"),
                   page=page,
                   ),
               )
    if action.action == "remote_command_submit":
        return remote_command_submit_card(db, action=action, user=user)
    if action.action == "vm_create_form":
        return vm_create_card(action, reset=True)
    if action.action == "vm_create_form_update":
        if action.open_id:
            try:
                images = load_vm_images()
            except ImageDiscoveryError as exc:
                return card_error("创建 VM", f"读取镜像列表失败：{exc}")
            get_vm_create_state(action.open_id, images)
            update_vm_create_state(action.open_id, action)
        return vm_create_card(action)
    if action.action == "vm_create_submit":
        return vm_create_submit_card(db, action=action, user=user)
    if action.action == "vm_request_detail":
        request_id = action.value.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            return build_not_found_card()
        return vm_request_detail_card(db, user=user, request_id=request_id)
    if action.action == "account_help":
        return build_account_help_card(user)
    return build_home_card()


def handle_card_action(db: Session, action: FeishuCardAction) -> dict[str, Any]:
    """卡片动作总入口：home/account_help 无需绑定，其余动作要求用户已绑定飞书身份。

    未绑定返回引导绑定卡片。已绑定转发到 handle_bound_action 按动作名分发。
    """
    if action.action == "home":
        return build_home_card()

    user = current_user(db, action)
    if action.action == "account_help":
        return build_account_help_card(user)
    if user is None:
        return build_unbound_card()
    return handle_bound_action(db, action=action, user=user)

