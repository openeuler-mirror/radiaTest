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
from collections import Counter

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.modules.leases.schemas import (
    LeaseCreate,
    LeaseImportRequest,
    LeaseImportResult,
    LeaseImportRowResult,
)
from app.modules.leases.service import (
    LeaseConflictError,
    LeasePolicyError,
    create_lease,
    get_resource_active_lease,
)
from app.modules.resources.models import Resource
from app.modules.resources.service import get_resource_by_code
from app.modules.users.models import User
from app.modules.users.service import get_user_by_username


class LeaseImportFormatError(Exception):
    pass


def normalize_header(header: str | None) -> str:
    return (header or "").strip().lstrip("\ufeff")


def normalize_cell(value: str | None) -> str:
    return (value or "").strip()


def parse_csv(content: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if reader.fieldnames is None:
        raise LeaseImportFormatError("CSV header is required")
    reader.fieldnames = [normalize_header(field_name) for field_name in reader.fieldnames]
    return [{normalize_header(key): value for key, value in row.items()} for row in reader]


def validation_error_messages(exc: ValidationError) -> list[str]:
    messages = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error["loc"]) or "row"
        messages.append(f"{location}: {error['msg']}")
    return messages


def validate_lease_row(
    db: Session,
    row: dict[str, str],
    duplicated_codes: set[str],
) -> tuple[LeaseCreate | None, Resource | None, User | None, list[str]]:
    errors: list[str] = []
    resource_code = normalize_cell(row.get("resource_code"))
    primary_ip = normalize_cell(row.get("primary_ip"))
    lease_owner = normalize_cell(row.get("lease_owner"))
    occupancy_status = normalize_cell(row.get("occupancy_status"))
    lease_type = normalize_cell(row.get("lease_type")).lower()
    purpose = normalize_cell(row.get("purpose"))
    expected_ends_at = normalize_cell(row.get("expected_ends_at"))

    if not resource_code:
        errors.append("resource_code is required")
    if resource_code in duplicated_codes:
        errors.append("resource_code is duplicated in CSV")
    if not lease_owner:
        errors.append("lease_owner is required")
    if occupancy_status and occupancy_status != "occupied":
        errors.append("occupancy_status must be occupied")
    if lease_type and lease_type not in {"permanent", "timed"}:
        errors.append("lease_type must be permanent or timed")
    if lease_type == "permanent" and expected_ends_at:
        errors.append("permanent lease must not set expected_ends_at")

    resource = get_resource_by_code(db, resource_code) if resource_code else None
    if resource_code and resource is None:
        errors.append("resource_code does not exist")
    if resource is not None and primary_ip and resource.primary_ip != primary_ip:
        errors.append("primary_ip does not match resource")
    if resource is not None and get_resource_active_lease(db, resource) is not None:
        errors.append("resource is already occupied")

    owner = get_user_by_username(db, lease_owner) if lease_owner else None
    if lease_owner and owner is None:
        errors.append("lease_owner does not exist")
    if owner is not None and not owner.is_active:
        errors.append("lease_owner is disabled")

    lease_payload: LeaseCreate | None = None
    if not errors:
        try:
            lease_payload = LeaseCreate.model_validate(
                {
                    "purpose": purpose,
                    "expected_ends_at": expected_ends_at or None,
                }
            )
        except ValidationError as exc:
            errors.extend(validation_error_messages(exc))

    return lease_payload, resource, owner, errors


def import_leases(db: Session, payload: LeaseImportRequest) -> LeaseImportResult:
    raw_rows = parse_csv(payload.content)
    resource_codes = [
        normalize_cell(row.get("resource_code"))
        for row in raw_rows
        if normalize_cell(row.get("resource_code"))
    ]
    duplicated_codes = {
        resource_code for resource_code, count in Counter(resource_codes).items() if count > 1
    }

    row_results: list[LeaseImportRowResult] = []
    valid_rows = []

    for index, row in enumerate(raw_rows, start=2):
        resource_code = normalize_cell(row.get("resource_code")) or None
        primary_ip = normalize_cell(row.get("primary_ip")) or None
        lease_payload, resource, owner, errors = validate_lease_row(db, row, duplicated_codes)

        row_has_error = errors or lease_payload is None
        row_incomplete = resource is None or owner is None
        if row_has_error or row_incomplete:
            row_results.append(
                LeaseImportRowResult(
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
                LeaseImportRowResult(
                    row_number=index,
                    resource_code=resource.resource_code,
                    primary_ip=resource.primary_ip,
                    status="validated",
                )
            )
        else:
            valid_rows.append((index, resource, owner, lease_payload))

    if not payload.dry_run:
        for row_number, resource, owner, lease_payload in valid_rows:
            try:
                create_lease(db, resource=resource, actor=owner, payload=lease_payload)
            except (LeaseConflictError, LeasePolicyError) as exc:
                row_results.append(
                    LeaseImportRowResult(
                        row_number=row_number,
                        resource_code=resource.resource_code,
                        primary_ip=resource.primary_ip,
                        status="error",
                        errors=[str(exc)],
                    )
                )
                continue
            row_results.append(
                LeaseImportRowResult(
                    row_number=row_number,
                    resource_code=resource.resource_code,
                    primary_ip=resource.primary_ip,
                    status="created",
                )
            )

    row_results.sort(key=lambda row: row.row_number)
    success_count = sum(row.status in {"created", "validated"} for row in row_results)
    error_count = sum(row.status == "error" for row in row_results)
    return LeaseImportResult(
        dry_run=payload.dry_run,
        total_rows=len(raw_rows),
        success_count=success_count,
        error_count=error_count,
        rows=row_results,
    )
