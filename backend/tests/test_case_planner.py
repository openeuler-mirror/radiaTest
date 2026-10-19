# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.pipelines.case_planner import (
    CasePlan,
    plan_cases,
)
from app.modules.test_management.models import MugenCase


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()


def _insert_mugen_case(
    db: Session,
    *,
    suite: str,
    case: str,
    env_type: str = "vm",
    commit_sha: str = "abc123",
) -> None:
    db.add(MugenCase(
        suite_name=suite,
        case_name=case,
        env_type=env_type,
        node_num=1,
        add_disk_num=0,
        add_nic_num=0,
        raw_data={},
        commit_sha=commit_sha,
    ))
    db.commit()


def test_plan_cases_matches_packages_to_mugen_index(
    db_session: Session,
) -> None:
    _insert_mugen_case(db_session, suite="bash", case="oe_test_bash", env_type="vm")
    _insert_mugen_case(
        db_session, suite="network-tools", case="oe_test_ntool", env_type="physical"
    )

    plan = plan_cases(
        db_session,
        packages=["bash", "network-tools", "no-case-pkg"],
        suite_name_prefix="cli-test",
    )

    assert isinstance(plan, CasePlan)
    assert len(plan.vm_cases) == 1
    assert plan.vm_cases[0].suite_name == "bash"
    assert plan.vm_cases[0].case_name == "oe_test_bash"
    assert len(plan.physical_cases) == 1
    assert plan.physical_cases[0].suite_name == "network-tools"
    assert len(plan.no_case_packages) == 1
    assert plan.no_case_packages[0] == "no-case-pkg"


def test_plan_cases_empty_package_list(db_session: Session) -> None:
    _insert_mugen_case(db_session, suite="bash", case="oe_test_bash")
    plan = plan_cases(db_session, packages=[], suite_name_prefix="cli-test")
    assert plan.vm_cases == []
    assert plan.physical_cases == []
    assert plan.no_case_packages == []


def test_plan_cases_all_matched(db_session: Session) -> None:
    _insert_mugen_case(db_session, suite="bash", case="oe_test_bash", env_type="vm")
    _insert_mugen_case(db_session, suite="curl", case="oe_test_curl", env_type="vm")
    plan = plan_cases(
        db_session, packages=["bash", "curl"], suite_name_prefix="cli-test"
    )
    assert len(plan.vm_cases) == 2
    assert plan.physical_cases == []
    assert plan.no_case_packages == []


def test_plan_cases_service_test_suite(db_session: Session) -> None:
    _insert_mugen_case(
        db_session,
        suite="service-test",
        case="oe_test_service_restart",
        env_type="vm",
    )
    _insert_mugen_case(
        db_session,
        suite="service-test",
        case="oe_test_service_firewalld",
        env_type="physical",
    )
    plan = plan_cases(
        db_session,
        packages=["service-test"],
        suite_name_prefix="service-test",
    )
    assert len(plan.vm_cases) == 1
    assert plan.vm_cases[0].case_name == "oe_test_service_restart"
    assert len(plan.physical_cases) == 1
    assert plan.physical_cases[0].case_name == "oe_test_service_firewalld"
