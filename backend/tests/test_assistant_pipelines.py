# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from types import SimpleNamespace

from app.modules.assistant.service import AssistantContext, AssistantResult, ToolResult
from app.modules.assistant.tools import pipelines as pipeline_tools
from app.modules.feishu.assistant_cards import build_assistant_result_card


def context() -> AssistantContext:
    return AssistantContext(
        user=SimpleNamespace(id="user-1", username="te1", role="TE"),
        channel="feishu",
    )


def test_list_pipeline_configs_returns_latest_computed_status(monkeypatch) -> None:
    config = SimpleNamespace(
        id="config-1",
        name="openEuler update",
        pipeline_type="update",
        versions=["24.03-LTS-SP4"],
        archs=["aarch64", "x86_64"],
        dist="openEuler",
        test_framework="mugen",
    )
    execution = SimpleNamespace(id="execution-1", triggered_at=None)
    monkeypatch.setattr(pipeline_tools, "list_pipeline_configs", lambda _db: [config])
    monkeypatch.setattr(
        pipeline_tools,
        "latest_execution_for_config",
        lambda _db, _config_id: execution,
    )
    monkeypatch.setattr(
        pipeline_tools,
        "compute_execution_status",
        lambda _db, _execution: "failed",
    )

    result = pipeline_tools.list_assistant_pipeline_configs(
        SimpleNamespace(), context(), {"name": "update", "limit": 5}
    )

    assert result == {
        "count": 1,
        "configs": [
            {
                "id": "config-1",
                "name": "openEuler update",
                "pipeline_type": "update",
                "versions": ["24.03-LTS-SP4"],
                "archs": ["aarch64", "x86_64"],
                "dist": "openEuler",
                "test_framework": "mugen",
                "latest_execution": {
                    "id": "execution-1",
                    "status": "failed",
                    "triggered_at": None,
                },
            }
        ],
    }


def test_get_failed_cases_returns_only_failure_statuses(monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline_tools,
        "get_run_job_detail",
        lambda _db, _run_job_id: {
            "id": "job-1",
            "status": "failed",
            "case_runs": [
                {
                    "id": "case-1",
                    "suite_name": "suite",
                    "case_name": "pass",
                    "status": "passed",
                },
                {
                    "id": "case-2",
                    "suite_name": "suite",
                    "case_name": "fail",
                    "status": "failed",
                    "stderr_summary": "boom",
                },
                {"id": "case-3", "suite_name": "suite", "case_name": "slow", "status": "timeout"},
            ],
        },
    )

    result = pipeline_tools.get_failed_cases(
        SimpleNamespace(), context(), {"run_job_id": "job-1"}
    )

    assert [case["id"] for case in result["cases"]] == ["case-2", "case-3"]
    assert result["cases"][0]["stderr_summary"] == "boom"


def test_get_case_log_excerpt_limits_content_and_keeps_error_context(monkeypatch) -> None:
    log = "\n".join(["normal line", "setup ok", "ERROR package install failed", "trace", "tail"])
    monkeypatch.setattr(
        pipeline_tools,
        "get_case_mugen_log",
        lambda _db, _run_job_id, _case_run_id: {
            "content": log,
            "file_path": "suite/case/mugen.log",
        },
    )

    result = pipeline_tools.get_case_log_excerpt(
        SimpleNamespace(),
        context(),
        {"run_job_id": "job-1", "case_run_id": "case-2", "max_chars": 200},
    )

    assert "ERROR package install failed" in result["excerpt"]
    assert len(result["excerpt"]) <= 200
    assert result["truncated"] is False


def test_pipeline_config_result_card_offers_trigger_form() -> None:
    card = build_assistant_result_card(
        AssistantResult(
            text="找到一条流水线。",
            tool_results=(
                ToolResult(
                    name="list_pipeline_configs",
                    data={
                        "configs": [
                            {
                                "id": "config-1",
                                "name": "openEuler update",
                                "pipeline_type": "update",
                                "versions": ["24.03-LTS-SP4"],
                                "archs": ["aarch64"],
                                "test_framework": "mugen",
                                "latest_execution": None,
                            }
                        ]
                    },
                ),
            ),
        )
    )

    actions = []
    for element in card["elements"]:
        if element.get("tag") != "action":
            continue
        actions.extend(element.get("actions", []))
    assert any(
        action.get("value", {}).get("action") == "pipeline_trigger_form"
        and action.get("value", {}).get("config_id") == "config-1"
        for action in actions
    )
