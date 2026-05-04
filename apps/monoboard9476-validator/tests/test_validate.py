import json
from unittest.mock import patch

import azure.functions as func

from function_app import validate


def _req(body: dict) -> func.HttpRequest:
    return func.HttpRequest(
        method="POST",
        url="/api/validate",
        body=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )


@patch("function_app._table_client")
def test_allow(mock_tc):
    resp = validate.build().get_user_function()(_req({"agent": "x", "action": "y"}))
    assert resp.status_code == 200
    assert json.loads(resp.get_body())["decision"] == "allow"


@patch("function_app._table_client")
def test_deny_destructive(mock_tc):
    resp = validate.build().get_user_function()(_req({"agent": "x", "action": "y", "destructive": True}))
    body = json.loads(resp.get_body())
    assert body["decision"] == "deny"
    assert "destructive action requires approval" in body["reasons"]


@patch("function_app._table_client")
def test_dry_run(mock_tc):
    resp = validate.build().get_user_function()(_req({"agent": "x", "action": "y", "dry_run": True}))
    assert json.loads(resp.get_body())["decision"] == "dry_run"


def test_missing_fields():
    resp = validate.build().get_user_function()(_req({}))
    assert resp.status_code == 400
