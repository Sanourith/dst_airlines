import aiohttp
import base64
from uuid import UUID
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from logging import getLogger, basicConfig, INFO
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from asyncio import sleep
from uuid import uuid4
from fastapi.middleware.cors import CORSMiddleware

basicConfig(level=INFO)
logger = getLogger(__name__)

## Example
# dag_id = "example_dag"
# task_id = "load_task"
# xcom_key = "final_result"

airflow_username = "admin"
airflow_password = "admin"

airflow_hostname = "airflow-webserver"
airflow_port = "8080"
dag_id = "predict_delay"
prediction_task_id = "predict_delay"
prediction_xcom_key = "prediction"


# TODO: stocker les utilisateurs dans une table MySQL
userdb = {"alice": "wonderland",
          "bob": "builder",
          "clementine": "mandarine"}

# TODO: stocker les admin dans une table MySQL
admindb = {"admin": "4dm1N"}


app = FastAPI(openapi_tags=[
    {
        "name": "home",
        "description": "default functions"
    },
    {
        "name": "application",
        "description": "functions to request a flight delay prediction"
    },
    {
        "name": "administration",
        "description": "functions to adminster the API"
    }
])


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Autoriser toutes les origines
    allow_credentials=True,
    allow_methods=["*"],  # Autoriser toutes les méthodes HTTP
    allow_headers=["*"],  # Autoriser tous les en-têtes
)


# TODO: Ajouter pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") (cf. cours)
security = HTTPBasic()


responses = {
    200: {"description": "OK"},
    400: {"description": "Bad request"},
    401: {"description": "Authentication failed"},
}


# TODO: Indiquer le format de scheduled_arrival_time
class PredictionRequest(BaseModel):
    """Body to request a flight delay prediction.

    Args:

        arrival_iata_code (str): 3-letter IATA code of the arrival airport
        scheduled_departure_utc_time (str): schedule departure time in UTC (format : YYYY-MM-DDThh:mmZ e.g., 2024-09-30T03:00Z)
        task_uuid (UUID): Automatically generated Airflow task UUID
    """
    arrival_iata_code: str
    scheduled_departure_utc_time: str
    task_uuid: UUID = Field(default_factory=uuid4)


class UserCreationRequest(BaseModel):
    """Body to create a user.

    Args:

        username (str): username of the user
        scheduled_arrival_time (str): password of the user
    """
    username: str
    password: str


def _verify_identity(username: str, password: str, db) -> bool:
    """Function to verify the identity of a user based on the provided username and password.

    Args:
        username (str): Username to verify
        password (str): Password to verify
        db (_type_): Database where to find the username & password

    Returns:
        bool: True if the username exists and corresponds to the password, else False 
    """
    username
    password 

    real_password = db.get(username)

    identity_verified = True if real_password == password else False
    
    return identity_verified


def _verify_identity_user(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """Extension of the _verify_identity for users

    Args:

        credentials (HTTPBasicCredentials, optional): provided credentials in the header. Defaults to Depends(security).

    Returns:

        bool: indicates if the identity is verified (True) or not (False)
    """
    return _verify_identity(credentials.username, credentials.password, userdb)


def _verify_identity_admin(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """Extension of the _verify_identity for administrators

    Args:

        credentials (HTTPBasicCredentials, optional): provided credentials in the header. Defaults to Depends(security).

    Returns:

        bool: indicates if the identity is verified (True) or not (False)
    """
    return _verify_identity(credentials.username, credentials.password, admindb)


async def _handle_airflow_api_response(response: aiohttp.client.ClientResponse) -> dict:
    """Handles the Airflow API response.

    Args:
        response (aiohttp.client.ClientResponse): Airflow API response

    Raises:
        HTTPException: Exception generated when the response status is not 200

    Returns:
        dict: Response of the Airflow API
    """
    if response.status == 200:
        response_data = await response.json()
        return response_data
    else:
        error_text = await response.text()
        print(f"Failed with status {response.status}: {error_text}")
        raise HTTPException(status_code=response.status, detail=error_text)


def _add_user(username: str, password: str) -> bool:
    """Add a user in the user database

    Args:
        username (str): username of the user
        password (str): password of the user

    Returns:
        bool: True if the user has been added, else False 
    """
    is_added = False

    if username not in userdb:
        userdb[username] = password
        is_added = True
    
    return is_added


@app.get("/", tags=['home'])
async def get_root() -> dict:
    """Get a welcome message when connecting on the API.

    Returns:

        dict: Simple message in a dictionary
    """
    return {"message": "Welcome to the prediction API of the DST Airlines project developped by Matthieu, Bruno and Gil!"}


@app.get("/health", status_code=200, tags=['home'])
async def get_health_check() -> JSONResponse:
    """Get a health check of the API.

    Returns:

        JSONResponse: Simple message to confirm everything is working as intended
    """
    return JSONResponse(content={"status": "ok - API is working"})


@app.post("/predict_flight_delay/", tags=["application"], responses=responses)
async def post_predict_flight_delay(request: PredictionRequest, valid_credentials: bool = Depends(_verify_identity_user)) -> JSONResponse:
    """Post a request to get a flight delay prediction (in minutes) based on the provided information 

    Args:

        request (PredictionRequest): Body of the request

    Raises:

        HTTPException: Error 401 - Authentication failed - username does not exist or match with password
        HTTPException: Error 500 - Internal Server Error - an unexpected error occurred

    Returns:

        JSONResponse: Prediction (in minutes) in JSON format {"state": state, "prediction": prediction, "message": message}
    """
    if not valid_credentials:
        logger.error("Error 401 - Authentication failed - username does not exist or match with password.")
        raise HTTPException(status_code=401,
                            detail="Authentication failed - username does not exist or match with password.")

    url = f"http://{airflow_hostname}:{airflow_port}/api/v1/dags/{dag_id}/dagRuns"
    credentials = f"{airflow_username}:{airflow_password}"

    headers = {"Content-Type": "application/json", "Authorization": "Basic " + base64.b64encode(credentials.encode()).decode("utf-8")}
    data = {"dag_run_id": str(request.task_uuid), "conf": {"arrival_iata_code": request.arrival_iata_code, "scheduled_departure_utc_time": request.scheduled_departure_utc_time}}
    logger.info(f"Setup the url as {url = }.")

    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"Request to be sent to the {url = } with the following data : dag_run_id = {str(request.task_uuid)} | {request.arrival_iata_code = } | {request.scheduled_departure_utc_time = }.")
            async with session.post(url, headers=headers, json=data) as response:
                logger.info(f"Request sent to the {url = } to trigger the DAG ({dag_id = }), waiting for the response.")
                response_data = await _handle_airflow_api_response(response)
            
            logger.info(f"DAG ({dag_id = }) triggered.")

            state = response_data["state"]
            count = 0
            max_count = 5 * 60
            url_get_state = f"{url}/{request.task_uuid}"

            while state not in ["success", "failed"] and count < max_count :
                count += 1
                logger.info(f"{state = } not yet either successful of failed, waiting 1s ({count}s / {max_count}s)")
                await sleep(1)

                logger.info(f"Request to be sent to the {url_get_state = }")
                async with session.get(url_get_state, headers=headers) as response:
                    logger.info(f"Request sent to the {url_get_state = }, waiting for the response.")
                    response_data = await _handle_airflow_api_response(response)
                
                state = response_data["state"]
                logger.info(f"{state = } of the {dag_id = } for the dag_run_id = {str(request.task_uuid)}.")

            if state == "success":
                url_get_xcom = f"{url}/{request.task_uuid}/taskInstances/{prediction_task_id}/xcomEntries/{prediction_xcom_key}"
                
                logger.info(f"Request to be sent to the {url_get_state = } to collect result from XCom.")
                async with session.get(url_get_xcom, headers=headers) as response:
                    logger.info(f"Request to be sent to the {url_get_state = } to collect the prediction from XCom, waiting for the response.")
                    response_data = await _handle_airflow_api_response(response)

                status_code = 200
                prediction = response_data['value']
                message = "The prediction was successful, please check the value associated to the key 'prediction' to get it."
                logger.info(f"{prediction = } retrived from Airflow, returning the value")
            else:
                status_code = 400
                prediction = ""                
                message = "The prediction failed, please check that the provided data are correct."
            return JSONResponse(status_code=status_code, content={"state": state, "prediction": f"{prediction}", "message": message})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error - an unexpected error occurred. {e}")


@app.post("/add_user/", tags=["administration"], responses=responses)
async def post_add_user(request: UserCreationRequest, valid_credentials: bool = Depends(_verify_identity_admin)) -> JSONResponse:
    """Post a request to add a new user to the user database

    Args:

        request (UserCreationRequest): Body of the request to add a new user

    Raises:

        HTTPException: Error 400 - Bad request - username already exists in the database
        HTTPException: Error 401 - Authentication failed - username = {provided username} does not exist or match with password

    Returns:

        JSONResponse: Confirmation message in JSON format {"message": f"Success - username = {provided username} successfully addded."}
    """
    if not valid_credentials:
        raise HTTPException(status_code=401,
                            detail="Authentication failed - username does not exist or match with password")
    
    username = request.username
    password = request.password

    is_added = _add_user(username=username, password=password)
    if is_added:
        return JSONResponse(content={"message": f"Success - {username = } successfully addded."})
    else:
        raise HTTPException(status_code=400,
                            detail=f"Bad request - {username = } already exists in the database.")
    

