from dst_airlines.data.lufthansa_api_flights import download_fullday_departing_flights
from dst_airlines.logging import logging_setup
from dst_airlines import utils

def main():
    # Configuration de la collecte des logs
    logging_setup.setup_logging()

    fra_iata = "FRA"

    # Récupération de l'adresse IP
    public_ip = utils.get_public_ip_address()

    # Récupération d'un token de l'API LH valide
    api_token = utils.get_lh_api_token()

    # Collecte des données d'il y a 3 jours (comportement par défaut quand la date et l'heure ne sont pas spécifiées) pour FRA
    download_fullday_departing_flights(api_token=api_token, public_ip=public_ip, airport_iata=fra_iata)

if __name__ == "__main__":
    main()