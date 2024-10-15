import requests
import os
from datetime import datetime, timedelta
import time
import logging
from typing import List
# from dotenv import load_dotenv # Chargé directement depuis le __init__.py (via config.py)

from .. import utils

logger = logging.getLogger(__name__)

URL = os.getenv("URL_API_LUFTHANSA")


def fetch_departing_flights(airport_iata: str, headers: dict, api_name: str="flightstatus", date: str="", start_time: str="00:00") -> dict:
    """Fetch departing flights from the given airport_iata starting from start_time till midnight

    Args:
        airport_iata (str): IATA of the airport
        headers (dict): dictionnary containing "Authorization" and "X-originating-IP" keys to authenticate the request
        api_name (str, optional): Name of the API (should be either "flightstatus" or "customerflightinformation"). Defaults to "flightstatus".
        date (str, optional): target date, format should be YYYY-MM-DD, if empty string is given, date will be set up as yesterday. Defaults to ''.
        start_time (str, optional): Start time from which fetching will start. Defaults to "00:00".

    Returns:
        dict: Dictionary containing a:
            - "metadata" field containing the request metadata
            - "data" field, containing answers from the API, each element of the list is an API call
    """
    ###
    # Création d'une fonction interne pour incrémenter l'endpoint de 4h (par défaut)
    # l'API ne renvoie que des données sur une tranche ("range") de 4h
    ###
    def increment_range(flight_endpoint: str) -> tuple:
        """Increment the starting time of the flight_endpoint of 4h (API range)

        Args:
            flight_endpoint (str): complete flight endpoint (exept the limit & offset)

        Returns:
            tuple: Tuple composed of a boolean indicating if the incremented time is outranged (> 24h) and the new endpoint
        """
        range_length = 4
        start_range = flight_endpoint[-5:]

        hour_int = int(start_range.split(":")[0])
        hour_int += range_length
        hour_str = "0" + str(hour_int) if hour_int < 10 else str(hour_int)

        minutes_str = start_range.split(":")[1]

        start_time = hour_str + ":" + minutes_str           
        new_flight_endpoint = flight_endpoint[:-5] + start_time

        if hour_int >= 24:
            logger.info(f"Nouveau range dépasse 24h (heure après incrémentation : {hour_int}h)")
            outranged = True
            return (outranged, new_flight_endpoint)
        else :
            logger.info(f"Nouvelle heure de début : {start_time}")
            logger.info(f"Nouveau endpoint : {new_flight_endpoint}")
            outranged = False
            return (outranged, new_flight_endpoint)

    ###
    # Définition des variables
    ###
    airport_endpoint = f"/operations/{api_name}/departures/{airport_iata}/"

    if date == '':
        date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    flight_endpoint =  airport_endpoint + date + "T" + start_time

    LIMIT = 50 # nombre max par page - l'API ne renvoie pas plus de 50 vols
    offset = 0 # démarre à la 1e page
    total_range_count = 0 # nombre d'éléments dans le range

    count = 0

    if api_name == "flightstatus":
        data_container = "FlightStatusResource"
    elif api_name == "customerflightinformation":
        data_container = "FlightInformation"
    else:
        logger.error(f"La valeur de {api_name = } n'est pas une valeur acceptée ('flightstatus' ou 'customerflightinformation')")
        raise ValueError(f"La valeur de {api_name = } n'est pas une valeur acceptée ('flightstatus' ou 'customerflightinformation')")

    ###
    # Structuration du dictionnaire final
    ###
    flights_data_dic = {}
    flights_data_dic["metadata"] = {}
    flights_data_dic["metadata"]["initial_flight_endpoint"] = flight_endpoint
    flights_data_dic["metadata"]["time_at_execution"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    flights_data_dic["metadata"]["start_range"] = flight_endpoint[-16:]
    flights_data_dic["data"] = []

    ###
    # Boucle pour parcourir les ranges de 4h puis la pagination des données sur ces ranges
    # En effet, si on requête les données à l'heure "08:00", l'API va être fournir les résultats
    # par page de 50 éléments max sur les 4h suivantes (donc de 08:00 à 12:00) 
    ###
    # TODO: Voir s'il est possible de changer la boucle while
    while True:
        count += 1
        ###
        # Récupération de la requête
        ###
        request = f"{URL}{flight_endpoint}?limit={LIMIT}&offset={offset}"
        response = requests.get(request, headers = headers)
        logger.info(f"Requête envoyée à : {request}")
        logger.info(f"Code réponse : {response.status_code}")

        ###
        # Si la requête renvoie des données sur ce range & offset (code 200 = OK)
        ###
        if response.status_code == 200:
            # Récupération des données
            flights_data = response.json()
            flights_data_dic["data"].append(flights_data)

            logger.debug(f'Longeur du résultat : {len(flights_data[data_container]["Flights"]["Flight"])}')
            
            # Nombre total d'éléments dans ce range de 4h
            total_range_count = flights_data[data_container]["Meta"]["TotalCount"]

            logger.debug(f"Offset: {offset} / {total_range_count}")
            offset += LIMIT

            # Si l'offset est supérieur au total d'éléments du range, incrémentation du range
            if offset >= total_range_count:
                offset = 0
                outranged, flight_endpoint = increment_range(flight_endpoint)
                # Si le range incrémenté commence le lendemain (> 24h) on arrête
                if outranged:
                    break

        ###
        # Si la requête ne renvoie pas de données (code 404 = Not Found)
        ###
        elif response.status_code == 404:
            logger.info(f"Erreur 404, pas de données sur le range de 4h commençant à : {start_time} avec pour offset : {offset}")

            # Incrémentation du range car il n'y a pas de données de celui-ci
            outranged, flight_endpoint = increment_range(flight_endpoint)
            offset = 0

            # Si le range incrémenté commence le lendemain (> 24h) on arrête
            if outranged:
                break

        ###
        # Si on a réalisé trop de requêtes en 1s
        ###
        elif response.status_code == 403 and response.json()["Error"] == "Account Over Queries Per Second Limit":
            time.sleep(1)
            logger.warning("Trop de requêtes par seconde, pause d'une 1s")
        
        ###
        # Si une autre erreur survient, on arrête
        ###
        else:
            logger.error(f"Erreur sur la requête de {flight_endpoint}: {response.status_code}", extra={"error_message": f'{response.json()["Error"]}'})
            break

    flights_data_dic["metadata"]["end_range"] = flight_endpoint[-16:]

    logger.info(f"Nombre de requêtes : {count}")
    return flights_data_dic


def extract_flights_from_resources(flight_resources: List[dict]) -> List[dict]:
    """Extract flights data from a list containing the flight resource content 
    (either "FlightStatusResource" or "customerflightinformation" content)

    Args:
        flight_resources (List[dict]): List containing the flight resource content (list of dictionaries with "Flights" and "Meta" as keys)

    Returns:
        List[dict]: List of "Flight" elements (value corresponding to the "Flight" key)
    """

    ###
    # Prépare la vérification du compte des vols reçus dans un intervalle de 4h 
    # par rapport au checksum envoyé par l'API
    ###
    table_total_count = 0
    flight_endpoint = flight_resources[0]["Meta"]["Link"][0]["@Href"].split("?")[0]
    meta_total_count = flight_resources[0]["Meta"]["TotalCount"]

    flights = []

    ###
    # Parcourt chacune des réponses de l'API
    ###
    for flight_resource in flight_resources:        
        
        ###
        # Vérifie le compte des vols reçus dans un intervalle de 4h 
        # par rapport au checksum envoyé par l'API
        ###
        new_flight_endpoint = flight_resource["Meta"]["Link"][0]["@Href"].split("?")[0]

        if new_flight_endpoint != flight_endpoint:
            if meta_total_count != table_total_count:
                flight_endpoint_verif = flight_resource["Meta"]["Link"][0]["@Rel"]
                logger.error(f"Attention, pour le endpoint {new_flight_endpoint} (vérif : {flight_endpoint_verif}) ! La longueur du tableau ({table_total_count}) n'est pas égale au compte total des métadonnées ({meta_total_count}).")

            flight_endpoint = new_flight_endpoint
            table_total_count = 0

        table_total_count += len(flight_resource["Flights"]["Flight"])
        meta_total_count = flight_resource["Meta"]["TotalCount"]

        ###
        # Ajoute les données à aux résultats pour consolider les vols dans une unique liste
        ###   
        for flight in flight_resource["Flights"]["Flight"]:
            flights.append(flight)

    return flights


def structure_departing_flights(file: str | dict, api_name: str) -> dict :
    """Structure the departing raw JSON by regrouping all flights into a single list

    Args:
        file (str or dict): Either the file path or the dictionary containing the raw data

    Returns:
        dict: Dictionary containing a:
            - "metadata" field containing the request metadata
            - "flights" field, containing a list of all flights in the raw data
    """
    
    ###
    # Vérifie si la variable donné est un chemin (string) ou les données directement
    ###
    if isinstance(file, str):
        flight_data = utils.retrieve_json(file)
    else:
        flight_data = file

    ###
    # Définit quelle API a été utilisé pour spécifier la forme du résultat
    ###
    if api_name == "flightstatus":
        data_container = "FlightStatusResource"
    elif api_name == "customerflightinformation":
        data_container = "FlightInformation"
    else:
        logger.error(f"La valeur de {api_name = } n'est pas une valeur acceptée ('flightstatus' ou 'customerflightinformation')")
        raise ValueError(f"La valeur de {api_name = } n'est pas une valeur acceptée ('flightstatus' ou 'customerflightinformation')")


    ###
    # Initie le résultat
    ###
    consolidated_flight_data = {}
    consolidated_flight_data["metadata"] = flight_data["metadata"]
    
    flight_resources = [flight_resource[data_container] for flight_resource in flight_data["data"]]
    
    consolidated_flight_data["flights"] = extract_flights_from_resources(flight_resources)

    return consolidated_flight_data


def download_fullday_departing_flights(api_token: str, public_ip: str, airport_iata: str, api_name: str="flightstatus", date: str="", start_time: str="00:00") -> None:
    """Consolidated function to collect the departing flights from the start time (by default 00:00 - beginning of the day) till midnight
    for the given date (by default 3 days ago) for a given airport using the given credentials
    The resulting data will be stored in raw format into data/1_raw then in interim format in data/2_interm in a consolidated JSON and CSV

    Args:
        api_token (str): Lufthansa API token
        public_ip (str): The IP address executing the script
        airport_iata (str): IATA of the airport from where the departing flights will be collected
        api_name (str, optional): Name of the API (should be either "flightstatus" or "customerflightinformation"). Defaults to "flightstatus".
        date (str, optional): Date (format: YYYY-MM-DD) of the expected data - attention, the API provides a limited range of data. Defaults to "" = 3 days ago.
        start_time (str, optional): Time (format: HH:mm) from when to start the extraction. Defaults to "00:00".
    """
    if date:
        if isinstance(date, datetime):
            date_formated = date.strftime('%Y-%m-%d')
        elif isinstance(date, str):
            date_formated = date
    else:
        date_formated = (datetime.today() - timedelta(days=3)).strftime('%Y-%m-%d')

    file_name_base = f"{airport_iata}_{api_name}_dep_flights_{date_formated}"

    headers = utils.build_lh_api_headers(api_token, public_ip)

    # Récupération des données de vol depuis l'API et stockage
    flight_data = fetch_departing_flights(airport_iata, headers, api_name=api_name, date=date_formated, start_time=start_time)
    file_name = f"{file_name_base}.json"
    file_path = utils.build_data_storage_path(file_name=file_name, data_stage="raw")
    utils.store_json_file(file_path, flight_data)

    # Consolidation des données reçues et stockage
    consolidated_flight_data = structure_departing_flights(file_path, api_name)
    file_name = f"{file_name_base}_conso.json"
    file_path = utils.build_data_storage_path(file_name=file_name, data_stage="interim", folder="flights")
    utils.store_json_file(file_path, consolidated_flight_data)

    # Applatissement du dictionnaire et stockage en CSV
    flights_df = utils.flatten_list_of_dict(consolidated_flight_data["flights"])
    file_name = f"{file_name_base}_conso_flatten.csv"
    file_path = utils.build_data_storage_path(file_name=file_name, data_stage="interim", folder="flights")
    flights_df.to_csv(file_path, index=False)