#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import mysql.connector
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Déterminer le chemin du script et charger les variables d'environnement
script_path = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(script_path, "../env/private.env")

# Vérifier si le fichier env existe
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    print(
        f"Attention: Le fichier {env_file} n'existe pas. Utilisation des variables d'environnement système."
    )

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Récupération des variables d'environnement
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# MySQL
sql_user = os.getenv("MYSQL_USER")
sql_password = os.getenv("MYSQL_ROOT_PASSWORD")
sql_host = os.getenv("MYSQL_HOST")
sql_port = int(os.getenv("MYSQL_PORT"))
sql_database = os.getenv("MYSQL_DATABASE")


class LufthansaAPI:
    """Classe pour interagir avec l'API Lufthansa"""

    BASE_URL = "https://api.lufthansa.com/v1"
    TOKEN_URL = "https://api.lufthansa.com/v1/oauth/token"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None

    def get_access_token(self) -> str:
        """Récupère un token d'accès à l'API Lufthansa"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        logger.info("Obtention d'un nouveau token d'accès")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        try:
            response = requests.post(self.TOKEN_URL, data=payload)
            response.raise_for_status()
            data = response.json()

            self.access_token = data["access_token"]
            # Définir l'expiration du token (généralement 1 heure)
            expires_in = data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'authentification: {e}")
            raise

    def get_flights(self, origin: str, date: str) -> List[Dict[str, Any]]:
        """
        Récupère les vols au départ d'un aéroport pour une date donnée

        :param origin: Code IATA de l'aéroport de départ (ex: 'FRA')
        :param date: Date au format YYYY-MM-DD
        :return: Liste des vols
        """
        endpoint = f"/operations/flightstatus/departures/{origin}/{date}"
        url = f"{self.BASE_URL}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Accept": "application/json",
        }

        try:
            logger.info(f"Récupération des vols au départ de {origin} pour le {date}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Extraction des vols depuis la réponse de l'API
            flights = data.get("FlightStatusResource", {}).get("Flights", {}).get("Flight", [])
            if not isinstance(flights, list):
                flights = [flights]  # Si un seul vol, mettre dans une liste

            return flights
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Aucun vol trouvé pour {origin} le {date}")
                return []
            logger.error(f"Erreur HTTP lors de la récupération des vols: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération des vols: {e}")
            raise
        except (KeyError, TypeError) as e:
            logger.error(f"Erreur dans la structure des données: {e}")
            return []


def save_to_json(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Sauvegarde les données dans un fichier JSON

    :param data: Données à sauvegarder
    :param filename: Nom du fichier
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Données sauvegardées dans {filename}")
    except IOError as e:
        logger.error(f"Erreur lors de la sauvegarde du fichier JSON: {e}")
        raise


def insert_into_mysql(flights: List[Dict[str, Any]], db_config: Dict[str, Any]) -> None:
    """
    Insère les données de vols dans une base de données MySQL

    :param flights: Liste des vols à insérer
    :param db_config: Configuration de la base de données
    """
    if not flights:
        logger.warning("Aucun vol à insérer dans la base de données")
        return

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Création de la table si elle n'existe pas déjà
        create_table_query = """
        CREATE TABLE IF NOT EXISTS lufthansa_flights (
            id VARCHAR(100) PRIMARY KEY,
            flight_number VARCHAR(20),
            carrier_code VARCHAR(10),
            carrier_name VARCHAR(100),
            origin VARCHAR(10),
            destination VARCHAR(10),
            scheduled_departure DATETIME,
            actual_departure DATETIME,
            status VARCHAR(50),
            terminal VARCHAR(10),
            gate VARCHAR(10),
            aircraft_type VARCHAR(50),
            raw_data JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        conn.commit()

        inserted_count = 0
        for flight in flights:
            try:
                # Extraction des données pertinentes
                flight_id = flight.get("FlightID", "")
                flight_details = flight.get("MarketingCarrier", {})
                flight_number = flight_details.get("FlightNumber", "")
                carrier_code = flight_details.get("AirlineID", "")
                carrier_name = flight_details.get("Name", "")

                departure = flight.get("Departure", {})
                origin = departure.get("AirportCode", "")
                terminal = departure.get("Terminal", {}).get("Name", "")
                gate = departure.get("Gate", {}).get("Name", "")

                scheduled_time = departure.get("ScheduledTimeLocal", {}).get("DateTime", "")
                actual_time = departure.get("ActualTimeLocal", {}).get("DateTime", "")

                arrival = flight.get("Arrival", {})
                destination = arrival.get("AirportCode", "")

                status = flight.get("Status", {}).get("Code", "")
                aircraft = flight.get("Equipment", {}).get("AircraftCode", "")

                # Préparation de l'insert SQL
                insert_query = """
                INSERT INTO lufthansa_flights 
                (id, flight_number, carrier_code, carrier_name, origin, destination, 
                scheduled_departure, actual_departure, status, terminal, gate, aircraft_type, raw_data) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                flight_number = VALUES(flight_number),
                carrier_code = VALUES(carrier_code),
                carrier_name = VALUES(carrier_name),
                origin = VALUES(origin),
                destination = VALUES(destination),
                scheduled_departure = VALUES(scheduled_departure),
                actual_departure = VALUES(actual_departure),
                status = VALUES(status),
                terminal = VALUES(terminal),
                gate = VALUES(gate),
                aircraft_type = VALUES(aircraft_type),
                raw_data = VALUES(raw_data)
                """

                values = (
                    flight_id,
                    flight_number,
                    carrier_code,
                    carrier_name,
                    origin,
                    destination,
                    scheduled_time,
                    actual_time,
                    status,
                    terminal,
                    gate,
                    aircraft,
                    json.dumps(flight),
                )

                cursor.execute(insert_query, values)
                inserted_count += 1

            except (KeyError, TypeError) as e:
                logger.error(f"Erreur lors de l'extraction des données de vol: {e}")
                continue

        conn.commit()
        logger.info(f"{inserted_count} vols insérés dans la base de données")

    except mysql.connector.Error as e:
        logger.error(f"Erreur MySQL: {e}")
        raise
    finally:
        if "conn" in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            logger.info("Connexion MySQL fermée")


def main():
    """Fonction principale"""
    # Script path pour les chemins relatifs
    script_path = os.path.dirname(os.path.abspath(__file__))

    # Vérification des variables d'environnement
    required_vars = [
        "CLIENT_ID",
        "CLIENT_SECRET",
        "MYSQL_USER",
        "MYSQL_ROOT_PASSWORD",
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_DATABASE",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Variables d'environnement manquantes: {', '.join(missing_vars)}")
        return

    try:
        # Date d'hier au format YYYY-MM-DD
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Initialisation de l'API Lufthansa
        api = LufthansaAPI(client_id, client_secret)

        # Récupération des vols
        flights = api.get_flights(origin="FRA", date=yesterday)

        if not flights:
            logger.warning(f"Aucun vol trouvé pour FRA le {yesterday}")
            return

        # Sauvegarde en JSON dans un sous-répertoire data/1_raw
        json_filename = f"../data/1_raw/lufthansa_flights_FRA_{yesterday}.json"
        json_path = os.path.join(script_path, json_filename)

        # Création du répertoire s'il n'existe pas
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        save_to_json(flights, json_path)

        # Configuration MySQL
        db_config = {
            "user": sql_user,
            "password": sql_password,
            "host": sql_host,
            "port": sql_port,
            "database": sql_database,
        }

        # Insertion dans MySQL
        insert_into_mysql(flights, db_config)

        logger.info("Traitement terminé avec succès")

    except Exception as e:
        logger.error(f"Erreur générale: {e}")


if __name__ == "__main__":
    env_file = os.path.join(script_path, "../env/private.env")
    load_dotenv(env_file)
    main()
