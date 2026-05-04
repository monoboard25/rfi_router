import json
import logging
import os

import azure.functions as func
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

VALIDATOR_API_URL = os.getenv("VALIDATOR_API_URL")


@app.route(route="route_rfi", methods=["POST"])
def route_rfi(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("invalid JSON", status_code=400)

    rfi_id = payload.get("rfi_id")
    subject = payload.get("subject", "")
    body = payload.get("body", "")
    if not rfi_id:
        return func.HttpResponse("rfi_id required", status_code=400)

    target = "structural" if any(k in (subject + body).lower() for k in ["beam", "column", "load", "footing"]) else "general"

    decision = {"decision": "allow"}
    if VALIDATOR_API_URL:
        try:
            resp = requests.post(
                VALIDATOR_API_URL,
                json={"agent": "rfi-router", "action": "route", "rfi_id": rfi_id, "target": target},
                timeout=15,
            )
            resp.raise_for_status()
            decision = resp.json()
        except Exception:
            logging.exception("validator call failed")

    return func.HttpResponse(
        json.dumps({"rfi_id": rfi_id, "target": target, "validator": decision}),
        mimetype="application/json",
    )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse('{"status":"ok"}', mimetype="application/json")
