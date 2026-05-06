"""End-to-end orchestrator runs against real fixtures from schemas/fixtures/."""

import json
import os
import pytest
from unittest.mock import patch

from orchestrator import ValidatorOrchestrator

FIXTURES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "schemas", "fixtures")
)


def _load(filename: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, filename), "r") as f:
        return json.load(f)


def _writes(output: dict) -> list:
    return output.get("writes_proposed", [])


def _filenames(output: dict) -> list:
    return [w["proposed_filename"] for w in _writes(output) if w.get("proposed_filename")]


@patch("graph_client.SharePointListFetcher.fetch_permission_matrix", return_value=[])
@patch("graph_client.SharePointListFetcher.fetch_escalation_matrix", return_value=[])
def test_rfi_router_valid_fixture_passes_schema(mock_esc, mock_perm):
    output = _load("rfi_router.valid.sample.json")
    orch = ValidatorOrchestrator()
    res = orch.execute_chain(output["run_id"], "rfi_router", output, _writes(output), _filenames(output))
    assert res["results"]["schema"]["pass"] is True


@patch("graph_client.SharePointListFetcher.fetch_permission_matrix", return_value=[])
@patch("graph_client.SharePointListFetcher.fetch_escalation_matrix", return_value=[])
def test_change_order_invalid_fixture_fails_schema(mock_esc, mock_perm):
    output = _load("change_order.invalid.bad_co_number.json")
    orch = ValidatorOrchestrator()
    res = orch.execute_chain(output["run_id"], "change_order", output, _writes(output), _filenames(output))
    assert res["pass"] is False
    assert res["first_failure"] == "schema"


@patch("graph_client.SharePointListFetcher.fetch_permission_matrix", return_value=[])
@patch("graph_client.SharePointListFetcher.fetch_escalation_matrix", return_value=[])
def test_safety_monitor_invalid_severity_fails_schema(mock_esc, mock_perm):
    output = _load("safety_monitor.invalid.bad_severity.json")
    orch = ValidatorOrchestrator()
    res = orch.execute_chain(output["run_id"], "safety_monitor", output, _writes(output), _filenames(output))
    assert res["pass"] is False
    assert res["first_failure"] == "schema"


@patch("graph_client.SharePointListFetcher.fetch_permission_matrix", return_value=[])
@patch("graph_client.SharePointListFetcher.fetch_escalation_matrix", return_value=[])
def test_daily_report_valid_fixture_passes_schema(mock_esc, mock_perm):
    output = _load("daily_report.valid.sample.json")
    orch = ValidatorOrchestrator()
    res = orch.execute_chain(output["run_id"], "daily_report", output, _writes(output), _filenames(output))
    assert res["results"]["schema"]["pass"] is True
