import pytest
from unittest.mock import patch, MagicMock
from src.agent import run_change_order_agent, parse_filename

def test_parse_filename_valid():
    res = parse_filename("2401-CO-PlumbingFix-v2.pdf")
    assert res["filename_conforms"] is True
    assert res["job_number"] == "2401"
    assert res["type_code"] == "CO"
    assert res["description_slug"] == "PlumbingFix"
    assert res["version"] == 2

def test_parse_filename_invalid():
    res = parse_filename("Change Order 2401.pdf")
    assert res["filename_conforms"] is False

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.extract_financials_with_llm')
def test_run_agent_under_threshold(mock_llm, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_llm.return_value = {"amount": 15000.0, "schedule_impact_days": 2, "reason_code": "unforeseen_condition"}
    
    payload = {
        "filename": "2401-CO-Fix-v1.pdf",
        "file_content": "Total amount requested is $15,000 for 2 extra days.",
        "contract_value": 100000.0
    }
    
    result = run_change_order_agent(payload)
    
    mock_llm.assert_called_once()
    assert result["financials"]["amount"] == 15000.0
    assert result["outcome"] == "routed"
    assert result["writes_proposed"][0]["target_scope"] == "teams_finance_channel"

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.extract_financials_with_llm')
def test_run_agent_over_threshold_escalation(mock_llm, mock_validator):
    # Simulate Escalation validator catching amount > 25000
    mock_validator.return_value = {"pass": False, "first_failure": "escalation", "results": {}}
    mock_llm.return_value = {"amount": 30000.0, "schedule_impact_days": 5, "reason_code": "design_error"}
    
    payload = {
        "filename": "2401-CO-HugeFix-v1.pdf",
        "file_content": "Total amount requested is $30,000 for 5 extra days.",
        "contract_value": 100000.0
    }
    
    result = run_change_order_agent(payload)
    
    assert result["financials"]["amount"] == 30000.0
    assert result["outcome"] == "escalated_amount_threshold"
    assert "validator_rejection" in result
    # Write proposed should be altered to post to review queue instead of executing operational write
    assert len(result["writes_proposed"]) == 1
    assert result["writes_proposed"][0]["target_scope"] == "teams_company_hq"
