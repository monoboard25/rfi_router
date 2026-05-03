import logging
import azure.functions as func
import json
from src.agent import run_rfi_router_agent

app = func.FunctionApp()

@app.route(route="route_rfi")
def route_rfi(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed an RFI routing request.')

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
             "Invalid JSON payload.",
             status_code=400
        )

    try:
        # Pass the webhook payload to the agent brain
        result_dict = run_rfi_router_agent(req_body)
        
        return func.HttpResponse(
            body=json.dumps(result_dict),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error in RFI Router: {str(e)}")
        return func.HttpResponse(
             f"Internal Server Error: {str(e)}",
             status_code=500
        )
