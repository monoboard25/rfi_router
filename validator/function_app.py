import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="validate", methods=["POST"])
def validate(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Validator Chain orchestrator processed a request.')
    
    # The orchestrator logic will go here
    
    return func.HttpResponse(
        "Validator Chain Orchestrator endpoint ready.",
        status_code=200
    )



@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse('{"status":"ok"}', mimetype="application/json")

