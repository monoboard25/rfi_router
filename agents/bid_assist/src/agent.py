import os
import uuid
import json
import logging
from datetime import datetime, timezone
from openai import AzureOpenAI
from typing import Dict, Any, List

from .validator_client import ValidatorClient

AGENT_VERSION = "1.0.0"
CONSTITUTION_VERSION = "1.2"

def generate_takeoff_checklist(bid_text: str) -> Dict[str, Any]:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    if not all([endpoint, key, deployment]):
        return {"takeoff_checklist": [], "historical_insights": []}
        
    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version="2024-02-01"
        )
        
        prompt = f"Analyze this bid package and draft a takeoff checklist. Also highlight historical cost outliers based on the scope: {bid_text[:4000]}"
        
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
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a professional Estimator Assistant agent helping with bid takeoffs."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "log_bid_analysis"}},
            temperature=0.0
        )
        
        if not response.choices or not response.choices[0].message.tool_calls:
            return {"takeoff_checklist": [], "historical_insights": []}

        args = response.choices[0].message.tool_calls[0].function.arguments
        parsed = json.loads(args)
        return parsed
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
