import pytest
from unittest.mock import patch, MagicMock
from agent import run_bid_assist_agent

@patch('agent.ValidatorClient.validate')
@patch('agent.generate_takeoff_checklist')
def test_run_bid_assist_success(mock_analyze, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_analyze.return_value = {
        "takeoff_checklist": [
            {"item_name": "Concrete Foundation", "category": "Concrete", "estimated_quantity": 500.0, "unit": "CY"}
        ],
        "historical_insights": [
            {"observation": "Concrete prices spiked 10% in this region last quarter.", "impact_rating": "high"}
        ]
    }
    
    payload = {
        "bid_text": "Project includes a 500 CY concrete foundation."
    }
    
    result = run_bid_assist_agent(payload)
    
    assert result["outcome"] == "completed_with_write"
    assert len(result["takeoff_checklist"]) == 1
    assert result["takeoff_checklist"][0]["item_name"] == "Concrete Foundation"
    assert result["writes_proposed"][0]["target_scope"] == "teams_estimating_channel"

@patch('agent.ValidatorClient.validate')
@patch('agent.generate_takeoff_checklist')
def test_run_bid_assist_empty(mock_analyze, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_analyze.return_value = {"takeoff_checklist": [], "historical_insights": []}
    
    payload = {
        "bid_text": ""
    }
    
    result = run_bid_assist_agent(payload)
    
    assert result["outcome"] == "insufficient_data"
    assert len(result["writes_proposed"]) == 0
