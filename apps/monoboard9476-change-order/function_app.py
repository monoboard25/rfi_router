import json
import logging
import os

import azure.functions as func
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

VALIDATOR_API_URL = os.getenv("VALIDATOR_API_URL")
APPROVAL_THRESHOLD = float(os.getenv("CO_APPROVAL_THRESHOLD", "10000"))


@app.route(route="evaluate_change_order", methods=["POST"])
def evaluate_change_order(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("invalid JSON", status_code=400)

    co_id = payload.get("co_id")
    amount = float(payload.get("amount", 0))
    if not co_id:
        return func.HttpResponse("co_id required", status_code=400)

    requires_approval = amount >= APPROVAL_THRESHOLD
    payload_to_validate = {
        "agent": "change-order",
        "action": "evaluate",
        "co_id": co_id,
        "amount": amount,
        "destructive": requires_approval,
        "approved": payload.get("approved", False),
    }

    decision = {"decision": "allow"}
    if VALIDATOR_API_URL:
        try:
            resp = requests.post(VALIDATOR_API_URL, json=payload_to_validate, timeout=15)
            resp.raise_for_status()
            decision = resp.json()
        except Exception:
            logging.exception("validator call failed")

    return func.HttpResponse(
        json.dumps({"co_id": co_id, "amount": amount, "requires_approval": requires_approval, "validator": decision}),
        mimetype="application/json",
    )
