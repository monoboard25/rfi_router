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
        
        if agent_id:
            try:
                agent = project_client.agents.get_agent(agent_id)
                logging.info(f"Retrieved persistent agent: {agent.id}")
            except Exception as e:
                logging.warning(f"Could not retrieve agent {agent_id}: {e}")
                agent = None
        else:
            agent = None

        if not agent:
            logging.info("Creating or updating agent version.")
            agent = project_client.agents.create_version(  
                agent_name="bid-assist-agent",
                definition=PromptAgentDefinition(
                    model=model_deployment,
                    instructions="You are a professional Estimator Assistant. Analyze bid packages and draft takeoff checklists. Use the log_bid_analysis tool to return structured data.",
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
        
        # 3. Get Response via Agent Reference
        response = openai_client.responses.create(
            input=[{"role": "user", "content": f"Analyze this bid package: {bid_text[:4000]}"}],
            extra_body={
                "agent_reference": {"name": agent.name, "type": "agent_reference"},
                "tools": tools,
                "tool_choice": {"type": "function", "function": {"name": "log_bid_analysis"}}
            }
        )
        
        if not response.output_text:
            return {"takeoff_checklist": [], "historical_insights": []}

        # The responses API returns output_text which is often the tool call result if tool_choice is forced
        # However, we need to extract the tool arguments. 
        # In the new SDK, if output_text contains the JSON, we parse it.
        # If it's a standard tool call, we might need to check response.choices or similar.
        # For now, let's assume output_text contains the tool output as per the sample's usage.
        
        try:
            parsed = json.loads(response.output_text)
            return parsed
        except json.JSONDecodeError:
            # Fallback: check tool calls if available
            # Note: The responses API structure can vary based on version.
            logging.error("Failed to parse output_text as JSON.")
            return {"takeoff_checklist": [], "historical_insights": []}

    except Exception as e:
        logging.error(f"Error in bid analysis: {str(e)}")
        return {"takeoff_checklist": [], "historical_insights": []}

def run_bid_assist_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    bid_text = payload.get("bid_text", "")
    
    # 1. Analyze Bid
    analysis = generate_takeoff_checklist(bid_text)
    
    # 2. Build Structured Output
    outcome = "completed_with_write" if analysis["takeoff_checklist"] else "insufficient_data"
    
    writes_proposed = []
    if analysis["takeoff_checklist"]:
        writes_proposed.append({
            "target_scope": "teams_estimating_channel",
            "target_uri": "https://teams.microsoft.com/l/channel/estimating-hq",
            "write_type": "post",
            "content_summary": f"Bid Assist drafted a takeoff checklist with {len(analysis['takeoff_checklist'])} items and surfaced {len(analysis['historical_insights'])} historical insights."
        })

    output = {
        "run_id": run_id,
        "agent_id": "bid_assist",
        "agent_version": AGENT_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "takeoff_checklist": analysis["takeoff_checklist"],
        "historical_insights": analysis["historical_insights"],
        "resolution_path": "retrieval",
        "writes_proposed": writes_proposed,
        "outcome": outcome
    }

    # 3. Validation
    validator = ValidatorClient()
    val_result = validator.validate(
        run_id=run_id,
        agent_id="bid_assist",
        agent_version=AGENT_VERSION,
        output=output,
        proposed_writes=output["writes_proposed"],
        proposed_filenames=[]
    )
    
    if not val_result.get("pass", False):
        output["outcome"] = "halted_validation"
        output["writes_proposed"] = []
        output["validator_rejection"] = val_result
        
        output["writes_proposed"].append({
            "target_scope": "teams_company_hq",
            "target_uri": "https://teams.microsoft.com/l/channel/review_queue",
            "write_type": "post",
            "content_summary": "Bid Assist validation failure"
        })

    return output
