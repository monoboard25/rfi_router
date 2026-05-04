import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func
from azure.data.tables import TableServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

TABLE_CONN = os.getenv("AZURE_TABLE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
TABLE_NAME = os.getenv("AGENT_RUNS_TABLE", "agentruns")


def _table_client():
    if not TABLE_CONN:
        raise RuntimeError("AZURE_TABLE_CONNECTION_STRING not set")
    svc = TableServiceClient.from_connection_string(TABLE_CONN)
    return svc.create_table_if_not_exists(TABLE_NAME)


@app.route(route="validate", methods=["POST"])
def validate(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("invalid JSON", status_code=400)

    agent = payload.get("agent")
    action = payload.get("action")
    if not agent or not action:
        return func.HttpResponse("agent and action required", status_code=400)

    decision = "allow"
    reasons: list[str] = []
    if payload.get("dry_run") is True:
        decision = "dry_run"
    if payload.get("destructive") is True and not payload.get("approved"):
        decision = "deny"
        reasons.append("destructive action requires approval")

    record = {
        "PartitionKey": agent,
        "RowKey": f"{datetime.now(timezone.utc).isoformat()}-{action}",
        "decision": decision,
        "reasons": json.dumps(reasons),
        "payload": json.dumps(payload)[:30000],
    }
    try:
        _table_client().upsert_entity(record)
    except Exception as exc:
        logging.exception("table write failed")
        return func.HttpResponse(f"log failure: {exc}", status_code=500)

    return func.HttpResponse(
        json.dumps({"decision": decision, "reasons": reasons}),
        mimetype="application/json",
    )
