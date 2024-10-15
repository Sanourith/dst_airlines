import os
import json
from flatten_json import flatten
import pandas as pd
import requests
from dotenv import load_dotenv
import json
import logging.config
import logging.handlers
import os
from .logging.logging_setup import setup_logging
from typing import List


logger = logging.getLogger(__name__)


def test(string = "un deux un deux test") -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"{__file__ = }")
    print(f"{script_dir = }")
    print(f'{string = }')


def test_logging():
    setup_logging()

    logger.error("éàù", extra={"x": "hello"})
    logger.debug("debug message", extra={"x": "hello"})
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("exception message")


def load_env_variables(public_env_path: str=None, private_env_path: str=None) -> None:
    """Load environment variables declared into two files "public.env" (for public env. var. which can be shared) 
    and "private.env" (for private env. var. which should not be shared), both stored in the folder "env" located
    in the "env" folder at the project root  

    To get the env. variable : `os.getenv("VAR_NAME")`

    Args:
        public_env_path (str, optional): Path to the public environment variables. Defaults to None.
        private_env_path (str, optional): Path to the private environment variables. Defaults to None.
    """
    project_root = get_project_root_path()
    
    public_env_path = public_env_path if public_env_path else os.path.join(project_root, "env", "public.env")
    private_env_path = private_env_path if private_env_path else os.path.join(project_root, "env", "private.env")
    
    load_dotenv(dotenv_path=public_env_path)
    load_dotenv(dotenv_path=private_env_path)

    logger.info(f'Variables publiques chargées depuis : {public_env_path}')
    logger.info(f'Variables privées chargées depuis : {private_env_path}')


def get_project_root_path() -> str:
    """Return the absolute path to the root of the project

    Returns:
        str: Path to the project root
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    return project_root


def store_json_file(file_path: str, data: object) -> None:
    """Store data into a JSON file

    Args:
        file_path (str): Path where to store the data
        data (object): Data to be stored
    """
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)
        logger.info(f"Données enregistrées dans '{file_path}'.")


def retrieve_json(file_path: str) -> dict | list:
    """Retrieve JSON data from the given file path

    Args:
        file_path (str): Path of the JSON to be retrieved

    Returns:
        dict | list: Dict or list of dicts stored into the JSON
    """
    try:
        with open(file_path, 'r') as f:
            flight_data = json.load(f)
    except FileNotFoundError:
        logger.exception(f"Le fichier {f} n'a pas été trouvé.")
    except json.JSONDecodeError:
        logger.exception(f"Erreur de syntaxe dans le fichier JSON.")
    return flight_data


def build_data_storage_path(file_name: str, data_stage: str, folder: str = "") -> str:
    """Build an absolute path combining the given file name and the folder corresponding to the given data stage

    Args:
        file_name (str): Name of the file to be saved
        data_stage (str, optional): Name of the data stage. Defaults to "".
        folder (str): Name of the folder within the data_stage (e.g., "flights" or "weather_daily")

    Raises:
        ValueError: Error raised when the data_stage is not recognized or there is no corresponding folder to the given stage

    Returns:
        str: _description_
    """
    data_paths = {"raw": "1_raw",
                  "interim": "2_interim",
                  "processed": "3_processed",
                  "external": "4_external"}
    
    if data_stage in data_paths:
        complete_data_stage = data_paths[data_stage]
    else:
        logger.error(f"Le stage '{data_stage}' n'est pas dans la liste des possibilités : {data_paths.keys}.")
        raise ValueError(f"Le stage '{data_stage}' n'est pas dans la liste des possibilités : {data_paths.keys}.")        

    project_root = get_project_root_path()
    path = os.path.join(project_root, 'data', complete_data_stage, folder)

    if not os.path.exists(path):
        logger.error(f"Le chemin '{path}' n'existe pas sur votre machine.")
        raise ValueError(f"Le chemin '{path}' n'existe pas sur votre machine.")
    else:
        return os.path.join(path, file_name)


def flatten_list_of_dict(dicts: list) -> pd.DataFrame:
    """Flatten a list of dictionaries into a pandas DataFrame

    Args:
        dicts (list): List of dictonaries to be flatten

    Returns:
        pd.DataFrame: Resulting flattened dataframe
    """
    return pd.DataFrame([flatten(d) for d in dicts])


def get_public_ip_address() -> str:
    """Get your public address via the website ipfy.org

    Returns:
        str: Your public IP
    """
    ipfy_url = os.getenv("IPFY_URL")
    try:
        response = requests.get(ipfy_url)
        ip_info = response.json()
        public_ip = ip_info['ip']
        return public_ip
    except requests.RequestException:
        logger.exception("Erreur de récupération de l'adresse IP")
        return None
    

def build_lh_api_headers(api_token: str, public_ip: str) -> dict:
    """Build the Lufthansa API headers via the given API token & public IP

    Args:
        api_token (str): Your API token
        public_ip (str): Your public IP

    Returns:
        dict: The Lufthansa API headers
    """
    headers = {
        'Authorization': f'Bearer {api_token}',
        'X-originating-IP': public_ip
    }
    return headers


def get_lh_api_token(client_id: str="", client_secret: str="") -> str:
    """Get Lufthansa API token for the given client ID and secret (will retrieve the one in the environment variables by default)

    Args:
        client_id (str, optional): Lufthansa API client ID. Defaults to "".
        client_secret (str, optional): Lufthansa API secret. Defaults to "".

    Returns:
        str: Temporary access token derived from the client ID and secret
    """
    client_id = os.getenv("CLIENT_ID") if client_id == "" else client_id
    client_secret = os.getenv("CLIENT_SECRET") if client_secret == "" else client_secret
    lh_api = os.getenv("URL_API_LUFTHANSA")

    get_cred_request = {"client_id": client_id,
             "client_secret": client_secret,
             "grant_type": "client_credentials"}

    url = f'{lh_api}/oauth/token'

    r = requests.post(url=url, data=get_cred_request)
    logger.info(f"Code de réponse suite à la demande d'un nouveau token : {r.status_code}")

    return r.json()["access_token"]


def get_files_in_folder(folder_path: str) -> List[str]:
    """Generate a list containing all the files withtin the given folder

    Args:
        folder_path (str): Absolute path to the folder

    Returns:
        List[str]: List of the files within the given folder
    """
    files = [file for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]
    return files
