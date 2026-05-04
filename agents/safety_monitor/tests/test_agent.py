import pytest
from unittest.mock import patch, MagicMock
from src.agent import run_safety_monitor_agent

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.detect_safety_hazards')
def test_run_safety_monitor_success(mock_detect, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_detect.return_value = [
        {
            "signal_type": "FALL_PROTECTION",
            "observation": "Worker spotted on 3rd floor deck without lanyard attached.",
            "severity": "critical",
            "source_evidence_uri": "https://tenant.sharepoint.com/photo1.jpg"
        }
    ]
    
    payload = {
        "job_number": "2401",
        "field_photos": [
            {"uri": "https://tenant.sharepoint.com/photo1.jpg", "description": "Electricians working near elevator shaft."}
        ]
    }
    
    result = run_safety_monitor_agent(payload)
    
    assert result["outcome"] == "completed_with_write"
    assert len(result["safety_signals"]) == 1
    assert result["safety_signals"][0]["signal_type"] == "FALL_PROTECTION"
    assert result["writes_proposed"][0]["target_scope"] == "teams_project_channel"

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.detect_safety_hazards')
def test_run_safety_monitor_clean_site(mock_detect, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_detect.return_value = []
    
    payload = {
        "job_number": "2401",
        "field_photos": []
    }
    
    result = run_safety_monitor_agent(payload)
    
    assert result["outcome"] == "no_hazards_detected"
    assert len(result["writes_proposed"]) == 0
