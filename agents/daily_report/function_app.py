import logging
import azure.functions as func
import json
from src.agent import run_daily_report_agent

app = func.FunctionApp()

@app.route(route="generate_daily_report")
def generate_daily_report(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a Daily Report request.')

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
             "Invalid JSON payload.",
             status_code=400
        )

    try:
        result_dict = run_daily_report_agent(req_body)
        
        return func.HttpResponse(
            body=json.dumps(result_dict),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error in Daily Report Agent: {str(e)}")
        return func.HttpResponse(
             f"Internal Server Error: {str(e)}",
             status_code=500
        )
