import os
import uuid
import json
import logging
from datetime import datetime, timezone
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from typing import Dict, Any, List

from .validator_client import ValidatorClient

AGENT_VERSION = "1.0.0"
CONSTITUTION_VERSION = "1.2"

def generate_takeoff_checklist(bid_text: str) -> Dict[str, Any]:
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    if not all([project_endpoint, model_deployment]):
        logging.warning("Missing project endpoint or deployment name.")
        return {"takeoff_checklist": [], "historical_insights": []}
        
    try:
        project_client = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential(),
        )
        
        # 1. Fetch or Create Agent
        agent_id = os.getenv("AZURE_AI_AGENT_ID")
        agent = None
        
        if agent_id:
            try:
                agent = project_client.agents.get_agent(agent_id)
            except Exception:
                pass

        if not agent:
            agent = project_client.agents.create_version(  
                agent_name="bid-assist-agent",
                definition=PromptAgentDefinition(
                    model=model_deployment,
                    instructions="You are a professional Estimator Assistant. Analyze bid packages and draft takeoff checklists. Use the log_bid_analysis tool.",
                ),
            )
        
        openai_client = project_client.get_openai_client()
        
        # 2. Define Tools
        tools = [{
            "type": "function",
            "function": {
                "name": "log_bid_analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "takeoff_checklist": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_name": {"type": "string"},
                                    "category": {"type": "string"},
                                    "estimated_quantity": {"type": "number"},
                                    "unit": {"type": "string"}
                                },
                                "required": ["item_name", "category", "estimated_quantity"]
                            }
                        },
                        "historical_insights": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "observation": {"type": "string"},
                                    "impact_rating": {"type": "string", "enum": ["low", "medium", "high"]}
                                },
                                "required": ["observation", "impact_rating"]
                            }
                        }
                    },
                    "required": ["takeoff_checklist", "historical_insights"]
                }
            }
        }]
        
        # 3. Get Response
        prompt = f"Analyze this bid package: {bid_text[:4000]}"
        response = openai_client.responses.create(
            input=[{"role": "user", "content": prompt}],
            extra_body={
                "agent_reference": {"name": agent.name, "type": "agent_reference"},
                "tools": tools,
                "tool_choice": {"type": "function", "function": {"name": "log_bid_analysis"}}
            }
        )
        
        # Extraction logic for tool call results
        if response.output_text:
            try:
                return json.loads(response.output_text)
            except:
                pass
                
        return {"takeoff_checklist": [], "historical_insights": []}

    except Exception as e:
        logging.error(f"Error in bid analysis: {str(e)}")
        return {"takeoff_checklist": [], "historical_insights": []}

def run_bid_assist_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    bid_text = payload.get("bid_text", "")
    
    # 1. Analyze Bid
    analysis = generate_takeoff_checklist(bid_text)
    
    # 2. Build Result
    output = {
        "run_id": run_id,
        "agent_id": "bid_assist",
        "takeoff_checklist": analysis["takeoff_checklist"],
        "historical_insights": analysis["historical_insights"],
        "status": "success" if analysis["takeoff_checklist"] else "no_data"
    }

    # 3. Governance Validation
    validator = ValidatorClient()
    # We validate the analysis output against the constitution
    val_result = validator.validate(
        agent_name="Bid-Assist-Agent",
        prompt=f"Analyze bid: {bid_text[:500]}...",
        response_text=json.dumps(analysis)
    )
    
    if not val_result.get("isValid", False):
        logging.warning(f"Governance Rejection: {val_result.get('violations')}")
        return {
            "run_id": run_id,
            "status": "rejected",
            "reason": "Governance Violation",
            "feedback": val_result.get("feedback")
        }

    return output
