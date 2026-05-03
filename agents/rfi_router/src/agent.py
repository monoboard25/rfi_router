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
    # Project files: ^\d{4}-(DWG|RFI|SUB|CO|RPT|PHO|CON)-[A-Za-z0-9]+(?:-\d{8})?-v\d+$
    pattern = r"^(\d{4})-(RFI)-([A-Za-z0-9]+)(?:-\d{8})?-v(\d+)(\.[A-Za-z0-9]+)?$"
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

def get_trade_from_slug(slug: str) -> str:
    slug_lower = slug.lower()
    trade_map = {
        "elec": "electrical",
        "mech": "mechanical",
        "plumb": "plumbing",
        "struct": "structural",
        "civil": "civil",
        "arch": "architectural",
        "lowvolt": "low_voltage",
        "fire": "fire_protection"
    }
    for key, trade in trade_map.items():
        if key in slug_lower:
            return trade
    return None

def infer_trade_with_llm(text_content: str) -> str:
    # Uses Azure OpenAI to infer trade
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    if not all([endpoint, key, deployment]):
        return "unclassifiable"
        
    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version="2024-02-01"
        )
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a construction agent. Classify the trade of this RFI based on the content. Reply ONLY with one of: electrical, mechanical, plumbing, structural, civil, architectural, low_voltage, fire_protection, general_conditions. If unsure, reply unclassifiable."},
                {"role": "user", "content": text_content[:2000]} # Limit tokens
            ],
            temperature=0.0
        )
        trade = response.choices[0].message.content.strip().lower()
        valid_trades = ["electrical","mechanical","plumbing","structural","civil","architectural","low_voltage","fire_protection","general_conditions","unclassifiable"]
        if trade in valid_trades:
            return trade
        return "unclassifiable"
    except Exception as e:
        return "unclassifiable"

def run_rfi_router_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    received_at = datetime.now(timezone.utc).isoformat()
    
    # 1. Parse Schema
    filename = payload.get("filename", "")
    file_content = payload.get("file_content", "")
    source_uri = payload.get("source_uri", "https://tenant.sharepoint.com/sites/project-0000/rfi.pdf")
    payload_hash = payload.get("payload_hash", "sha256:0000000000000000000000000000000000000000000000000000000000000000")
    
    parsed = parse_filename(filename)
    
    resolution_path_attempts = []
    
    trade = None
    classification_method = None
    confidence_source = "none"
    trade_basis = None
    
    if not parsed["filename_conforms"]:
        # Triage needed
        outcome = "halted_triage"
        trade = "unclassifiable"
        classification_method = "unclassifiable"
    else:
        # Step 1: Schema Parse
        trade = get_trade_from_slug(parsed["description_slug"])
        if trade:
            classification_method = "schema_parse"
            confidence_source = "parse"
            trade_basis = f"description_slug contains trade keyword"
            resolution_path_attempts.append({"step": "schema_parse", "outcome": "success"})
        else:
            resolution_path_attempts.append({"step": "schema_parse", "outcome": "fail", "failure_reason": "slug did not match known trade keywords"})
            
            # Step 2: LLM Inference Fallback
            trade = infer_trade_with_llm(file_content)
            if trade and trade != "unclassifiable":
                classification_method = "inference"
                confidence_source = "model_logprob"
                trade_basis = "inference from document text"
                resolution_path_attempts.append({"step": "inference", "outcome": "success"})
            else:
                trade = "unclassifiable"
                classification_method = "unclassifiable"
                resolution_path_attempts.append({"step": "inference", "outcome": "fail", "failure_reason": "model returned unclassifiable"})

    # Deterministic Routing based on trade
    # Simulated Delegation Register mapping
    delegation_register = {
        "electrical": "@Estimator",
        "mechanical": "@PM",
        "structural": "@Super"
    }
    
    assigned_to_role = delegation_register.get(trade, "unroutable")
    routing_basis = f"trade={trade} -> {assigned_to_role} per Delegation Register" if assigned_to_role != "unroutable" else "no trade -> escalated to @PM"
    
    if assigned_to_role == "unroutable":
        outcome = "escalated_no_trade"
    else:
        outcome = "routed"

    # Construct the JSON output per rfi_router.schema.json
    output = {
        "run_id": run_id,
        "agent_id": "rfi_router",
        "agent_version": AGENT_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "rfi": {
            "filename": filename,
            "filename_conforms": parsed["filename_conforms"],
            "job_number": parsed.get("job_number", "0000"),
            "rfi_number": "RFI-0001",
            "type_code": "RFI",
            "description_slug": parsed.get("description_slug", "Unknown"),
            "version": parsed.get("version", 1),
            "source_uri": source_uri,
            "received_at": received_at,
            "payload_hash": payload_hash
        },
        "classification": {
            "trade": trade if trade != "unclassifiable" else None,
            "trade_basis": trade_basis,
            "classification_method": classification_method,
            "confidence_source": confidence_source,
            "priority": "medium",
            "priority_basis": "default assignment"
        },
        "routing": {
            "assigned_to_role": assigned_to_role,
            "target_channel_uri": "https://teams.microsoft.com/l/channel/...",
            "target_scope": "teams_project_channel",
            "routing_basis": routing_basis,
            "escalation_triggered": (assigned_to_role == "unroutable")
        },
        "tracking_row": {
            "list_uri": "https://tenant.sharepoint.com/sites/project/Lists/RFI",
            "row_key": f"{parsed.get('job_number', '0000')}-RFI-0001",
            "status": "open",
            "job_number": parsed.get("job_number", "0000"),
            "rfi_number": "RFI-0001",
            "trade": trade if trade != "unclassifiable" else None,
            "assigned_to_role": assigned_to_role,
            "received_at": received_at,
            "source_file_uri": source_uri,
            "sla_deadline": None
        },
        "resolution_path": classification_method if classification_method != "unclassifiable" else "schema_parse",
        "resolution_path_attempts": resolution_path_attempts or [{"step": "schema_parse", "outcome": "skipped"}],
        "sources_cited": [
            {"type": "sp_file", "uri": source_uri}
        ],
        "writes_proposed": [
            {
                "target_scope": "teams_project_channel",
                "target_uri": "https://teams.microsoft.com/l/channel/...",
                "write_type": "post",
                "content_summary": f"Routing RFI to {assigned_to_role}"
            }
        ],
        "escalations_fired": [],
        "outcome": outcome
    }
    
    # Call Validator Chain
    validator = ValidatorClient()
    val_result = validator.validate(
        run_id=run_id,
        agent_id="rfi_router",
        agent_version=AGENT_VERSION,
        output=output,
        proposed_writes=output["writes_proposed"],
        proposed_filenames=[] # RFI Router only writes Teams messages, no new files
    )
    
    # If validator fails, short-circuit and modify instructions to halt writes
    if not val_result.get("pass", False):
        output["outcome"] = "halted_validation"
        output["writes_proposed"] = [] # Drop operational writes
        output["validator_rejection"] = val_result
        
        output["writes_proposed"].append({
            "target_scope": "teams_company_hq",
            "target_uri": "https://teams.microsoft.com/l/channel/review_queue",
            "write_type": "post",
            "content_summary": "Validator rejection alert"
        })

    return output
