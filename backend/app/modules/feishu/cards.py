# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

# 飞书卡片构造：把资源/VM/远程命令等业务对象渲染成飞书 interactive 卡片 JSON。
# 纯展示层，无副作用；按钮 value 携带 action 名供 card_actions 分发。

from dataclasses import dataclass

import json
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.modules.leases.schemas import ResourceCredentialRead
from app.modules.resources.schemas import ResourceRead
from app.modules.users.models import User
from app.modules.vms.image_discovery import VMImage
from app.modules.vms.schemas import VMRequestRead

PAGE_SIZE = 5
VM_DEFAULT_PURPOSE = "飞书申请 VM"


def vm_image_value(image: VMImage) -> str:
    return f"image|{image.dist}|{image.os_version}|{image.image_round}"


def vm_arch_value(arch: str) -> str:
    return f"arch|{arch}"


def text_block(content: str) -> dict[str, Any]:
    return {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": content,
        },
    }


def button(label: str, action: str, *, value: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": "default",
        "value": {"action": action, **(value or {})},
    }


def primary_button(
    label: str,
    action: str,
    *,
    value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = button(label, action, value=value)
    item["type"] = "primary"
    return item


def select_static(
    *,
    name: str | None = None,
    placeholder: str,
    options: list[dict[str, Any]],
    initial_option: str | None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "tag": "select_static",
        "placeholder": {"tag": "plain_text", "content": placeholder},
        "options": options,
    }
    if name:
        item["name"] = name
    if initial_option:
        item["initial_option"] = initial_option
    return item


def input_control(
    *,
    name: str,
    placeholder: str,
    default_value: str,
    max_length: int = 128,
) -> dict[str, Any]:
    return {
        "tag": "input",
        "name": name,
        "placeholder": {"tag": "plain_text", "content": placeholder},
        "default_value": default_value,
        "max_length": max_length,
    }


def option(label: str, value: str) -> dict[str, Any]:
    return {"text": {"tag": "plain_text", "content": label}, "value": value}


def action_block(actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"tag": "action", "actions": actions}


def card(title: str, elements: list[dict[str, Any]], *, template: str = "blue") -> dict[str, Any]:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": template,
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": elements,
    }


def display(value: object) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def datetime_display(value: datetime | None) -> str:
    if value is None:
        return "永久"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    timezone = ZoneInfo(get_settings().display_timezone)
    return value.astimezone(timezone).strftime("%Y-%m-%d %H:%M")


def build_home_card() -> dict[str, Any]:
    return card(
        "radiaTest",
        [
            text_block("请选择要查看的资源入口。"),
            action_block(
                [
                    primary_button("物理机管理", "physical_menu"),
                    button("VM 管理", "vm_menu"),
                    button("流水线", "pipeline_menu"),
                    button("智能助手", "assistant_help"),
                    button("账号与帮助", "account_help"),
                ]
            ),
        ],
    )


def build_home_card_content() -> str:
    return json.dumps(build_home_card(), ensure_ascii=False, separators=(",", ":"))


def build_physical_menu_card() -> dict[str, Any]:
    return card(
        "物理机管理",
        [
            text_block("选择要查看的物理机范围。"),
            action_block(
                [
                    primary_button("我的物理机", "physical_mine", value={"page": 0}),
                    button("所有物理机", "physical_all", value={"page": 0}),
                    button("返回首页", "home"),
                ]
            ),
        ],
    )


def build_vm_menu_card() -> dict[str, Any]:
    return card(
        "VM 管理",
        [
            text_block("选择要查看的 VM 入口。"),
            action_block(
                [
                    primary_button("我的 VM", "vm_mine", value={"page": 0}),
                    button("创建 VM", "vm_create_form"),
                    button("返回首页", "home"),
                ]
            ),
        ],
    )


def build_account_help_card(user: User | None) -> dict[str, Any]:
    if user is None:
        account_line = "当前飞书账号尚未绑定 radiaTest 用户，请先在 radiaTest Web 账号页绑定飞书。"
    else:
        account_line = f"当前绑定用户：{user.username}（{user.role}）"
    return card(
        "账号与帮助",
        [
            text_block(
                f"{account_line}\n\n"
                "发送 `help` 或 `帮助` 可以打开首页卡片。"
            ),
            action_block([button("返回首页", "home")]),
        ],
    )


def build_unbound_card() -> dict[str, Any]:
    return card(
        "需要绑定账号",
        [
            text_block("资源查询需先绑定 radiaTest 用户，请在 radiaTest Web 账号页完成飞书绑定。"),
            action_block([button("返回首页", "home")]),
        ],
        template="yellow",
    )


def build_not_found_card() -> dict[str, Any]:
    return card(
        "没有找到资源",
        [
            text_block("资源不存在或已被删除。"),
            action_block([button("返回首页", "home")]),
        ],
        template="red",
    )


def resource_occupancy(resource: ResourceRead) -> str:
    if resource.current_lease_username:
        lease_end = datetime_display(resource.current_lease_expected_ends_at)
        return f"{resource.current_lease_username} / {lease_end}"
    return "空闲"


def resource_list_line(resource: ResourceRead, *, kind: str) -> str:
    if kind == "physical":
        return (
            f"**OS IP**：{display(resource.primary_ip)}\n"
            f"**BMC IP**：{display(resource.bmc_ip)}\n"
            f"**占用**：{resource_occupancy(resource)}"
        )
    return (
        f"**OS IP**：{display(resource.primary_ip)}\n"
        f"**VM 名称**：{display(resource.vm_name or resource.name)}\n"
        f"**占用**：{resource_occupancy(resource)}"
    )


@dataclass(frozen=True)
class ResourceListCardRequest:
    """资源列表卡片入参。"""

    title: str
    resources: list[ResourceRead]
    action: str
    page: int
    empty_text: str
    kind: str


def build_resource_list_card(
    *,
    request: ResourceListCardRequest,
) -> dict[str, Any]:
    title = request.title
    resources = request.resources
    action = request.action
    page = request.page
    empty_text = request.empty_text
    kind = request.kind
    start = page * PAGE_SIZE
    page_resources = resources[start:start + PAGE_SIZE]
    elements: list[dict[str, Any]] = []
    if not page_resources:
        elements.append(text_block(empty_text))
    for resource in page_resources:
        elements.append(text_block(resource_list_line(resource, kind=kind)))
        elements.append(
            action_block(
                [
                    button(
                        "详情",
                        "resource_detail",
                        value={
                            "resource_id": resource.id,
                            "kind": kind,
                            "return_action": action,
                            "page": page,
                        },
                    )
                ]
            )
        )

    nav: list[dict[str, Any]] = []
    if page > 0:
        nav.append(button("上一页", action, value={"page": page - 1}))
    if start + PAGE_SIZE < len(resources):
        nav.append(button("下一页", action, value={"page": page + 1}))
    nav.append(button("返回首页", "home"))
    elements.append(action_block(nav))
    return card(title, elements)


def credential_lines(credentials: ResourceCredentialRead | None, *, include_bmc: bool) -> list[str]:
    if credentials is None:
        return []
    lines = [
        f"**SSH 用户**：{display(credentials.ssh_username)}",
        f"**SSH 密码**：{display(credentials.ssh_password)}",
    ]
    if include_bmc:
        lines.extend(
            [
                f"**BMC 用户**：{display(credentials.bmc_username)}",
                f"**BMC 密码**：{display(credentials.bmc_password)}",
            ]
        )
    return lines


@dataclass(frozen=True)
class ResourceDetailCardRequest:
    """资源详情卡片入参。"""

    resource: ResourceRead
    credentials: ResourceCredentialRead | None
    return_action: str
    page: int
    can_run_remote_command: bool = False
    credential_error: str | None = None


def build_resource_detail_card(
    *,
    request: ResourceDetailCardRequest,
) -> dict[str, Any]:
    resource = request.resource
    credentials = request.credentials
    can_run_remote_command = request.can_run_remote_command
    credential_error = request.credential_error
    return_action = request.return_action
    page = request.page
    is_physical = resource.resource_type.value == "PHYSICAL"
    lines = [
        f"**资源编码**：{display(resource.resource_code)}",
        f"**OS IP**：{display(resource.primary_ip)}",
        f"**架构**：{display(resource.arch)}",
        f"**OS**：{display(resource.os_version)}",
        f"**内核**：{display(resource.kernel_version)}",
        f"**占用**：{resource_occupancy(resource)}",
        f"**使用场景**：{display(resource.usage_scenario)}",
    ]
    if is_physical:
        lines.extend(
            [
                f"**BMC IP**：{display(resource.bmc_ip)}",
                f"**CPU**：{display(resource.cpu_model)} / {display(resource.cpu_count)}",
                f"**内存**：{display(resource.memory_spec)}",
            ]
        )
    else:
        lines.extend(
            [
                f"**VM 名称**：{display(resource.vm_name or resource.name)}",
                f"**规格**：{display(resource.vcpu_count)} vCPU / {display(resource.memory_mb)} MB",
                f"**VNC**：{display(resource.host_primary_ip)}:{display(resource.vnc_port)}",
            ]
        )

    secret_lines = credential_lines(credentials, include_bmc=is_physical)
    if secret_lines:
        lines.extend(["", "**凭据**：", *secret_lines])
    elif credential_error:
        lines.extend(["", f"**凭据**：{credential_error}"])

    actions = [
        button("返回列表", return_action, value={"page": page}),
        button("返回首页", "home"),
    ]
    if can_run_remote_command and resource.primary_ip:
        actions.insert(
            0,
            primary_button(
                "远程命令",
                "remote_command_form",
                value={
                    "resource_id": resource.id,
                    "return_action": return_action,
                    "page": page,
                },
            ),
        )

    return card(
        "资源详情",
        [
            text_block("\n".join(lines)),
            action_block(actions),
        ],
    )


def remote_command_input_name(resource_id: str) -> str:
    return f"remote_command|{resource_id}"


def build_remote_command_form_card(
    *,
    resource: ResourceRead,
    command: str,
    return_action: str,
    page: int,
    error: str | None = None,
) -> dict[str, Any]:
    elements: list[dict[str, Any]] = [
        text_block(
            f"**目标资源**：{display(resource.resource_code)}\n"
            f"**OS IP**：{display(resource.primary_ip)}\n"
            f"**SSH 用户**：{display(resource.ssh_username)}"
        )
    ]
    if error:
        elements.append(text_block(f"**执行失败**：{error}"))
    elements.extend(
        [
            text_block("请直接在当前私聊发送要执行的单条命令，例如：`uname -a`。"),
            action_block(
                [
                    button(
                        "返回详情",
                        "resource_detail",
                        value={
                            "resource_id": resource.id,
                            "return_action": return_action,
                            "page": page,
                        },
                    ),
                ]
            ),
        ]
    )
    return card("远程命令", elements)


@dataclass(frozen=True)
class RemoteCommandResultCardRequest:
    """远程命令结果卡片入参。"""

    resource: ResourceRead
    command: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout: str
    stderr: str
    output_truncated: bool
    return_action: str
    page: int


def build_remote_command_result_card(
    *,
    request: RemoteCommandResultCardRequest,
) -> dict[str, Any]:
    resource = request.resource
    command = request.command
    exit_code = request.exit_code
    timed_out = request.timed_out
    duration_ms = request.duration_ms
    stdout = request.stdout
    stderr = request.stderr
    output_truncated = request.output_truncated
    return_action = request.return_action
    page = request.page
    status = "超时" if timed_out else f"退出码 {display(exit_code)}"
    output_lines = [
        f"**目标资源**：{display(resource.resource_code)}",
        f"**OS IP**：{display(resource.primary_ip)}",
        f"**命令**：`{command}`",
        f"**结果**：{status} / {duration_ms} ms",
    ]
    if stdout:
        output_lines.extend(["", "**stdout**：", f"```text\n{stdout}\n```"])
    if stderr:
        output_lines.extend(["", "**stderr**：", f"```text\n{stderr}\n```"])
    if not stdout and not stderr:
        output_lines.extend(["", "无输出。"])
    if output_truncated:
        output_lines.extend(["", "输出过长，已截断。"])

    return card(
        "远程命令结果",
        [
            text_block("\n".join(output_lines)),
            action_block(
                [
                    button(
                        "返回详情",
                        "resource_detail",
                        value={
                            "resource_id": resource.id,
                            "return_action": return_action,
                            "page": page,
                        },
                    ),
                    button("返回首页", "home"),
                ]
            ),
        ],
        template="green" if not timed_out and exit_code == 0 else "yellow",
    )


def unique_images(images: list[VMImage]) -> list[VMImage]:
    seen: set[str] = set()
    result: list[VMImage] = []
    for image in sorted(images, key=lambda item: (item.dist, item.os_version, item.image_round)):
        value = vm_image_value(image)
        if value in seen:
            continue
        seen.add(value)
        result.append(image)
    return result


def selected_image(images: list[VMImage], image_value: str | None) -> VMImage | None:
    for image in unique_images(images):
        if vm_image_value(image) == image_value:
            return image
    return unique_images(images)[0] if images else None


def arch_options_for(images: list[VMImage], image: VMImage | None) -> list[str]:
    if image is None:
        return sorted({item.arch for item in images})
    arches: set[str] = set()
    for item in images:
        if item.dist != image.dist:
            continue
        if item.os_version != image.os_version:
            continue
        if item.image_round != image.image_round:
            continue
        arches.add(item.arch)
    return sorted(arches)


def build_vm_create_card(
    *,
    images: list[VMImage],
    state: dict[str, str],
    error: str | None = None,
) -> dict[str, Any]:
    image = selected_image(images, state.get("image"))
    arch_values = arch_options_for(images, image)
    selected_arch = state.get("arch")
    if selected_arch not in {vm_arch_value(arch) for arch in arch_values}:
        selected_arch = vm_arch_value(arch_values[0]) if arch_values else None

    image_options = [
        option(f"{image.os_version} / {image.image_round}", vm_image_value(image))
        for image in unique_images(images)
    ]
    arch_options = [option(arch, vm_arch_value(arch)) for arch in arch_values]

    if not image_options or not arch_options:
        return card(
            "创建 VM",
            [
                text_block("没有可用 VM 镜像，请先检查镜像仓库。"),
                action_block([button("返回 VM 管理", "vm_menu")]),
            ],
            template="yellow",
        )

    elements: list[dict[str, Any]] = []
    if error:
        elements.append(text_block(f"**提交失败**：{error}"))
    elements.extend(
        [
            text_block("选择镜像并确认规格后提交申请。"),
            action_block(
                [
                    select_static(
                        placeholder="版本",
                        options=image_options,
                        initial_option=vm_image_value(image) if image else None,
                    )
                ]
            ),
            action_block(
                [
                    select_static(
                        placeholder="架构",
                        options=arch_options,
                        initial_option=selected_arch,
                    )
                ]
            ),
            text_block("vCPU（1-16）"),
            action_block(
                [
                    input_control(
                        name="vcpu_count",
                        placeholder="默认 2",
                        default_value=state.get("vcpu_count", "2"),
                        max_length=2,
                    )
                ]
            ),
            text_block("内存 GB（1-32）"),
            action_block(
                [
                    input_control(
                        name="memory_gb",
                        placeholder="默认 4",
                        default_value=state.get("memory_gb", "4"),
                        max_length=2,
                    )
                ]
            ),
            text_block("额外数据盘数量（0-4，每块 50 GB）"),
            action_block(
                [
                    input_control(
                        name="data_disk_count",
                        placeholder="默认 0",
                        default_value=state.get("data_disk_count", "0"),
                        max_length=1,
                    )
                ]
            ),
            text_block("额外网卡数量（0-4）"),
            action_block(
                [
                    input_control(
                        name="extra_nic_num",
                        placeholder="默认 0",
                        default_value=state.get("extra_nic_num", "0"),
                        max_length=1,
                    )
                ]
            ),
            text_block("租期天数（默认 1，管理员可填 0 表示永久）"),
            action_block(
                [
                    input_control(
                        name="lease_days",
                        placeholder="默认 1",
                        default_value=state.get("lease_days", "1"),
                        max_length=2,
                    )
                ]
            ),
            text_block("用途"),
            action_block(
                [
                    input_control(
                        name="purpose",
                        placeholder=VM_DEFAULT_PURPOSE,
                        default_value=state.get("purpose", VM_DEFAULT_PURPOSE),
                        max_length=512,
                    )
                ]
            ),
            action_block(
                [
                    primary_button(
                        "提交申请",
                        "vm_create_submit",
                        value={"form_id": state.get("form_id")},
                    ),
                    button("返回 VM 管理", "vm_menu"),
                ]
            ),
        ]
    )
    return card("创建 VM", elements)


def request_status_text(request: VMRequestRead) -> str:
    status_map = {
        "pending": "排队中",
        "creating": "创建中",
        "succeeded": "成功",
        "failed": "失败",
        "cancelled": "已取消",
    }
    return status_map.get(request.status.value, request.status.value)


def build_vm_request_detail_card(request: VMRequestRead) -> dict[str, Any]:
    lines = [
        f"**状态**：{request_status_text(request)}",
        f"**镜像**：{request.dist} / {request.os_version} / {request.image_round} / {request.arch}",
        f"**规格**：{request.vcpu_count} vCPU / {request.memory_mb // 1024} GB",
        f"**数据盘**：{request.data_disk_count} 块，每块 {request.data_disk_size_gb} GB",
        f"**用途**：{display(request.purpose)}",
        f"**到期**：{datetime_display(request.expected_ends_at)}",
    ]
    if request.error_message:
        lines.append(f"**错误**：{request.error_message}")

    return card(
        "VM 申请",
        [
            text_block("\n".join(lines)),
            action_block(
                [
                    primary_button(
                        "刷新状态",
                        "vm_request_detail",
                        value={"request_id": request.id},
                    ),
                    button("我的 VM", "vm_mine", value={"page": 0}),
                    button("返回 VM 管理", "vm_menu"),
                ]
            ),
        ],
        template="green" if request.status.value == "succeeded" else "blue",
    )
