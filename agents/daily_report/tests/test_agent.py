import pytest
from unittest.mock import patch, MagicMock
from src.agent import run_daily_report_agent

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.synthesize_daily_narrative')
def test_run_daily_report_success(mock_narrative, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_narrative.return_value = {
        "summary": "The electrical team finished the lobby wiring.",
        "roadblocks": "None."
    }
    
    payload = {
        "job_number": "2401",
        "report_date": "2026-05-03",
        "crew_hours": [
            {"trade": "electrical", "hours": 40.0, "count": 5}
        ],
        "field_photos": [
            {"uri": "https://tenant.sharepoint.com/photo1.jpg", "caption": "Lobby wiring complete."}
        ]
    }
    
    result = run_daily_report_agent(payload)
    
    assert result["report_metadata"]["job_number"] == "2401"
    assert result["report_metadata"]["report_date"] == "2026-05-03"
    assert result["outcome"] == "completed_with_write"
    
    # Verify naming convention in proposed write
    proposed_file = result["writes_proposed"][0]["proposed_filename"]
    assert proposed_file == "2401-RPT-DailyReport-20260503-v1.pdf"

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.synthesize_daily_narrative')
def test_run_daily_report_naming_failure(mock_narrative, mock_validator):
    # Simulate the naming validator failing (e.g. if we messed up the format)
    mock_validator.return_value = {"pass": False, "first_failure": "naming", "results": {}}
    mock_narrative.return_value = {"summary": "...", "roadblocks": "..."}
    
    payload = {
        "job_number": "2401",
        "report_date": "2026-05-03",
        "crew_hours": []
    }
    
    result = run_daily_report_agent(payload)
    
    assert result["outcome"] == "halted_validation"
    assert len(result["writes_proposed"]) == 1
    assert result["writes_proposed"][0]["target_scope"] == "teams_company_hq" # Escalated
