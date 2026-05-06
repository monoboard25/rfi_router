import pytest
from unittest.mock import patch
from validators.schema_validator import SchemaValidator
from validators.scope_validator import ScopeValidator
from validators.naming_validator import NamingValidator
from validators.escalation_validator import EscalationValidator
from orchestrator import ValidatorOrchestrator

def test_naming_validator_project():
    validator = NamingValidator()
    # Correct filename
    res = validator.validate(["2401-RFI-ElectricalLayout-v1.pdf"])
    assert res["pass"] is True

    # Bad prefix
    res = validator.validate(["2401-FOO-ElectricalLayout-v1.pdf"])
    assert res["pass"] is False

def test_naming_validator_company():
    validator = NamingValidator()
    res = validator.validate(["HR-POL-LeavePolicy-2026.docx"])
    assert res["pass"] is True
    
    res = validator.validate(["FOO-POL-LeavePolicy-2026.docx"])
    assert res["pass"] is False
    
@patch('graph_client.SharePointListFetcher.fetch_permission_matrix', return_value=[])
def test_scope_validator(mock_fetch):
    validator = ScopeValidator()
    proposed = [{"target_uri": "teams://acme-corp/project-2401", "write_type": "post"}]
    res = validator.validate("rfi_router", proposed)
    assert res["pass"] is True

    proposed_bad = [{"target_uri": "https://acme.sharepoint.com/sites/Finance", "write_type": "post"}]
    res = validator.validate("rfi_router", proposed_bad)
    assert res["pass"] is False
    assert res["violations"][0]["access_granted"] == "None"


@patch('graph_client.SharePointListFetcher.fetch_permission_matrix', return_value=[])
def test_scope_validator_teams_deeplink_registry(mock_fetch):
    validator = ScopeValidator()
    deeplink = "https://teams.microsoft.com/l/channel/19%3Aproject-2401-electrical%40thread.tacv2"
    res = validator.validate("rfi_router", [{"target_uri": deeplink, "write_type": "post"}])
    assert res["pass"] is True

    unknown = "https://teams.microsoft.com/l/channel/19%3Aunknown-channel%40thread.tacv2"
    res = validator.validate("rfi_router", [{"target_uri": unknown, "write_type": "post"}])
    assert res["pass"] is False
    assert res["violations"][0]["reason"] == "URI does not match any known scope"

@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_escalation_validator(mock_fetch):
    validator = EscalationValidator()
    # Change order > 25000 should escalate
    output = {"financials": {"amount": 30000, "contract_value": 100000}}
    res = validator.validate("change_order", output)
    assert res["pass"] is False
    triggers = [t["trigger_id"] for t in res["triggers_fired"]]
    assert "co_amount_threshold" in triggers
    co_trigger = next(t for t in res["triggers_fired"] if t["trigger_id"] == "co_amount_threshold")
    assert co_trigger["halts_write"] is True

@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_escalation_validator_pass(mock_fetch):
    validator = EscalationValidator()
    # Change order under thresholds; sources fresh; no failed attempts
    output = {
        "financials": {"amount": 10000, "contract_value": 500000},
        "sources_cited": [{"freshness_ok": True}],
        "resolution_path_attempts": [{"outcome": "success"}],
    }
    res = validator.validate("change_order", output)
    assert res["pass"] is True


@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_escalation_general_stale_data_fires(mock_fetch):
    validator = EscalationValidator()
    output = {"sources_cited": [{"freshness_ok": True}, {"freshness_ok": False}]}
    res = validator.validate("rfi_router", output)
    assert res["pass"] is False
    assert any(t["trigger_id"] == "general_stale_data" for t in res["triggers_fired"])


@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_escalation_general_tool_failure_fires(mock_fetch):
    validator = EscalationValidator()
    output = {"resolution_path_attempts": [
        {"outcome": "fail"}, {"outcome": "fail"}, {"outcome": "success"}
    ]}
    res = validator.validate("rfi_router", output)
    assert res["pass"] is False
    assert any(t["trigger_id"] == "general_tool_failure" for t in res["triggers_fired"])


@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_escalation_daily_missing_photos_fires(mock_fetch):
    validator = EscalationValidator()
    output = {
        "crew_hours": [{"trade": "elec", "hours": 8, "count": 2}],
        "field_evidence": [],
    }
    res = validator.validate("daily_report", output)
    assert any(t["trigger_id"] == "daily_missing_photos" for t in res["triggers_fired"])


@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_escalation_daily_safety_keywords_fires(mock_fetch):
    validator = EscalationValidator()
    output = {"narrative": {"summary": "Worker fall from scaffold reported", "roadblocks": ""}}
    res = validator.validate("daily_report", output)
    assert any(t["trigger_id"] == "daily_safety_keywords" for t in res["triggers_fired"])


@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_escalation_helpers_direct(mock_fetch):
    v = EscalationValidator()
    assert v._sum_crew_hours([{"hours": 8}, {"hours": 4}]) == 12
    assert v._any_stale([{"freshness_ok": True}, {"freshness_ok": False}]) is True
    assert v._any_stale([{"freshness_ok": True}]) is False
    assert v._count_failed_attempts([{"outcome": "fail"}, {"outcome": "success"}]) == 1
    assert v._signals_match_keywords([{"observation": "Worker fall from scaffold"}], ["fall"]) is True
    assert v._signals_match_keywords([{"observation": "PPE missing"}], ["fall"]) is False
    assert v._any_severity([{"severity": "high"}], ["high", "critical"]) is True
    assert v._any_severity([{"severity": "low"}], ["high", "critical"]) is False

def test_schema_validator():
    validator = SchemaValidator()
    res = validator.validate("rfi_router", {})
    assert res["pass"] is False
    assert "errors" in res

@patch('graph_client.SharePointListFetcher.fetch_permission_matrix', return_value=[])
@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_orchestrator(mock_fetch_esc, mock_fetch_perm):
    orchestrator = ValidatorOrchestrator()
    res = orchestrator.execute_chain("run-123", "rfi_router", {}, [], [])
    assert res["pass"] is False
    assert res["first_failure"] == "schema"
