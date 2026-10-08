# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import json
import subprocess
import sys
from dataclasses import dataclass
from collections.abc import Generator
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import process_runner
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.feishu.bot_runtime import (
    FeishuBotHandler,
    FeishuIncomingMessage,
    extract_text_content,
    parse_card_action_event,
    parse_sdk_event,
)
from app.modules.feishu.card_actions import reset_vm_create_state
from app.modules.feishu.cards import build_home_card, datetime_display
from app.modules.feishu.commands import FeishuBotAction, parse_private_text_command
from app.modules.feishu.models import FeishuAppConfig, UserIdentity
from app.modules.feishu.oauth import create_oauth_state, decode_oauth_state
from app.modules.feishu.remote_command import RemoteCommandRequest, RemoteCommandResult, execute_remote_command
from app.modules.feishu.schemas import FeishuIdentityBind
from app.modules.feishu.service import (
    FeishuIdentityConflictError,
    bind_feishu_identity,
    get_bound_user_for_feishu_actor,
)
from app.modules.leases.schemas import LeaseCreate
from app.modules.leases.service import create_lease
from app.modules.pipelines.models import PipelineConfig, PipelineExecution
from app.modules.pipelines.seed import seed_pipeline_types
from app.modules.resources.models import ResourceType
from app.modules.resources.schemas import ResourceCreate
from app.modules.resources.service import create_resource
from app.modules.users.models import User, UserRole
from app.modules.users.service import create_user
from app.modules.vms import service as vm_service
from app.modules.vms.image_discovery import VMImage
from app.modules.vms.models import VMRequest, VMRequestStatus


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _seed_pipeline_types(db_session: Session) -> None:
    seed_pipeline_types(db_session)


@pytest.fixture(autouse=True)
def clear_feishu_card_state() -> Generator[None, None, None]:
    reset_vm_create_state()
    yield
    reset_vm_create_state()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def add_user(
    db: Session,
    *,
    username: str,
    role: UserRole,
    password: str = "test-pass",
) -> User:
    user = create_user(
        db,
        username=username,
        password=password,
        role=role,
        display_name=username,
    )
    db.commit()
    return user


def login(client: TestClient, username: str, password: str = "test-pass") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_feishu_config(db: Session) -> FeishuAppConfig:
    config = FeishuAppConfig(
        environment="development",
        app_id="cli_test",
        app_secret="secret-value",
        is_enabled=True,
    )
    db.add(config)
    db.commit()
    return config


def physical_resource_payload(**overrides: object) -> ResourceCreate:
    payload: dict[str, object] = {
        "resource_code": "SN000000000001",
        "resource_type": ResourceType.PHYSICAL,
        "name": "TaiShan 200",
        "primary_ip": "172.168.131.75",
        "mac_address": "aa:bb:cc:dd:ee:75",
        "arch": "aarch64",
        "os_version": "openEuler-24.03-LTS-SP4",
        "kernel_version": "6.6.0-test",
        "ssh_username": "root",
        "ssh_password": "ssh-pass",
        "bmc_ip": "170.70.30.75",
        "bmc_username": "Administrator",
        "bmc_password": "bmc-pass",
        "cpu_model": "Kunpeng",
        "cpu_count": 2,
        "memory_spec": "32G * 12",
        "usage_scenario": "CI公共机器",
    }
    payload.update(overrides)
    return ResourceCreate.model_validate(payload)


def virtual_resource_payload(**overrides: object) -> ResourceCreate:
    payload: dict[str, object] = {
        "resource_code": "vm-uuid-1",
        "resource_type": ResourceType.VIRTUAL,
        "name": "openEuler-vm",
        "primary_ip": "172.168.132.10",
        "mac_address": "52:54:00:00:00:10",
        "arch": "aarch64",
        "os_version": "openEuler-24.03-LTS-SP4",
        "kernel_version": "6.6.0-test",
        "ssh_username": "root",
        "ssh_password": "vm-pass",
        "vm_name": "openEuler-vm",
        "vnc_port": 5901,
        "vnc_websocket_port": 5701,
        "vcpu_count": 2,
        "memory_mb": 4096,
        "disk_gb": 50,
    }
    payload.update(overrides)
    return ResourceCreate.model_validate(payload)


def vm_image(
    *,
    os_version: str = "openEuler-24.03-LTS-SP4",
    image_round: str = "round-9",
    arch: str = "aarch64",
) -> VMImage:
    return VMImage(
        dist="openEuler",
        os_version=os_version,
        image_round=image_round,
        arch=arch,
        url=f"http://repo/{os_version}/{image_round}/{arch}/{os_version}-{arch}.qcow2",
    )


@dataclass(frozen=True)
class CardActionContext:
    """card_action_event 的可选上下文（事件 ID 与表单值）。"""

    event_id: str | None = None
    header_event_id: str | None = None
    action_form_value: dict[str, object] | None = None


def card_action_event(
    action: str,
    *,
    open_id: str = "ou_te1",
    union_id: str | None = "on_te1",
    context: CardActionContext = CardActionContext(),
    **value: object,
) -> SimpleNamespace:
    return SimpleNamespace(
        event_id=context.event_id,
        header=SimpleNamespace(event_id=context.header_event_id),
        event=SimpleNamespace(
            operator=SimpleNamespace(open_id=open_id, union_id=union_id),
            action=SimpleNamespace(
                value={"action": action, **value}, form_value=context.action_form_value
            ),
        ),
    )


def card_select_event(
    option: str,
    *,
    name: str | None = None,
    open_id: str = "ou_te1",
    union_id: str | None = "on_te1",
) -> SimpleNamespace:
    return SimpleNamespace(
        event=SimpleNamespace(
            operator=SimpleNamespace(open_id=open_id, union_id=union_id),
            action=SimpleNamespace(value=None, tag="select_static", option=option, name=name),
        )
    )


def card_input_event(
    name: str,
    input_value: str,
    *,
    open_id: str = "ou_te1",
    union_id: str | None = "on_te1",
) -> SimpleNamespace:
    return SimpleNamespace(
        event=SimpleNamespace(
            operator=SimpleNamespace(open_id=open_id, union_id=union_id),
            action=SimpleNamespace(
                value=None,
                tag="input",
                option=None,
                name=name,
                input_value=input_value,
            ),
        )
    )


def response_card(response: object) -> dict[str, object]:
    return response.card.data


def card_text(card: dict[str, object]) -> str:
    return json.dumps(card, ensure_ascii=False)


def find_button_value(card: dict[str, object], label: str) -> dict[str, object]:
    for element in card["elements"]:
        if not isinstance(element, dict) or element.get("tag") != "action":
            continue
        for action in element.get("actions", []):
            text = action.get("text", {})
            if text.get("content") == label:
                return action["value"]
    raise AssertionError(f"button not found: {label}")


def test_feishu_admin_confirms_pipeline_trigger_once(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    bind_feishu_identity(
        db_session,
        actor=admin,
        payload=FeishuIdentityBind(open_id="ou_admin", union_id="on_admin"),
    )
    config = PipelineConfig(
        name="openEuler update",
        versions=["24.03-LTS-SP4"],
        archs=["aarch64"],
        image_round="round-1",
        config_data={"module_template_ids": []},
    )
    db_session.add(config)
    db_session.commit()
    queued: list[str] = []
    monkeypatch.setattr(
        "app.modules.feishu.card_actions.enqueue_run_jobs",
        lambda _db, jobs, _actor_id: queued.extend(job.id for job in jobs),
    )
    handler = FeishuBotHandler(SimpleNamespace(), session_factory=lambda: nullcontext(db_session))

    form_card = response_card(
        handler.handle_card_action_event(
            card_action_event(
                "pipeline_trigger_form",
                open_id="ou_admin",
                union_id="on_admin",
                config_id=config.id,
            )
        )
    )
    assert "openEuler update" in card_text(form_card)

    response_card(
        handler.handle_card_action_event(
            card_select_event(
                "24.03-LTS-SP4",
                name=f"pipeline_version|{config.id}",
                open_id="ou_admin",
                union_id="on_admin",
            )
        )
    )
    response_card(
        handler.handle_card_action_event(
            card_select_event(
                "aarch64",
                name=f"pipeline_arch|{config.id}",
                open_id="ou_admin",
                union_id="on_admin",
            )
        )
    )
    response_card(
        handler.handle_card_action_event(
            card_input_event(
                f"pipeline_image_round|{config.id}",
                "round-2",
                open_id="ou_admin",
                union_id="on_admin",
            )
        )
    )

    confirm_card = response_card(
        handler.handle_card_action_event(
            card_action_event(
                "pipeline_trigger_confirm",
                open_id="ou_admin",
                union_id="on_admin",
                config_id=config.id,
            )
        )
    )
    submit = find_button_value(confirm_card, "确认执行")
    submit_event = card_action_event(
        str(submit.pop("action")),
        open_id="ou_admin",
        union_id="on_admin",
        context=CardActionContext(event_id="evt-pipeline-trigger"),
        **submit,
    )
    result_card = response_card(handler.handle_card_action_event(submit_event))
    replayed_card = response_card(handler.handle_card_action_event(submit_event))

    executions = db_session.execute(select(PipelineExecution)).scalars().all()
    assert len(executions) == 1
    assert executions[0].versions == ["24.03-LTS-SP4"]
    assert executions[0].archs == ["aarch64"]
    assert executions[0].image_round == "round-2"
    assert "已启动" in card_text(result_card)
    assert replayed_card == result_card
    assert queued == []


def test_feishu_non_admin_cannot_open_pipeline_trigger_form(db_session: Session) -> None:
    user = add_user(db_session, username="te1", role=UserRole.TE)
    bind_feishu_identity(
        db_session,
        actor=user,
        payload=FeishuIdentityBind(open_id="ou_te1", union_id="on_te1"),
    )
    config = PipelineConfig(
        name="weekly",
        versions=["24.03-LTS-SP4"],
        archs=["x86_64"],
        config_data={"module_template_ids": []},
    )
    db_session.add(config)
    db_session.commit()
    handler = FeishuBotHandler(SimpleNamespace(), session_factory=lambda: nullcontext(db_session))

    denied = response_card(
        handler.handle_card_action_event(
            card_action_event("pipeline_trigger_form", config_id=config.id)
        )
    )

    assert "管理员" in card_text(denied)
    assert db_session.execute(select(PipelineExecution)).scalars().all() == []


def test_feishu_pipeline_running_card_lists_only_active_executions(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = add_user(db_session, username="terunning", role=UserRole.TE)
    bind_feishu_identity(
        db_session,
        actor=user,
        payload=FeishuIdentityBind(open_id="ou_running", union_id="on_running"),
    )
    running = SimpleNamespace(
        id="execution-running",
        config_id="config-1",
        versions=["24.03-LTS-SP4"],
        archs=["aarch64"],
        triggered_by="admin",
        triggered_at=datetime.now(UTC),
    )
    succeeded = SimpleNamespace(
        id="execution-done",
        config_id="config-2",
        versions=["22.03-LTS-SP4"],
        archs=["x86_64"],
        triggered_by="admin",
        triggered_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "app.modules.feishu.card_actions.list_pipeline_executions",
        lambda _db, limit=None: [running, succeeded],
    )
    monkeypatch.setattr(
        "app.modules.feishu.card_actions.compute_execution_status",
        lambda _db, execution: (
            "running" if execution.id == "execution-running" else "succeeded"
        ),
    )
    monkeypatch.setattr(
        "app.modules.feishu.card_actions.execution_config_name",
        lambda _db, execution: f"pipeline-{execution.config_id}",
    )
    handler = FeishuBotHandler(SimpleNamespace(), session_factory=lambda: nullcontext(db_session))

    running_card = response_card(
        handler.handle_card_action_event(
            card_action_event(
                "pipeline_executions_running",
                open_id="ou_running",
                union_id="on_running",
            )
        )
    )

    content = card_text(running_card)
    assert "execution-running" in content
    assert "execution-done" not in content
    detail = find_button_value(running_card, "查看详情")
    assert detail["action"] == "pipeline_execution_detail"
    assert detail["execution_id"] == "execution-running"


def test_feishu_datetime_display_uses_display_timezone() -> None:
    value = datetime(2026, 7, 13, 7, 49, 30, tzinfo=UTC)

    assert datetime_display(value) == "2026-07-13 15:49"


def lease_payload() -> LeaseCreate:
    return LeaseCreate(
        purpose="调试",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
    )


def test_admin_can_upsert_feishu_app_config_without_secret_in_response(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="admin", role=UserRole.ADMIN)
    token = login(client, "admin")

    response = client.put(
        "/api/v1/integrations/feishu/app",
        json={
            "app_id": "cli_aabbcc",
            "app_secret": "secret-value",
            "is_enabled": True,
        },
        headers=auth_header(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["environment"] == "development"
    assert body["app_id"] == "cli_aabbcc"
    assert body["is_enabled"] is True
    assert body["has_app_secret"] is True
    assert "app_secret" not in body

    stored = db_session.execute(select(FeishuAppConfig)).scalar_one()
    assert stored.app_secret == "secret-value"

    logs = (
        db_session.execute(
            select(AuditLog).where(AuditLog.action == "feishu_app_config.upsert")
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].action == "feishu_app_config.upsert"
    assert "secret-value" not in str(logs[0].detail)

    read_response = client.get(
        "/api/v1/integrations/feishu/app",
        headers=auth_header(token),
    )

    assert read_response.status_code == 200
    assert read_response.json() == body


def test_non_admin_cannot_manage_feishu_app_config(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    token = login(client, "te1")

    get_response = client.get(
        "/api/v1/integrations/feishu/app",
        headers=auth_header(token),
    )
    put_response = client.put(
        "/api/v1/integrations/feishu/app",
        json={"app_id": "cli_aabbcc", "app_secret": "secret-value"},
        headers=auth_header(token),
    )

    assert get_response.status_code == 403
    assert put_response.status_code == 403


def test_feishu_identity_binding_prefers_union_id_and_rejects_conflicts(
    db_session: Session,
) -> None:
    alice = add_user(db_session, username="alice", role=UserRole.TE)
    bob = add_user(db_session, username="bob", role=UserRole.TSE)

    identity = bind_feishu_identity(
        db_session,
        actor=alice,
        payload=FeishuIdentityBind(open_id="ou_alice_app", union_id="on_alice"),
    )
    db_session.commit()

    assert identity.open_id == "ou_alice_app"
    assert identity.union_id == "on_alice"
    assert get_bound_user_for_feishu_actor(
        db_session,
        open_id="different_open_id",
        union_id="on_alice",
    ).id == alice.id
    assert get_bound_user_for_feishu_actor(
        db_session,
        open_id="ou_alice_app",
        union_id=None,
    ).id == alice.id

    with pytest.raises(FeishuIdentityConflictError):
        bind_feishu_identity(
            db_session,
            actor=bob,
            payload=FeishuIdentityBind(open_id="ou_bob_app", union_id="on_alice"),
        )


def test_current_user_can_read_own_feishu_identity(
    client: TestClient,
    db_session: Session,
) -> None:
    user = add_user(db_session, username="te1", role=UserRole.TE)
    bind_feishu_identity(
        db_session,
        actor=user,
        payload=FeishuIdentityBind(open_id="ou_te1", union_id=None),
    )
    db_session.commit()
    token = login(client, "te1")

    response = client.get(
        "/api/v1/integrations/feishu/me/identity",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user.id
    assert body["provider"] == "feishu"
    assert body["open_id"] == "ou_te1"
    assert body["union_id"] is None

    stored = db_session.execute(select(UserIdentity)).scalar_one()
    assert stored.id == body["id"]


def test_current_user_can_create_feishu_bind_url(
    client: TestClient,
    db_session: Session,
) -> None:
    user = add_user(db_session, username="te1", role=UserRole.TE)
    add_feishu_config(db_session)
    token = login(client, "te1")
    redirect_uri = "http://testserver:8080/api/v1/integrations/feishu/oauth/callback"

    response = client.get(
        "/api/v1/integrations/feishu/me/bind-url",
        params={"redirect_uri": redirect_uri},
        headers={**auth_header(token), "host": "testserver:8080"},
    )

    assert response.status_code == 200
    authorize_url = response.json()["authorize_url"]
    parsed = urlparse(authorize_url)
    query = parse_qs(parsed.query)
    assert parsed.geturl().startswith(
        "https://accounts.feishu.cn/open-apis/authen/v1/authorize?"
    )
    assert query["client_id"] == ["cli_test"]
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == [redirect_uri]
    state_user_id, state_redirect_uri = decode_oauth_state(query["state"][0])
    assert state_user_id == user.id
    assert state_redirect_uri == redirect_uri


def test_feishu_bind_url_rejects_unexpected_redirect_uri(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    add_feishu_config(db_session)
    token = login(client, "te1")

    response = client.get(
        "/api/v1/integrations/feishu/me/bind-url",
        params={"redirect_uri": "http://testserver/wrong"},
        headers=auth_header(token),
    )

    assert response.status_code == 400

    external_host = client.get(
        "/api/v1/integrations/feishu/me/bind-url",
        params={
            "redirect_uri": (
                "https://example.test/api/v1/integrations/feishu/oauth/callback"
            )
        },
        headers=auth_header(token),
    )

    assert external_host.status_code == 400


def test_feishu_oauth_callback_binds_current_user_identity(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = add_user(db_session, username="te1", role=UserRole.TE)
    add_feishu_config(db_session)
    redirect_uri = "http://testserver/api/v1/integrations/feishu/oauth/callback"
    state = create_oauth_state(user_id=user.id, redirect_uri=redirect_uri)

    def fake_fetch_feishu_identity(
        *,
        config: FeishuAppConfig,
        code: str,
        redirect_uri: str,
    ) -> FeishuIdentityBind:
        assert config.app_id == "cli_test"
        assert code == "oauth-code"
        assert redirect_uri == "http://testserver/api/v1/integrations/feishu/oauth/callback"
        return FeishuIdentityBind(open_id="ou_te1", union_id="on_te1")

    monkeypatch.setattr(
        "app.modules.feishu.router.feishu_oauth.fetch_feishu_identity",
        fake_fetch_feishu_identity,
    )

    response = client.get(
        "/api/v1/integrations/feishu/oauth/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "http://testserver/#/account?feishu_bind=success"
    stored = db_session.execute(select(UserIdentity)).scalar_one()
    assert stored.user_id == user.id
    assert stored.open_id == "ou_te1"
    assert stored.union_id == "on_te1"


def test_feishu_help_command_is_explicit_only() -> None:
    assert parse_private_text_command("help") == FeishuBotAction.SHOW_HOME
    assert parse_private_text_command(" 帮助 ") == FeishuBotAction.SHOW_HOME
    assert parse_private_text_command("物理机") == FeishuBotAction.IGNORE
    assert parse_private_text_command("unknown") == FeishuBotAction.IGNORE


def test_feishu_text_content_is_parsed_from_event_json() -> None:
    assert extract_text_content(json.dumps({"text": " help "})) == " help "
    assert extract_text_content("{bad-json") == ""
    assert extract_text_content(json.dumps({"post": "help"})) == ""


def test_feishu_sdk_event_is_mapped_to_internal_message() -> None:
    event = SimpleNamespace(
        event=SimpleNamespace(
            sender=SimpleNamespace(
                sender_id=SimpleNamespace(open_id="ou_user", union_id="on_user")
            ),
            message=SimpleNamespace(
                message_id="om_message_1",
                chat_id="oc_chat",
                chat_type="p2p",
                message_type="text",
                content=json.dumps({"text": "help"}),
            ),
        )
    )

    message = parse_sdk_event(event)

    assert message == FeishuIncomingMessage(
        chat_id="oc_chat",
        chat_type="p2p",
        message_type="text",
        text="help",
        open_id="ou_user",
        union_id="on_user",
        message_id="om_message_1",
    )


def test_feishu_sdk_duplicate_message_is_answered_once(db_session: Session) -> None:
    class FakeSender:
        def __init__(self) -> None:
            self.chat_ids: list[str] = []

        def send_home_card(self, chat_id: str) -> None:
            self.chat_ids.append(chat_id)

    event = SimpleNamespace(
        event=SimpleNamespace(
            sender=SimpleNamespace(
                sender_id=SimpleNamespace(open_id="ou_user", union_id="on_user")
            ),
            message=SimpleNamespace(
                message_id="om_duplicate",
                chat_id="oc_chat",
                chat_type="p2p",
                message_type="text",
                content=json.dumps({"text": "help"}),
            ),
        )
    )
    sender = FakeSender()
    handler = FeishuBotHandler(sender, session_factory=lambda: nullcontext(db_session))

    handler.handle_sdk_event(event)
    handler.handle_sdk_event(event)

    assert sender.chat_ids == ["oc_chat"]


def test_feishu_card_action_event_is_mapped_to_internal_action() -> None:
    action = parse_card_action_event(
        card_action_event(
            "physical_all",
            page=2,
            context=CardActionContext(
                header_event_id="evt-header",
                action_form_value={"remote_command|resource-1": "lscpu"},
            ),
        )
    )

    assert action is not None
    assert action.action == "physical_all"
    assert action.value["page"] == 2
    assert action.value["form_value"] == {"remote_command|resource-1": "lscpu"}
    assert action.open_id == "ou_te1"
    assert action.union_id == "on_te1"
    assert action.event_id == "evt-header"


def test_feishu_card_action_event_reads_top_level_event_id() -> None:
    action = parse_card_action_event(card_action_event("physical_all", context=CardActionContext(event_id="evt-top")))

    assert action is not None
    assert action.event_id == "evt-top"


def test_feishu_card_form_events_are_mapped_to_vm_create_update() -> None:
    select_action = parse_card_action_event(card_select_event("arch|aarch64"))
    input_action = parse_card_action_event(card_input_event("vcpu_count", "4"))
    command_action = parse_card_action_event(
        card_input_event("remote_command|resource-1", "uname -a")
    )

    assert select_action is not None
    assert select_action.action == "vm_create_form_update"
    assert select_action.value["tag"] == "select_static"
    assert select_action.value["option"] == "arch|aarch64"
    assert input_action is not None
    assert input_action.action == "vm_create_form_update"
    assert input_action.value["tag"] == "input"
    assert input_action.value["name"] == "vcpu_count"
    assert input_action.value["input_value"] == "4"
    assert command_action is not None
    assert command_action.action == "remote_command_form_update"
    assert command_action.value["name"] == "remote_command|resource-1"


def test_feishu_bot_handler_only_sends_home_card_for_private_help() -> None:
    class FakeSender:
        def __init__(self) -> None:
            self.chat_ids: list[str] = []

        def send_home_card(self, chat_id: str) -> None:
            self.chat_ids.append(chat_id)

    sender = FakeSender()
    handler = FeishuBotHandler(sender)

    handler.handle_message(
        FeishuIncomingMessage(
            chat_id="oc_help",
            chat_type="p2p",
            message_type="text",
            text="帮助",
            open_id="ou_user",
            union_id=None,
        )
    )
    handler.handle_message(
        FeishuIncomingMessage(
            chat_id="oc_group",
            chat_type="group",
            message_type="text",
            text="help",
            open_id="ou_user",
            union_id=None,
        )
    )
    handler.handle_message(
        FeishuIncomingMessage(
            chat_id="oc_image",
            chat_type="p2p",
            message_type="image",
            text="help",
            open_id="ou_user",
            union_id=None,
        )
    )
    handler.handle_message(
        FeishuIncomingMessage(
            chat_id="oc_other",
            chat_type="p2p",
            message_type="text",
            text="物理机",
            open_id="ou_user",
            union_id=None,
        )
    )

    assert sender.chat_ids == ["oc_help"]


def test_feishu_bound_user_natural_language_uses_assistant(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSender:
        def __init__(self) -> None:
            self.cards: list[dict[str, object]] = []

        @staticmethod
        def send_home_card(chat_id: str) -> None:
            raise AssertionError("home card should not be sent")

        def send_card(self, chat_id: str, card: dict[str, object]) -> None:
            assert chat_id == "oc_chat"
            self.cards.append(card)

    class FakeClient:
        @staticmethod
        def complete(messages: list[dict], tools: list[dict]) -> dict:
            assert messages[-1]["content"] == "查看我的资源"
            assert {tool["function"]["name"] for tool in tools} == {
                "search_resources",
                "list_my_resources",
                "list_pipeline_configs",
                "list_pipeline_executions",
                "get_pipeline_execution",
                "get_run_job_result",
                "get_failed_cases",
                "get_case_log_excerpt",
            }
            return {"role": "assistant", "content": "你当前没有占用资源。"}

    user = add_user(db_session, username="te1", role=UserRole.TE)
    bind_feishu_identity(
        db_session,
        actor=user,
        payload=FeishuIdentityBind(open_id="ou_te1", union_id="on_te1"),
    )
    db_session.commit()
    monkeypatch.setattr(
        "app.modules.feishu.bot_runtime.get_settings",
        lambda: SimpleNamespace(llm_assistant_enabled=True, llm_max_tool_rounds=3),
    )
    monkeypatch.setattr(
        "app.modules.feishu.bot_runtime.create_llm_client",
        lambda _settings: FakeClient(),
    )
    sender = FakeSender()
    handler = FeishuBotHandler(sender, session_factory=lambda: nullcontext(db_session))

    handler.handle_message(
        FeishuIncomingMessage(
            chat_id="oc_chat",
            chat_type="p2p",
            message_type="text",
            text="查看我的资源",
            open_id="ou_te1",
            union_id="on_te1",
        )
    )

    assert len(sender.cards) == 1
    assert "你当前没有占用资源" in card_text(sender.cards[0])


def test_feishu_card_action_returns_menu_card(db_session: Session) -> None:
    user = add_user(db_session, username="te1", role=UserRole.TE)
    bind_feishu_identity(
        db_session,
        actor=user,
        payload=FeishuIdentityBind(open_id="ou_te1", union_id="on_te1"),
    )
    db_session.commit()
    handler = FeishuBotHandler(SimpleNamespace(), session_factory=lambda: nullcontext(db_session))

    card = response_card(handler.handle_card_action_event(card_action_event("physical_menu")))

    assert card["header"]["title"]["content"] == "物理机管理"
    assert "我的物理机" in card_text(card)


