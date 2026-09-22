# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""split resource specs and encrypt credentials

Revision ID: 20260627_0003
Revises: 20260627_0002
Create Date: 2026-06-27
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from cryptography.fernet import Fernet

from alembic import op

revision: str = "20260627_0003"
down_revision: str | None = "20260627_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def credential_cipher() -> Fernet:
    secret_key = os.environ.get("RESOURCE_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("RESOURCE_SECRET_KEY is required for credential migration")
    return Fernet(secret_key.encode())


def encrypt_value(cipher: Fernet, value: str | None) -> str | None:
    if not value:
        return None
    return cipher.encrypt(value.encode()).decode()


def decrypt_value(cipher: Fernet, value: str | None) -> str | None:
    if not value:
        return None
    return cipher.decrypt(value.encode()).decode()


def upgrade() -> None:
    op.create_table(
        "physical_resource_specs",
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("device_location", sa.String(length=255), nullable=True),
        sa.Column("device_distribution", sa.String(length=64), nullable=True),
        sa.Column("bmc_ip", sa.String(length=64), nullable=True),
        sa.Column("bmc_username", sa.String(length=64), nullable=True),
        sa.Column("bmc_password_ciphertext", sa.Text(), nullable=True),
        sa.Column("cpu_model", sa.String(length=128), nullable=True),
        sa.Column("cpu_count", sa.Integer(), nullable=True),
        sa.Column("memory_count", sa.Integer(), nullable=True),
        sa.Column("memory_spec", sa.String(length=255), nullable=True),
        sa.Column("hdd_count", sa.Integer(), nullable=True),
        sa.Column("hdd_spec", sa.String(length=255), nullable=True),
        sa.Column("ssd_count", sa.Integer(), nullable=True),
        sa.Column("ssd_spec", sa.String(length=255), nullable=True),
        sa.Column("ssd_card_count", sa.Integer(), nullable=True),
        sa.Column("ssd_card_spec", sa.String(length=255), nullable=True),
        sa.Column("system_sn", sa.String(length=128), nullable=True),
        sa.Column("board_sn", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("resource_id"),
    )
    op.create_index(
        op.f("ix_physical_resource_specs_bmc_ip"),
        "physical_resource_specs",
        ["bmc_ip"],
        unique=False,
    )

    op.create_table(
        "virtual_resource_specs",
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("vnc_port", sa.Integer(), nullable=True),
        sa.Column("vcpu_count", sa.Integer(), nullable=True),
        sa.Column("memory_mb", sa.Integer(), nullable=True),
        sa.Column("disk_gb", sa.Integer(), nullable=True),
        sa.Column("host_resource_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("resource_id"),
    )

    op.add_column("resources", sa.Column("ssh_password_ciphertext", sa.Text(), nullable=True))

    bind = op.get_bind()
    cipher = credential_cipher()
    resources = bind.execute(sa.text("SELECT * FROM resources")).mappings().all()
    for resource in resources:
        bind.execute(
            sa.text(
                """
                UPDATE resources
                SET ssh_password_ciphertext = :ssh_password_ciphertext
                WHERE id = :resource_id
                """
            ),
            {
                "resource_id": resource["id"],
                "ssh_password_ciphertext": encrypt_value(cipher, resource["ssh_password"]),
            },
        )

        if resource["resource_type"] == "PHYSICAL":
            bind.execute(
                sa.text(
                    """
                    INSERT INTO physical_resource_specs (
                        resource_id,
                        device_location,
                        device_distribution,
                        bmc_ip,
                        bmc_username,
                        bmc_password_ciphertext,
                        cpu_model,
                        cpu_count,
                        memory_count,
                        memory_spec,
                        hdd_count,
                        hdd_spec,
                        ssd_count,
                        ssd_spec,
                        ssd_card_count,
                        ssd_card_spec,
                        system_sn,
                        board_sn
                    )
                    VALUES (
                        :resource_id,
                        :device_location,
                        :device_distribution,
                        :bmc_ip,
                        :bmc_username,
                        :bmc_password_ciphertext,
                        :cpu_model,
                        :cpu_count,
                        :memory_count,
                        :memory_spec,
                        :hdd_count,
                        :hdd_spec,
                        :ssd_count,
                        :ssd_spec,
                        :ssd_card_count,
                        :ssd_card_spec,
                        :system_sn,
                        :board_sn
                    )
                    """
                ),
                {
                    "resource_id": resource["id"],
                    "device_location": resource["device_location"],
                    "device_distribution": resource["device_distribution"],
                    "bmc_ip": resource["bmc_ip"],
                    "bmc_username": resource["bmc_username"],
                    "bmc_password_ciphertext": encrypt_value(cipher, resource["bmc_password"]),
                    "cpu_model": resource["cpu_model"],
                    "cpu_count": resource["cpu_count"],
                    "memory_count": resource["memory_count"],
                    "memory_spec": resource["memory_spec"],
                    "hdd_count": resource["hdd_count"],
                    "hdd_spec": resource["hdd_spec"],
                    "ssd_count": resource["ssd_count"],
                    "ssd_spec": resource["ssd_spec"],
                    "ssd_card_count": resource["ssd_card_count"],
                    "ssd_card_spec": resource["ssd_card_spec"],
                    "system_sn": resource["system_sn"],
                    "board_sn": resource["board_sn"],
                },
            )

        if resource["resource_type"] == "VIRTUAL":
            bind.execute(
                sa.text(
                    """
                    INSERT INTO virtual_resource_specs (
                        resource_id,
                        vnc_port,
                        vcpu_count,
                        memory_mb,
                        disk_gb,
                        host_resource_id
                    )
                    VALUES (
                        :resource_id,
                        :vnc_port,
                        :vcpu_count,
                        :memory_mb,
                        :disk_gb,
                        :host_resource_id
                    )
                    """
                ),
                {
                    "resource_id": resource["id"],
                    "vnc_port": resource["vnc_port"],
                    "vcpu_count": resource["vcpu_count"],
                    "memory_mb": resource["memory_mb"],
                    "disk_gb": resource["disk_gb"],
                    "host_resource_id": resource["host_resource_id"],
                },
            )

    op.alter_column("resources", "ssh_password_ciphertext", nullable=False)
    op.drop_column("resources", "ssh_password")
    op.drop_index(op.f("ix_resources_bmc_ip"), table_name="resources")
    op.drop_column("resources", "device_location")
    op.drop_column("resources", "device_distribution")
    op.drop_column("resources", "bmc_ip")
    op.drop_column("resources", "bmc_username")
    op.drop_column("resources", "bmc_password")
    op.drop_column("resources", "cpu_model")
    op.drop_column("resources", "cpu_count")
    op.drop_column("resources", "memory_count")
    op.drop_column("resources", "memory_spec")
    op.drop_column("resources", "hdd_count")
    op.drop_column("resources", "hdd_spec")
    op.drop_column("resources", "ssd_count")
    op.drop_column("resources", "ssd_spec")
    op.drop_column("resources", "ssd_card_count")
    op.drop_column("resources", "ssd_card_spec")
    op.drop_column("resources", "system_sn")
    op.drop_column("resources", "board_sn")
    op.drop_column("resources", "vnc_port")
    op.drop_column("resources", "vcpu_count")
    op.drop_column("resources", "memory_mb")
    op.drop_column("resources", "disk_gb")
    op.drop_column("resources", "host_resource_id")


def downgrade() -> None:
    op.add_column("resources", sa.Column("ssh_password", sa.String(length=512), nullable=True))
    op.add_column("resources", sa.Column("device_location", sa.String(length=255), nullable=True))
    op.add_column(
        "resources",
        sa.Column("device_distribution", sa.String(length=64), nullable=True),
    )
    op.add_column("resources", sa.Column("bmc_ip", sa.String(length=64), nullable=True))
    op.add_column("resources", sa.Column("bmc_username", sa.String(length=64), nullable=True))
    op.add_column("resources", sa.Column("bmc_password", sa.String(length=512), nullable=True))
    op.add_column("resources", sa.Column("cpu_model", sa.String(length=128), nullable=True))
    op.add_column("resources", sa.Column("cpu_count", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("memory_count", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("memory_spec", sa.String(length=255), nullable=True))
    op.add_column("resources", sa.Column("hdd_count", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("hdd_spec", sa.String(length=255), nullable=True))
    op.add_column("resources", sa.Column("ssd_count", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("ssd_spec", sa.String(length=255), nullable=True))
    op.add_column("resources", sa.Column("ssd_card_count", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("ssd_card_spec", sa.String(length=255), nullable=True))
    op.add_column("resources", sa.Column("system_sn", sa.String(length=128), nullable=True))
    op.add_column("resources", sa.Column("board_sn", sa.String(length=128), nullable=True))
    op.add_column("resources", sa.Column("vnc_port", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("vcpu_count", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("memory_mb", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("disk_gb", sa.Integer(), nullable=True))
    op.add_column("resources", sa.Column("host_resource_id", sa.String(length=36), nullable=True))

    bind = op.get_bind()
    cipher = credential_cipher()
    resources = (
        bind.execute(sa.text("SELECT id, ssh_password_ciphertext FROM resources"))
        .mappings()
        .all()
    )
    for resource in resources:
        bind.execute(
            sa.text("UPDATE resources SET ssh_password = :ssh_password WHERE id = :resource_id"),
            {
                "resource_id": resource["id"],
                "ssh_password": decrypt_value(cipher, resource["ssh_password_ciphertext"]),
            },
        )

    physical_specs = bind.execute(sa.text("SELECT * FROM physical_resource_specs")).mappings().all()
    for spec in physical_specs:
        bind.execute(
            sa.text(
                """
                UPDATE resources
                SET device_location = :device_location,
                    device_distribution = :device_distribution,
                    bmc_ip = :bmc_ip,
                    bmc_username = :bmc_username,
                    bmc_password = :bmc_password,
                    cpu_model = :cpu_model,
                    cpu_count = :cpu_count,
                    memory_count = :memory_count,
                    memory_spec = :memory_spec,
                    hdd_count = :hdd_count,
                    hdd_spec = :hdd_spec,
                    ssd_count = :ssd_count,
                    ssd_spec = :ssd_spec,
                    ssd_card_count = :ssd_card_count,
                    ssd_card_spec = :ssd_card_spec,
                    system_sn = :system_sn,
                    board_sn = :board_sn
                WHERE id = :resource_id
                """
            ),
            {
                "resource_id": spec["resource_id"],
                "device_location": spec["device_location"],
                "device_distribution": spec["device_distribution"],
                "bmc_ip": spec["bmc_ip"],
                "bmc_username": spec["bmc_username"],
                "bmc_password": decrypt_value(cipher, spec["bmc_password_ciphertext"]),
                "cpu_model": spec["cpu_model"],
                "cpu_count": spec["cpu_count"],
                "memory_count": spec["memory_count"],
                "memory_spec": spec["memory_spec"],
                "hdd_count": spec["hdd_count"],
                "hdd_spec": spec["hdd_spec"],
                "ssd_count": spec["ssd_count"],
                "ssd_spec": spec["ssd_spec"],
                "ssd_card_count": spec["ssd_card_count"],
                "ssd_card_spec": spec["ssd_card_spec"],
                "system_sn": spec["system_sn"],
                "board_sn": spec["board_sn"],
            },
        )

    virtual_specs = bind.execute(sa.text("SELECT * FROM virtual_resource_specs")).mappings().all()
    for spec in virtual_specs:
        bind.execute(
            sa.text(
                """
                UPDATE resources
                SET vnc_port = :vnc_port,
                    vcpu_count = :vcpu_count,
                    memory_mb = :memory_mb,
                    disk_gb = :disk_gb,
                    host_resource_id = :host_resource_id
                WHERE id = :resource_id
                """
            ),
            {
                "resource_id": spec["resource_id"],
                "vnc_port": spec["vnc_port"],
                "vcpu_count": spec["vcpu_count"],
                "memory_mb": spec["memory_mb"],
                "disk_gb": spec["disk_gb"],
                "host_resource_id": spec["host_resource_id"],
            },
        )

    op.alter_column("resources", "ssh_password", nullable=False)
    op.create_index(op.f("ix_resources_bmc_ip"), "resources", ["bmc_ip"], unique=False)
    op.drop_column("resources", "ssh_password_ciphertext")
    op.drop_table("virtual_resource_specs")
    op.drop_index(op.f("ix_physical_resource_specs_bmc_ip"), table_name="physical_resource_specs")
    op.drop_table("physical_resource_specs")
