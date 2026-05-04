import os
import uuid
import json
from typing import Dict, Any, List
from src.validator_client import ValidatorClient

AGENT_VERSION = "1.0.0"

def run_onboarding_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    job_number = payload.get("job_number", "0000")
    site_id = payload.get("site_id", "monoboard-sp-site-id")
    
    # 1. Propose Folders
    proposed_folders = ["RFIs", "Submittals", "Photos", "Safety", "Reports"]
    
    # 2. Propose Permission Matrix
    proposed_permission_matrix = {
        "job_number": job_number,
        "site_id": site_id,
        "mappings": [
            {"trade_prefix": "ELEC", "target_folder_uri": f"https://tenant.sharepoint.com/sites/{job_number}/RFIs/Electrical"},
            {"trade_prefix": "PLUM", "target_folder_uri": f"https://tenant.sharepoint.com/sites/{job_number}/RFIs/Plumbing"},
            {"trade_prefix": "MECH", "target_folder_uri": f"https://tenant.sharepoint.com/sites/{job_number}/RFIs/Mechanical"}
        ]
    }
    
    # 3. Propose Escalation Matrix
    proposed_escalation_matrix = {
        "job_number": job_number,
        "triggers": [
            {
                "trigger_id": "threshold_over_10k",
                "condition": "cost_impact > 10000",
                "destination": "pm_approval_queue",
                "halts_write": True
            },
            {
                "trigger_id": "safety_idlh",
                "condition": "severity == 'critical'",
                "destination": "safety_hq_alert",
                "halts_write": False
            }
        ]
    }
    
    # 4. Writes Proposed
    writes_proposed = [
        {
            "target_scope": "sharepoint_admin",
            "target_uri": f"https://tenant.sharepoint.com/sites/{job_number}/_api/folders",
            "write_type": "create_folders",
            "content_summary": f"Initialize project folder structure for {job_number}"
        },
        {
            "target_scope": "sharepoint_admin",
            "target_uri": f"https://tenant.sharepoint.com/sites/{job_number}/governance/permission_matrix.json",
            "write_type": "upload_file",
            "content_summary": "Upload project permission matrix"
        }
    ]
    
    output = {
        "run_id": run_id,
        "agent_id": "onboarding_agent",
        "proposed_permission_matrix": proposed_permission_matrix,
        "proposed_folders": proposed_folders,
        "proposed_escalation_matrix": proposed_escalation_matrix,
        "resolution_path": "template",
        "writes_proposed": writes_proposed,
        "outcome": "completed_with_write"
    }
    
    # 5. Validation
    validator = ValidatorClient()
    val_result = validator.validate(
        run_id=run_id,
        agent_id="onboarding_agent",
        agent_version=AGENT_VERSION,
        output=output,
        proposed_writes=output["writes_proposed"],
        proposed_filenames=[]
    )
    
    if not val_result.get("pass", False):
        output["outcome"] = "halted_validation"
        output["writes_proposed"] = []
        
    return output
