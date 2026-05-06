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
    output = {"amount": 30000, "contract_value": 100000}
    res = validator.validate("change_order", output)
    assert res["pass"] is False
    assert len(res["triggers_fired"]) > 0
    assert res["triggers_fired"][0]["trigger_id"] == "co_amount_threshold"
    assert res["triggers_fired"][0]["halts_write"] is True

@patch('graph_client.SharePointListFetcher.fetch_escalation_matrix', return_value=[])
def test_escalation_validator_pass(mock_fetch):
    validator = EscalationValidator()
    # Change order under thresholds
    output = {"amount": 10000, "contract_value": 500000, "is_new_scope": False, "current_spend": 10000, "budget_contingency": 50000, "source_artifact_age_days": 1, "freshness_threshold_days": 7}
    res = validator.validate("change_order", output)
    print("DEBUG:", res)
    assert res["pass"] is True

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
