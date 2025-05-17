import aiohttp
import base64

from logging import getLogger, basicConfig, INFO
from asyncio import sleep
from uuid import uuid4, UUID
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


airflow_username = "admin"
airflow_password = "admin"

airflow_hostname = "airflow-webserver"
airflow_port = "8080"
dag_id = "predict_delay"
prediction_task_id = "predict_delay"
prediction_xcom_key = "prediction"

responses = {
    200: {"description": "OK"},
    400: {"description": "Bad request"},
    401: {"description": "Authentication failed"},
}

logger = getLogger(__name__)
basicConfig(level=INFO)

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "role": "user",
        "hashed_password": "$2b$12$SjNRrShqcITqCujOg58w7.oIsEqw5Sh.mILQcr2dA3k96syzPjucy", # password123
        "disabled": False,
    },
    "janedoe": {
        "username": "janedoe",
        "role": "admin",
        "hashed_password": "$2b$12$Uw334NP/JHnbSpq.KtujpeDLBv3WcdyPG2kfwJ0gUvEkoWibs89t6", # password456
        "disabled": False,
    },
    "bob": {
        "username": "bob",
        "role": "admin",
        "hashed_password": "$2b$12$31SyW.vA/9oI4MOkr5p4N.WSSP3/GofTKaH3dMkoP5S2JFYD2v5L.", # builder
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "role": "admin",
        "hashed_password": "$2b$12$Aaq9077v1JpzwJc3PD84vO.3KTGALximzCxYt6crC7w19izt/oRBG", # wonderland
        "disabled": False,
    }
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    role: str
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


class UserCreationRequest(BaseModel):
    """Body to create a user.

    Args:

        username (str): username of the user
        scheduled_arrival_time (str): password of the user
    """
    username: str
    password: str


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


app = FastAPI(openapi_tags=[
    {
        "name": "home",
        "description": "default functions"
    },
    {
        "name": "identification",
        "description": "functions to generate a token required to access the application"
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


def _verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def _get_password_hash(password):
    return pwd_context.hash(password)


def _get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def _authenticate_user(fake_db, username: str, password: str):
    user = _get_user(fake_db, username)
    if not user:
        return False
    if not _verify_password(password, user.hashed_password):
        return False
    return user


def _create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def _get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = _get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def _get_current_active_user(
    current_user: Annotated[User, Depends(_get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


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


async def _add_user(username: str, password: str) -> bool:
    """Add a user in the user database

    Args:
        username (str): username of the user
        password (str): password of the user

    Returns:
        bool: True if the user has been added, else False 
    """
    is_added = False

    if username not in fake_users_db:
        fake_users_db[username] = {
            "username": username,
            "role": "user",
            "hashed_password": _get_password_hash(password),
            "disabled": False, 
        }
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


@app.post("/token", tags=["identification"])
async def post_login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = _authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = _create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/token/check", status_code=200, tags=['identification'])
async def get_token_check(current_user: Annotated[User, Depends(_get_current_active_user)]) -> JSONResponse:
    """Get a verification that your token is working.

    Returns:

        JSONResponse: Simple message to confirm everything is working as intended
    """
    return JSONResponse(content={"status": f"Hi {current_user.username}, your token is valid"})


@app.post("/predict_flight_delay", tags=["application"], responses=responses)
async def post_predict_flight_delay(request: PredictionRequest, current_user: Annotated[User, Depends(_get_current_active_user)]) -> JSONResponse:
    """Post a request to get a flight delay prediction (in minutes) based on the provided information 

    Args:

        request (PredictionRequest): Body of the request

    Raises:

        HTTPException: Error 401 - Authentication failed - username does not exist or match with password
        HTTPException: Error 500 - Internal Server Error - an unexpected error occurred

    Returns:

        JSONResponse: Prediction (in minutes) in JSON format {"state": state, "prediction": prediction, "message": message}
    """

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
            return JSONResponse(status_code=status_code, content={"state": state, "prediction": f"{prediction}", "message": message, "requester": current_user})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error - an unexpected error occurred. {e}")


@app.post("/add_user/", tags=["administration"], responses=responses)
async def post_add_user(request: UserCreationRequest, current_user: Annotated[User, Depends(_get_current_active_user)]) -> JSONResponse:
    """Post a request to add a new user to the user database

    Args:

        request (UserCreationRequest): Body of the request to add a new user

    Raises:

        HTTPException: Error 400 - Bad request - username already exists in the database
        HTTPException: Error 401 - Authentication failed - username = {provided username} does not exist or match with password

    Returns:

        JSONResponse: Confirmation message in JSON format {"message": f"Success - username = {provided username} successfully addded."}
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=401,
                            detail="Authentication failed - you do not have sufficient rights.")
    
    username = request.username
    password = request.password

    is_added = await _add_user(username=username, password=password)
    if is_added:
        return JSONResponse(content={"message": f"Success - {username = } successfully addded."})
    else:
        raise HTTPException(status_code=400,
                            detail=f"Bad request - {username = } already exists in the database.")