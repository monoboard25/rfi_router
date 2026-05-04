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

def detect_safety_hazards(photos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    if not all([endpoint, key, deployment]):
        return []
        
    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version="2024-02-01"
        )
        
        # In a real scenario, we would use Multi-Modal capabilities (GPT-4o) 
        # to analyze the actual image URIs. For this scaffold, we analyze 
        # the provided text descriptions/metadata of the photos.
        prompt = (
            "Analyze these field photo descriptions and visual features for potential safety hazards. "
            "Categorize findings based on the OSHA 'Fatal Four' and other standards: "
            "FALL_PROTECTION, STRUCK_BY, CAUGHT_IN_BETWEEN, ELECTROCUTION, or PPE_VIOLATION. "
            "Assign severity as 'critical' for IDLH (Immediate Danger to Life or Health) conditions, "
            "'high' for serious violations, and 'info' for good practices: "
            f"{json.dumps(photos)}"
        )
        
        # Tools/Function calling for structured output
        tools = [{
            "type": "function",
            "function": {
                "name": "log_safety_signals",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "signals": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "signal_type": {
                                        "type": "string", 
                                        "enum": ["FALL_PROTECTION", "STRUCK_BY", "CAUGHT_IN_BETWEEN", "ELECTROCUTION", "PPE_VIOLATION", "GOOD_PRACTICE"]
                                    },
                                    "observation": {"type": "string"},
                                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical", "info"]},
                                    "source_evidence_uri": {"type": "string"}
                                },
                                "required": ["signal_type", "observation", "severity", "source_evidence_uri"]
                            }
                        }
                    },
                    "required": ["signals"]
                }
            }
        }]
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a professional Safety Monitor agent scanning construction sites for hazards."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "log_safety_signals"}},
            temperature=0.0
        )
        
        args = response.choices[0].message.tool_calls[0].function.arguments
        parsed = json.loads(args)
        return parsed.get("signals", [])
    except Exception as e:
        logging.error(f"Error in safety hazard detection: {str(e)}")
        return []

def run_safety_monitor_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    job_number = payload.get("job_number", "0000")
    photos = payload.get("field_photos", [])
    
    # 1. Detect Hazards
    signals = detect_safety_hazards(photos)
    
    # 2. Build Structured Output
    outcome = "completed_with_write" if signals else "no_hazards_detected"
    
    writes_proposed = []
    if signals:
        writes_proposed.append({
            "target_scope": "teams_project_channel",
            "target_uri": f"https://teams.microsoft.com/l/channel/project-{job_number}-safety",
            "write_type": "post",
            "content_summary": f"Safety Monitor detected {len(signals)} potential safety signals in today's field photos."
        })

    output = {
        "run_id": run_id,
        "agent_id": "safety_monitor",
        "agent_version": AGENT_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "safety_signals": signals,
        "resolution_path": "inference",
        "writes_proposed": writes_proposed,
        "outcome": outcome
    }
    
    # 3. Validation
    validator = ValidatorClient()
    val_result = validator.validate(
        run_id=run_id,
        agent_id="safety_monitor",
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
            "content_summary": "Safety Monitor validation failure"
        })

    return output
