import pytest
from unittest.mock import patch, MagicMock
from src.agent import run_bid_assist_agent

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.generate_takeoff_checklist')
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

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.generate_takeoff_checklist')
def test_run_bid_assist_empty(mock_analyze, mock_validator):
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_analyze.return_value = {"takeoff_checklist": [], "historical_insights": []}
    
    payload = {
        "bid_text": ""
    }
    
    result = run_bid_assist_agent(payload)
    
    assert result["outcome"] == "insufficient_data"
    assert len(result["writes_proposed"]) == 0

@patch('src.agent.ValidatorClient.validate')
@patch('src.agent.AIProjectClient')
@patch('src.agent.DefaultAzureCredential')
def test_generate_takeoff_checklist_success(mock_cred, mock_client_class, mock_validator):
    # Setup mocks
    mock_validator.return_value = {"pass": True, "results": {}}
    mock_project_client = MagicMock()
    mock_client_class.return_value = mock_project_client
    
    mock_agent = MagicMock()
    mock_agent.name = "test-agent"
    mock_project_client.agents.create_version.return_value = mock_agent
    
    mock_openai_client = MagicMock()
    mock_project_client.get_openai_client.return_value = mock_openai_client
    
    mock_response = MagicMock()
    mock_response.output_text = '{"takeoff_checklist": [{"item_name": "Test Item", "category": "Test", "estimated_quantity": 10.0}], "historical_insights": []}'
    mock_openai_client.responses.create.return_value = mock_response
    
    with patch.dict('os.environ', {
        'AZURE_AI_PROJECT_ENDPOINT': 'https://test.endpoint',
        'AZURE_OPENAI_DEPLOYMENT': 'test-deployment'
    }):
        result = run_bid_assist_agent({"bid_text": "Test bid content"})
        
    assert result["takeoff_checklist"][0]["item_name"] == "Test Item"
    assert result["outcome"] == "completed_with_write"
