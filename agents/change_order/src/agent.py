import os
import re
import uuid
from datetime import datetime, timezone
import json
from openai import AzureOpenAI
from typing import Dict, Any

from .validator_client import ValidatorClient

AGENT_VERSION = "1.0.0"
CONSTITUTION_VERSION = "1.2"

def parse_filename(filename: str) -> Dict[str, Any]:
    # Project files: ^\d{4}-(CO)-[A-Za-z0-9]+(?:-\d{8})?-v\d+$
    pattern = r"^(\d{4})-(CO)-([A-Za-z0-9]+)(?:-\d{8})?-v(\d+)(\.[A-Za-z0-9]+)?$"
    match = re.match(pattern, filename)
    if match:
        return {
            "filename_conforms": True,
            "job_number": match.group(1),
            "type_code": match.group(2),
            "description_slug": match.group(3),
            "version": int(match.group(4))
        }
    return {
        "filename_conforms": False
    }

def extract_financials_with_llm(text_content: str) -> Dict[str, Any]:
    # Uses Azure OpenAI to infer financial amounts
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    if not all([endpoint, key, deployment]):
        return {
            "amount": 0.0,
            "schedule_impact_days": 0,
            "reason_code": "null"
        }
        
    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version="2024-02-01"
        )
        
        # We simulate the structured outputs function calling behavior
        tools = [{
            "type": "function",
            "function": {
                "name": "extract_co_financials",
                "description": "Extract financial data from a Change Order document",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "description": "The exact dollar amount requested. 0 if none."},
                        "schedule_impact_days": {"type": "integer", "description": "Days added to schedule."},
                        "reason_code": {"type": "string", "enum": ["client_request", "design_error", "unforeseen_condition", "allowance_reconciliation", "null"]}
                    },
                    "required": ["amount", "schedule_impact_days", "reason_code"]
                }
            }
        }]
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a specialized agent extracting financial data from Change Orders."},
                {"role": "user", "content": text_content[:4000]}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_co_financials"}},
            temperature=0.0
        )
        
        args = response.choices[0].message.tool_calls[0].function.arguments
        parsed = json.loads(args)
        return {
            "amount": float(parsed.get("amount", 0.0)),
            "schedule_impact_days": int(parsed.get("schedule_impact_days", 0)),
            "reason_code": parsed.get("reason_code", "null")
        }
    except Exception as e:
        return {
            "amount": 0.0,
            "schedule_impact_days": 0,
            "reason_code": "null"
        }

def run_change_order_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    received_at = datetime.now(timezone.utc).isoformat()
    
    filename = payload.get("filename", "")
    file_content = payload.get("file_content", "")
    source_uri = payload.get("source_uri", "https://tenant.sharepoint.com/sites/project-0000/co.pdf")
    payload_hash = payload.get("payload_hash", "sha256:0000000000000000000000000000000000000000000000000000000000000000")
    
    parsed = parse_filename(filename)
    
    if not parsed["filename_conforms"]:
        outcome = "halted_triage"
        financials = {"amount": 0.0, "schedule_impact_days": 0, "reason_code": "null"}
        resolution_path_attempts = [{"step": "schema_parse", "outcome": "fail", "failure_reason": "invalid filename"}]
        classification_method = "schema_parse"
    else:
        financials = extract_financials_with_llm(file_content)
        resolution_path_attempts = [
            {"step": "schema_parse", "outcome": "success"},
            {"step": "inference", "outcome": "success"}
        ]
        classification_method = "inference"

    contract_value = payload.get("contract_value", 100000.0) 

    assigned_to_role = "@PM"
    routing_basis = "Default routing for CO to PM."
    outcome = "routed"

    output = {
        "run_id": run_id,
        "agent_id": "change_order",
        "agent_version": AGENT_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "change_order": {
            "filename": filename,
            "filename_conforms": parsed["filename_conforms"],
            "job_number": parsed.get("job_number", "0000"),
            "co_number": "CO-001",
            "type_code": "CO",
            "description_slug": parsed.get("description_slug", "Unknown"),
            "version": parsed.get("version", 1),
            "source_uri": source_uri,
            "received_at": received_at,
            "payload_hash": payload_hash
        },
        "financials": {
            "amount": financials["amount"],
            "contract_value": contract_value,
            "schedule_impact_days": financials["schedule_impact_days"],
            "reason_code": financials["reason_code"]
        },
        "routing": {
            "assigned_to_role": assigned_to_role,
            "target_channel_uri": "https://teams.microsoft.com/l/channel/finance",
            "target_scope": "teams_finance_channel",
            "routing_basis": routing_basis,
            "escalation_triggered": False
        },
        "resolution_path": classification_method,
        "resolution_path_attempts": resolution_path_attempts,
        "sources_cited": [
            {"type": "sp_file", "uri": source_uri}
        ],
        "writes_proposed": [
            {
                "target_scope": "teams_finance_channel",
                "target_uri": "https://teams.microsoft.com/l/channel/finance",
                "write_type": "post",
                "content_summary": f"Posting new Change Order for ${financials['amount']}"
            }
        ],
        "escalations_fired": [],
        "outcome": outcome
    }
    
    validator = ValidatorClient()
    val_result = validator.validate(
        run_id=run_id,
        agent_id="change_order",
        agent_version=AGENT_VERSION,
        output=output,
        proposed_writes=output["writes_proposed"],
        proposed_filenames=[]
    )
    
    if not val_result.get("pass", False):
        if val_result.get("first_failure") == "escalation":
            output["outcome"] = "escalated_amount_threshold"
        else:
            output["outcome"] = "halted_validation"
            
        output["writes_proposed"] = []
        output["validator_rejection"] = val_result
        
        output["writes_proposed"].append({
            "target_scope": "teams_company_hq",
            "target_uri": "https://teams.microsoft.com/l/channel/review_queue",
            "write_type": "post",
            "content_summary": f"Validator rejection / Escalation alert for Change Order: ${financials['amount']}"
        })

    return output
