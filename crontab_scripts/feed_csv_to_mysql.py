from dst_airlines.database import mysql
from dst_airlines import utils
from dst_airlines.data import airports
import pandas as pd
import os
from logging import getLogger

def main():
    utils.setup_logging()

    logger = getLogger(__name__)

    CURRENT_USER = os.getenv("CURRENT_USER")

    USER_USERNAME = os.getenv(f"MYSQL_{CURRENT_USER}_USERNAME")
    USER_PASSWORD = os.getenv(f"MYSQL_{CURRENT_USER}_PASSWORD")


    # Stockage des données des aéroports
    airports_df = airports.generate_clean_airport_data()

    table_name = "airports"

    logger.info(f"Starting the insertion of airports data into {table_name = }.")
    mysql.upload_data_in_mysql(data=airports_df, table="airports", sql_user=USER_USERNAME, sql_password=USER_PASSWORD)

    # Stockage des données de vol
    flights_folder_path = utils.build_data_storage_path(file_name="", data_stage="interim", folder="flights")    
    flights_files = utils.get_files_in_folder(flights_folder_path)
    clean_flights_files = [flight_file for flight_file in flights_files if flight_file.endswith(".csv")]

    for flights_file in clean_flights_files:
        flights_path = os.path.join(flights_folder_path, flights_file)

        flights_df = pd.read_csv(flights_path)

        table_name = "flights"
        logger.info(f"Starting the insertion of {flights_path} into {table_name = }.")
        mysql.upload_data_in_mysql(data=flights_df, table=table_name, sql_user=USER_USERNAME, sql_password=USER_PASSWORD)

    # Stockage des données de météo
    weather_forecasts_folder_path = utils.build_data_storage_path(file_name="", data_stage="interim", folder="weather_hourly")    
    weather_forecasts_files = utils.get_files_in_folder(weather_forecasts_folder_path)

    for weather_forecasts_file in weather_forecasts_files:
        weather_forecasts_path = os.path.join(weather_forecasts_folder_path, weather_forecasts_file)
        weather_forecasts_df = pd.read_csv(weather_forecasts_path)

        table_name = "weather_forecasts"
        logger.info(f"Starting the insertion of {weather_forecasts_path} into {table_name = }.")
        mysql.upload_data_in_mysql(data=weather_forecasts_df, table=table_name, sql_user=USER_USERNAME, sql_password=USER_PASSWORD)

if __name__ == "__main__":
    main()