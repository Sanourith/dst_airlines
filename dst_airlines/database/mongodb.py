from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure
import os
import logging
from .. import utils
from typing import List
import json

logger = logging.getLogger(__name__)

def create_users(mongo_client: MongoClient, database_name: str, user_list: List[str], role: str = "readWrite") -> None:
    """Tries to create users listed in "user_list" with the given "role" in the MongoDB database named "database_name" from the MongoDB mongo_client, it will handle the issue if the user already exists without failing

    Args:
        mongo_client (MongoClient): MongoDB client
        database_name (str): Name of the MongoDB database
        user_list (List[str]): List of the users to be added
        role (str, optional): Role to be given to the users. Defaults to "readWrite".

    Raises:
        e: All standard errors apart from OperationFailure code 51003 (user already exists)
    """
    db_admin = mongo_client["admin"]

    for user in user_list:
        user = user.upper()
        print(f"{user = }")
        user_username = os.getenv(f"{user}_USERNAME")
        user_password = os.getenv(f"{user}_PASSWORD")

        try:
            db_admin.command("createUser", user_username,
                             pwd = user_password,
                             roles = [{"role": role, "db": database_name}])
            logger.info(f"User '{user_username}' created in the database '{database_name}' with '{role}' role.")
        except OperationFailure as e:
            if e.code == 51003: # Code associé à l'erreur "l'utilisateur existe déjà"
                logger.info(f"User '{user_username}' already exist in the database '{database_name}'.")
            else:
                raise e


def add_flight_dict(flights: dict, flights_collection: Collection, existence_max_count: int=5, force_test_all: bool=False) -> bool:
    """Add a dict containing Lufthanza flights into the given MongoDB flights_collection 
    
    Will check if the MongoDB collection contains already at least existence_max_count documents of the provided dict
    if it is the case and force_test_all is False, it will stop and return False

    Args:
        flights (dict): Dictionary containing the raw flights to be added into the MongoDB flights_collection (dictionary generated by the fetch_departing_flights function)
        flights_collection (pymongo.collection.Collection): MongoDB collection where to add flights
        existence_max_count (int, optional): Maximum number of "FlightStatusResource" elements to check before considering that the provided dictionary has already been added. Defaults to 5.
        force_test_all (bool, optional): Force the test of all "FlightStatusResource" elements contained in the provided dictionary. Defaults to False.

    Returns:
        bool: Boolean indicating if the elements within the provided dictionary were fully added (True) or not (False) if there were too many present
    """
    # Sélection des données contenues dans la clé "FlightStatusResource"
    flight_data = flights["data"]
    flight_status_resources = [data["FlightStatusResource"] for data in flight_data]

    # Mise en place du test d'existence pour éviter l'intégralité du fichier s'il a déjà été inséré dans la collection
    existence_count = 0

    # Pour chacun des objets "FlightStatusResource"...
    for flight_status_resource in flight_status_resources:

        # Vérification de son existence au sein de la collection sinon, ajout, si oui incrémentation du comptage
        # Si le comptage atteint existence_max_count = 5, passage au fichier suivant
        existence_test = flights_collection.find_one(flight_status_resource)

        if existence_test == None:
            flights_collection.insert_one(flight_status_resource)
        elif existence_count >= existence_max_count and not force_test_all:
            break            
        else:
            existence_count +=1

    # Informe si la base a été entièrement été ajoutée le comptage atteint existence_max_count 
    if existence_count >= existence_max_count and not force_test_all:
        was_fully_added = False
        logger.info(f"At least {existence_max_count} documents of the provided dictionary already exist in the '{flights_collection.name}'.")
    else:
        was_fully_added = True
        logger.info(f"FlightStatusResource documents of the provided dictionary added in the '{flights_collection.name}' collection.")

    return was_fully_added


# TODO: Gestion de la situation où un fichier a été partiellement traité
def add_flight_files(mongo_client: MongoClient, db_name: str, collection_name: str, force_test_all: bool=False):
    """Add all flights raw data files (files in 1_raw folder containing "flight_file" but not "OLD") into the given mongo_client > database_name > collection_name. 
    The function checks if the document already exists in the collection and only add it if it's not the case.
    If the function finds that there are at least 5 FlightStatusRessource documents which already exist in the given collection, it will move to the next file apart if it is forced to test them all (via force_test_all)

    Args:
        mongo_client (MongoClient): Mongo Client to be used to find the database (the user must have sufficient rights)
        db_name (str): Name of the Mongo database
        collection_name (str): Name of the collection - will create one if it doesn't exist
        force_test_all (bool, optional): Force to check the existence of all FlightStatusRessource documents for a given file before moving to the next. Defaults to False - i.e., if 5 documents already exist in the collection, it will move to the next file.
    """
    # Récupération de la base de données et de la collection (en crée une si elle n'existe pas déjà)
    flights_db = mongo_client[db_name]

    if collection_name in flights_db.list_collection_names():
        flights_collection = flights_db[collection_name]
    else:
        flights_collection = flights_db.create_collection(collection_name)
        logger.info(f"'{collection_name}' collection created in '{db_name}' database.")

    # Récupération de la liste des fichiers JSON contenant les données de vol brutes
    raw_path = utils.build_data_storage_path("", data_stage="raw")
    raw_files = utils.get_files_in_folder(raw_path)
    flight_files = [flight_file for flight_file in raw_files if ("dep_flights" in flight_file and "OLD" not in flight_file)]

    # Pour chacun des fichiers de vol brute...
    for flights_file in flight_files:
        flights_path = os.path.join(raw_path, flights_file)
        
        # Récupération des données dans un dictionnaire
        with open(flights_path, "r") as file:
            flights = json.load(file)

        logger.info(f"Launch of the file {flights_path} insersion into the the '{collection_name}' collection of the '{db_name}' database.")

        add_flight_dict(flights, flights_collection, force_test_all=force_test_all)
        
        # # Sélection des données contenues dans la clé "FlightStatusResource"
        # flight_data = flights["data"]
        # flight_status_resources = [data["FlightStatusResource"] for data in flight_data]

        # # Mise en place du test d'existence pour éviter l'intégralité du fichier s'il a déjà été inséré dans la collection
        # existence_count = 0
        # existence_max_count = 5

        # # Pour chacun des objets "FlightStatusResource"...
        # for flight_status_resource in flight_status_resources:

        #     # Vérification de son existence au sein de la collection sinon, ajout, si oui incrémentation du comptage
        #     # Si le comptage atteint existence_max_count = 5, passage au fichier suivant
        #     existence_test = flights_collection.find_one(flight_status_resource)

        #     if existence_test == None:
        #         flights_collection.insert_one(flight_status_resource)
        #     elif existence_count >= existence_max_count and not force_test_all:
        #         break            
        #     else:
        #         existence_count +=1

        # # Si le comptage atteint existence_max_count = 5, traçage
        # if existence_count >= existence_max_count and not force_test_all:
        #     logger.info(f"At least {existence_max_count} documents of '{flights_path}' already exist in the '{collection_name}' collection of the '{db_name}' database, moved to the next file.")
        #     continue
        
        # logger.info(f"FlightStatusResource documents of '{flights_path}' added in the '{collection_name}' collection of the '{db_name}' database.")
