import pytest
from unittest.mock import patch, MagicMock
from agent import run_onboarding_agent

@patch('agent.ValidatorClient.validate')
def test_run_onboarding_success(mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    
    payload = {
        "job_number": "2401",
        "site_id": "site-xyz"
    }
    
    result = run_onboarding_agent(payload)
    
    assert result["outcome"] == "completed_with_write"
    assert result["proposed_permission_matrix"]["job_number"] == "2401"
    assert "RFIs" in result["proposed_folders"]
    assert len(result["proposed_escalation_matrix"]["triggers"]) == 2
    assert result["proposed_escalation_matrix"]["triggers"][0]["trigger_id"] == "threshold_over_10k"
