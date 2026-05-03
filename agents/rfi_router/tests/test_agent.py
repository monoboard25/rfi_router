import pytest
from unittest.mock import patch
from src.agent import run_rfi_router_agent, parse_filename, get_trade_from_slug

def test_parse_filename_valid():
    res = parse_filename("2401-RFI-ElectricalLayout-v1.pdf")
    assert res["filename_conforms"] is True
    assert res["job_number"] == "2401"
    assert res["type_code"] == "RFI"
    assert res["description_slug"] == "ElectricalLayout"
    assert res["version"] == 1

def test_parse_filename_invalid():
    res = parse_filename("Electrical RFI.pdf")
    assert res["filename_conforms"] is False

def test_get_trade_from_slug():
    assert get_trade_from_slug("ElecRoom") == "electrical"
    assert get_trade_from_slug("MechDucts") == "mechanical"
    assert get_trade_from_slug("RandomStuff") is None

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.infer_trade_with_llm')
def test_run_agent_schema_parse_success(mock_llm, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    
    payload = {
        "filename": "2401-RFI-ElectricalLayout-v1.pdf",
        "file_content": "Some text",
        "source_uri": "https://tenant.sharepoint.com/file"
    }
    
    result = run_rfi_router_agent(payload)
    
    # LLM should not be called because "Electrical" is in the slug
    mock_llm.assert_not_called()
    
    assert result["classification"]["trade"] == "electrical"
    assert result["classification"]["classification_method"] == "schema_parse"
    assert result["routing"]["assigned_to_role"] == "@Estimator"
    assert result["outcome"] == "routed"

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.infer_trade_with_llm')
def test_run_agent_llm_fallback(mock_llm, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_llm.return_value = "structural"
    
    # "FloorPlan" doesn't map to a trade, so it will fall back to LLM
    payload = {
        "filename": "2401-RFI-FloorPlan-v1.pdf",
        "file_content": "Contains questions about load bearing walls.",
        "source_uri": "https://tenant.sharepoint.com/file"
    }
    
    result = run_rfi_router_agent(payload)
    
    mock_llm.assert_called_once()
    
    assert result["classification"]["trade"] == "structural"
    assert result["classification"]["classification_method"] == "inference"
    assert result["routing"]["assigned_to_role"] == "@Super"
    assert result["outcome"] == "routed"

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.infer_trade_with_llm')
def test_run_agent_validator_rejection(mock_llm, mock_validator):
    # Simulate the validator catching a threshold violation or missing schema field
    mock_validator.return_value = {"pass": False, "first_failure": "schema", "results": {}}
    
    payload = {
        "filename": "2401-RFI-ElectricalLayout-v1.pdf"
    }
    
    result = run_rfi_router_agent(payload)
    
    assert result["outcome"] == "halted_validation"
    assert "validator_rejection" in result
    # Write proposed should be altered to post to review queue instead of executing operational write
    assert len(result["writes_proposed"]) == 1
    assert result["writes_proposed"][0]["target_scope"] == "teams_company_hq"
