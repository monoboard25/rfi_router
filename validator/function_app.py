import os
import sys
import json
import logging
import azure.functions as func

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from orchestrator import ValidatorOrchestrator

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

_orchestrator = None
def get_orchestrator() -> ValidatorOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ValidatorOrchestrator()
    return _orchestrator


@app.route(route="validate", methods=["POST"])
def validate(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Validator orchestrator received POST /validate")

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"pass": False, "error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    required = ("run_id", "agent_id", "output")
    missing = [k for k in required if k not in body]
    if missing:
        return func.HttpResponse(
            json.dumps({"pass": False, "error": f"Missing required fields: {missing}"}),
            status_code=400,
            mimetype="application/json",
        )

    run_id = body["run_id"]
    agent_id = body["agent_id"]
    output = body["output"]
    proposed_writes = body.get("proposed_writes", output.get("writes_proposed", []))
    proposed_filenames = body.get(
        "proposed_filenames",
        [w.get("proposed_filename") for w in proposed_writes if w.get("proposed_filename")],
    )

    try:
        result = get_orchestrator().execute_chain(
            run_id, agent_id, output, proposed_writes, proposed_filenames
        )
        status = 200 if result.get("pass") else 422
        return func.HttpResponse(
            json.dumps(result),
            status_code=status,
            mimetype="application/json",
        )
    except Exception as e:
        logging.exception("Orchestrator error")
        return func.HttpResponse(
            json.dumps({"pass": False, "error": f"Internal error: {e}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse('{"status":"ok"}', mimetype="application/json")
