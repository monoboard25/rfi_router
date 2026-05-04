import logging
import azure.functions as func
import json
from src.agent import run_bid_assist_agent

app = func.FunctionApp()

@app.route(route="bid_assist")
def bid_assist(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a Bid Assist request.')

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
             "Invalid JSON payload.",
             status_code=400
        )

    try:
        # Pass the payload to the agent brain
        result_dict = run_bid_assist_agent(req_body)
        
        return func.HttpResponse(
            body=json.dumps(result_dict),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error in Bid Assist Agent: {str(e)}")
        return func.HttpResponse(
             f"Internal Server Error: {str(e)}",
             status_code=500
        )



@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse('{"status":"ok"}', mimetype="application/json")

