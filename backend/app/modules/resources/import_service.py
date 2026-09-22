# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.modules.resources.schemas import (
    ResourceCreate,
    ResourceImportRequest,
    ResourceImportResult,
    ResourceImportRowResult,
)
from app.modules.resources.service import (
    ResourceAlreadyExistsError,
    create_resource,
    get_resource_by_code,
)

# 资源 CSV 导入解析：先全量校验(格式 + 重复码 + 已存在码)，再逐行创建。
# dry_run 只校验不落库；正式导入由路由层套幂等闭环，此处只负责行级处理。

INT_FIELDS = {
    "cpu_count",
    "disk_gb",
    "hdd_count",
    "memory_count",
    "memory_mb",
    "ssd_card_count",
    "ssd_count",
    "vcpu_count",
    "vnc_port",
    "vnc_websocket_port",
}
BOOL_FIELDS = {"is_critical"}
DEFAULTED_FIELDS = {
    "connectivity_status",
    "is_critical",
    "management_status",
    "resource_type",
    "tags",
    "extra",
}
RESOURCE_FIELDS = set(ResourceCreate.model_fields)


class ResourceImportFormatError(Exception):
    """CSV 格式错误(缺少表头等)，导入前置校验失败。"""


def normalize_header(header: str | None) -> str:
    """去掉 BOM 与首尾空白，规范化 CSV 表头以便与字段名匹配。"""
    return (header or "").strip().lstrip("\ufeff")


def normalize_cell(value: str | None) -> str:
    return (value or "").strip()


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "是"}:
        return True
    if normalized in {"0", "false", "no", "n", "否"}:
        return False
    raise ValueError("must be a boolean")


def parse_tags(value: str) -> list[str]:
    """解析 tags 列：JSON 数组优先，否则按逗号/分号(中英)分隔为列表。"""
    if not value:
        return []
    if value.startswith("["):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise ValueError("tags must be a list")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in re.split(r"[,;，；]", value) if item.strip()]


def parse_extra(value: str) -> dict[str, object]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("extra must be an object")
    return parsed


def parse_csv(content: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if reader.fieldnames is None:
        raise ResourceImportFormatError("CSV header is required")
    reader.fieldnames = [normalize_header(field_name) for field_name in reader.fieldnames]
    return [{normalize_header(key): value for key, value in row.items()} for row in reader]


def row_to_payload_data(row: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    """把一行 CSV 转成 ResourceCreate 的字段 dict 与错误列表。

    已知字段按类型强转(int/bool/tags/extra)，未知列若有值并入 extra。
    空值非默认字段置 None；data_disk_paths 空值置空列表。转换错误收集到
    errors 列表，由上层决定该行是否跳过。
    """
    data: dict[str, Any] = {}
    extra: dict[str, object] = {}
    errors: list[str] = []

    for key, raw_value in row.items():
        if not key:
            continue
        value = normalize_cell(raw_value)
        if key not in RESOURCE_FIELDS:
            if value:
                extra[key] = value
            continue
        if not value:
            if key == "data_disk_paths":
                data[key] = []
            elif key not in DEFAULTED_FIELDS:
                data[key] = None
            continue
        try:
            if key in INT_FIELDS:
                data[key] = int(value)
            elif key in BOOL_FIELDS:
                data[key] = parse_bool(value)
            elif key == "tags":
                data[key] = parse_tags(value)
            elif key == "data_disk_paths":
                data[key] = parse_tags(value)
            elif key == "extra":
                parsed_extra = parse_extra(value)
                extra.update(parsed_extra)
            else:
                data[key] = value
        except ValueError as exc:
            errors.append(f"{key}: {exc}")

    if extra:
        data["extra"] = {**data.get("extra", {}), **extra}
    return data, errors


def validation_error_messages(exc: ValidationError) -> list[str]:
    messages = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error["loc"]) or "row"
        messages.append(f"{location}: {error['msg']}")
    return messages


def import_resources(db: Session, payload: ResourceImportRequest) -> ResourceImportResult:
    """导入资源 CSV：先解析+重复码检测+逐行校验，dry_run 只校验不落库。

    行号从 2 起(1 为表头)。每行独立判定：格式错或 resource_code 在 CSV 内
    重复或库内已存在则记 error；否则 dry_run 记 validated，正式导入逐行
    create_resource(并发冲突再记 error)。返回逐行结果汇总。
    """
    raw_rows = parse_csv(payload.content)
    resource_codes = [
        normalize_cell(row.get("resource_code"))
        for row in raw_rows
        if normalize_cell(row.get("resource_code"))
    ]
    duplicated_codes = {
        resource_code for resource_code, count in Counter(resource_codes).items() if count > 1
    }

    row_results: list[ResourceImportRowResult] = []
    valid_rows: list[tuple[int, ResourceCreate]] = []

    for index, row in enumerate(raw_rows, start=2):
        data, errors = row_to_payload_data(row)
        resource_code = normalize_cell(row.get("resource_code")) or None
        primary_ip = normalize_cell(row.get("primary_ip")) or None

        if resource_code in duplicated_codes:
            errors.append("resource_code is duplicated in CSV")
        if resource_code and get_resource_by_code(db, resource_code) is not None:
            errors.append("resource_code already exists")

        resource_payload: ResourceCreate | None = None
        if not errors:
            try:
                resource_payload = ResourceCreate.model_validate(data)
            except ValidationError as exc:
                errors.extend(validation_error_messages(exc))

        if errors or resource_payload is None:
            row_results.append(
                ResourceImportRowResult(
                    row_number=index,
                    resource_code=resource_code,
                    primary_ip=primary_ip,
                    status="error",
                    errors=errors,
                )
            )
            continue

        if payload.dry_run:
            row_results.append(
                ResourceImportRowResult(
                    row_number=index,
                    resource_code=resource_payload.resource_code,
                    primary_ip=resource_payload.primary_ip,
                    status="validated",
                )
            )
        else:
            valid_rows.append((index, resource_payload))

    if not payload.dry_run:
        for row_number, resource_payload in valid_rows:
            try:
                created = create_resource(db, resource_payload)
            except ResourceAlreadyExistsError:
                row_results.append(
                    ResourceImportRowResult(
                        row_number=row_number,
                        resource_code=resource_payload.resource_code,
                        primary_ip=resource_payload.primary_ip,
                        status="error",
                        errors=["resource_code already exists"],
                    )
                )
                continue
            row_results.append(
                ResourceImportRowResult(
                    row_number=row_number,
                    resource_code=created.resource_code,
                    primary_ip=created.primary_ip,
                    status="created",
                )
            )

    row_results.sort(key=lambda row: row.row_number)
    success_count = sum(row.status in {"created", "validated"} for row in row_results)
    error_count = sum(row.status == "error" for row in row_results)
    return ResourceImportResult(
        dry_run=payload.dry_run,
        total_rows=len(raw_rows),
        success_count=success_count,
        error_count=error_count,
        rows=row_results,
    )
