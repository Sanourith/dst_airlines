from dst_airlines.data.open_meteo_api_weather_hourly import download_weather_data_for_existing_flights
from dst_airlines.logging import logging_setup

def main():
    # Configuration de la collecte des logs
    logging_setup.setup_logging()

    # Collecte des données pour les données de vols existantes
    download_weather_data_for_existing_flights()


if __name__ == "__main__":
    main()