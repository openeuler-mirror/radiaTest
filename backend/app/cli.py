# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import argparse
import getpass
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("kronos.cli")

from app.db.session import SessionLocal
from app.modules.idempotency.service import cleanup_idempotency_records
from app.modules.pipelines.seed import seed_module_templates, seed_pipeline_types
from app.modules.resources.schemas import ResourceCreate, ResourceUpdate
from app.modules.resources.service import (
    create_resource,
    get_resource_by_code,
    update_resource,
    upsert_install_image,
)
from app.modules.tasks.service import cleanup_task_events
from app.modules.users.models import UserRole
from app.modules.users.service import UserAlreadyExistsError, create_user

# 运维 CLI：在服务器本机执行，用于创建管理员、资源台账维护、清理历史
# 记录和 seed 模板/镜像。密码等敏感参数走交互输入或 stdin，不写进命令行历史。


def create_admin(args: argparse.Namespace) -> int:
    """创建 ADMIN 用户。密码未在命令行给出时交互读取，避免落进 shell 历史。"""
    password = args.password or getpass.getpass("Password: ")

    with SessionLocal() as db:
        try:
            create_user(
                db,
                username=args.username,
                password=password,
                role=UserRole.ADMIN,
                display_name=args.display_name,
            )
        except UserAlreadyExistsError:
            logger.info(f"User already exists: {args.username}")
            return 1

        db.commit()

    logger.info(f"Created ADMIN user: {args.username}")
    return 0


def seed_admin(args: argparse.Namespace) -> int:
    """
    幂等 admin seed（deploy 用）：ADMIN_USERNAME/ADMIN_PASSWORD 都配了且用户
    不存在才创建；未配或已存在都跳过。恒 return 0，不阻断 deploy。
    """
    from app.core.config import get_settings

    settings = get_settings()
    username = settings.admin_username
    password = settings.admin_password
    if not (username and password):
        logger.info("seed-admin: ADMIN_USERNAME/ADMIN_PASSWORD not configured, skip")
        return 0
    with SessionLocal() as db:
        try:
            create_user(
                db,
                username=username,
                password=password,
                role=UserRole.ADMIN,
                display_name=args.display_name or username,
            )
        except UserAlreadyExistsError:
            logger.info(f"seed-admin: {username} exists, skip")
            return 0
        db.commit()
    logger.info(f"seed-admin: created ADMIN user {username}")
    return 0


def upsert_resource(args: argparse.Namespace) -> int:
    """从 JSON 文件或 stdin 批量 upsert 资源台账，按 resource_code 判重。

    只导入资源本身，不导入租约——当前租约迁移用 Web CSV 导入入口。
    """
    raw_content = sys.stdin.read() if args.json_file == "-" else Path(args.json_file).read_text()
    raw_payload = json.loads(raw_content)
    records = raw_payload if isinstance(raw_payload, list) else [raw_payload]

    created = 0
    updated = 0
    with SessionLocal() as db:
        for raw_record in records:
            payload = ResourceCreate.model_validate(raw_record)
            existing = get_resource_by_code(db, payload.resource_code)
            if existing is None:
                create_resource(db, payload)
                created += 1
            else:
                update_payload = ResourceUpdate.model_validate(
                    {
                        key: value
                        for key, value in payload.model_dump(mode="json").items()
                        if key not in {"resource_code", "resource_type"}
                    }
                )
                update_resource(db, existing, update_payload)
                updated += 1
        db.commit()

    logger.info(f"Upserted resources: created={created} updated={updated}")
    return 0


def cleanup_task_events_command(args: argparse.Namespace) -> int:
    if args.days < 1:
        logger.error("--days must be greater than 0")
        return 2

    with SessionLocal() as db:
        deleted = cleanup_task_events(db, days=args.days)
        db.commit()

    logger.info(f"Deleted task events older than {args.days} days: {deleted}")
    return 0


def cleanup_idempotency_records_command(args: argparse.Namespace) -> int:
    if args.days < 1:
        logger.error("--days must be greater than 0")
        return 2

    with SessionLocal() as db:
        deleted = cleanup_idempotency_records(db, days=args.days)
        db.commit()

    logger.info(f"Deleted idempotency records older than {args.days} days: {deleted}")
    return 0


def seed_pipeline_templates(args: argparse.Namespace) -> int:
    """幂等 seed 测试流水线类型和模块模板，可重复执行。"""
    with SessionLocal() as db:
        types_created = seed_pipeline_types(db)
        templates_created = seed_module_templates(db)

    logger.info(
        "Seeded pipeline types: created=%s; module templates: created=%s",
        types_created,
        templates_created,
    )
    return 0


def seed_install_images(args: argparse.Namespace) -> int:
    """从 JSON 批量 seed 物理机 PXE 安装镜像，按 (os_version, arch) 幂等 upsert。

    缺字段的记录跳过不报错；URL 含内网地址，只从服务器本地文件读取，不进 Git。
    """
    raw_content = (
        sys.stdin.read() if args.json_file == "-" else Path(args.json_file).read_text()
    )
    raw_payload = json.loads(raw_content)
    records = raw_payload if isinstance(raw_payload, list) else [raw_payload]

    required = {"os_version", "arch", "efi_url", "repo_url"}
    created = 0
    updated = 0
    skipped = 0
    with SessionLocal() as db:
        for raw_record in records:
            missing = required - raw_record.keys()
            if missing:
                logger.error(
                    "跳过缺少字段 %s 的记录: %s",
                    sorted(missing),
                    raw_record,
                )
                skipped += 1
                continue
            is_created = upsert_install_image(
                db,
                os_version=raw_record["os_version"],
                arch=raw_record["arch"],
                efi_url=raw_record["efi_url"],
                repo_url=raw_record["repo_url"],
            )
            if is_created:
                created += 1
            else:
                updated += 1
        db.commit()

    logger.info(f"Seed install images: created={created} updated={updated} skipped={skipped}")
    return 0


def seed_rc_install_images(args: argparse.Namespace) -> int:
    """从 dailybuild 发现 RC 镜像 + 本地源登记，收敛 physical_install_images。

    复用 `sync_install_image_catalog`（发现/upsert/删旧 + 本地 OS 树登记），
    与列表接口的后台刷新同源，避免逻辑分叉。
    """
    from app.core.config import get_settings
    from app.modules.resources.install_sources import sync_install_image_catalog

    with SessionLocal() as db:
        total = sync_install_image_catalog(
            db, mirror_base=get_settings().install_mirror_base
        )
    logger.info(f"RC install images catalog synced: total={total}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """构建运维 CLI 的子命令解析器。"""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser("create-admin")
    create_admin_parser.add_argument("--username", required=True)
    create_admin_parser.add_argument("--password")
    create_admin_parser.add_argument("--display-name")
    create_admin_parser.set_defaults(func=create_admin)

    seed_admin_parser = subparsers.add_parser("seed-admin")
    seed_admin_parser.add_argument("--display-name")
    seed_admin_parser.set_defaults(func=seed_admin)

    upsert_resource_parser = subparsers.add_parser("upsert-resource")
    upsert_resource_parser.add_argument("--json-file", required=True)
    upsert_resource_parser.set_defaults(func=upsert_resource)

    cleanup_task_events_parser = subparsers.add_parser("cleanup-task-events")
    cleanup_task_events_parser.add_argument("--days", default=30, type=int)
    cleanup_task_events_parser.set_defaults(func=cleanup_task_events_command)

    cleanup_idempotency_records_parser = subparsers.add_parser("cleanup-idempotency-records")
    cleanup_idempotency_records_parser.add_argument("--days", default=7, type=int)
    cleanup_idempotency_records_parser.set_defaults(func=cleanup_idempotency_records_command)

    seed_pipeline_parser = subparsers.add_parser("seed-pipeline-templates")
    seed_pipeline_parser.set_defaults(func=seed_pipeline_templates)

    seed_install_images_parser = subparsers.add_parser("seed-install-images")
    seed_install_images_parser.add_argument("--json-file", required=True)
    seed_install_images_parser.set_defaults(func=seed_install_images)

    seed_rc_parser = subparsers.add_parser("seed-rc-install-images")
    seed_rc_parser.set_defaults(func=seed_rc_install_images)

    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
