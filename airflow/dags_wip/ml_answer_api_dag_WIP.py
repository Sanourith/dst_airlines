import os
from datetime import datetime
import pandas as pd
from joblib import load
import openmeteo_requests
import requests_cache
from retry_requests import retry
from typing import List
import logging
import time
import re
from typing import List, Dict
from openmeteo_requests.Client import OpenMeteoRequestsError

# from airflow import DAG
# from airflow.operators.python import PythonOperator
# from airflow.utils.dates import days_ago

def fetch_weather_data(airport_codes: List[str], latitudes: List[str], longitudes: List[str], times: List[str]):
    
    if (len(airport_codes) != len(latitudes)) or (len(airport_codes) != len(times)) or (len(airport_codes) != len(longitudes)):
        logger.error(error_message := f"Lengths of provided lists are not equals : {len(airport_codes) = } | {len(latitudes) = } | {len(longitudes) = } | {len(times) = }")
        raise ValueError(error_message)
    
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Variables = éléments de l'api Meteo que l'on veut mettre en avant dans notre database
    variables = ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature", "precipitation_probability",
                "precipitation", "rain", "showers", "snowfall", "snow_depth", "weather_code", "pressure_msl", "surface_pressure", 
                "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "visibility", "evapotranspiration", 
                "et0_fao_evapotranspiration", "vapour_pressure_deficit", "wind_speed_10m", "wind_speed_80m", "wind_speed_120m", 
                "wind_speed_180m", "wind_direction_10m", "wind_direction_80m", "wind_direction_120m", "wind_direction_180m", 
                "wind_gusts_10m", "temperature_80m", "temperature_120m", "temperature_180m", "soil_temperature_0cm", 
                "soil_temperature_6cm", "soil_temperature_18cm", "soil_temperature_54cm", "soil_moisture_0_to_1cm", 
                "soil_moisture_1_to_3cm", "soil_moisture_3_to_9cm", "soil_moisture_9_to_27cm", "soil_moisture_27_to_81cm"]

    hourly_data = {"Flight_DateTime": times,
                   "Airport_Code": airport_codes,
                   "Latitude": latitudes,
                   "Longitude": longitudes}

    for var in variables:
        hourly_data[var] = []

    # Les paramètres de la requête API

    timezones = ["GMT" for i in range(len(times))]

    # TODO: réduire la taille des lat & log pour pouvoir envoyer plus de coordonnées
    page_length = 50 # Nombre maximum de coordonnées qu'on peut donner avant d'atteindre la taille limite de l'URL
    page_nb = len(times) // page_length + 1

    for page in range(page_nb):

        page_start = page * page_length
        page_end = (page + 1) * page_length
        logger.debug(f"{page_start = } - {page_end = }")

        latitudes_page = latitudes[page_start:page_end]
        longitudes_page = longitudes[page_start:page_end]
        timezones_page = timezones[page_start:page_end]
        times_page = times[page_start:page_end]

        params = {"latitude": latitudes_page,
                "longitude": longitudes_page,
                "hourly": ",".join(variables),
                "timezone": timezones_page,
                "start_hour": times_page,
                "end_hour": times_page}
        
        try:
            responses = openmeteo.weather_api(URL, params=params)
        except Exception as e:
            logger.error(f"Error in open-meteo API query: {e}")
            if isinstance(e, OpenMeteoRequestsError):
                str_err = str(e).replace("'", '"').replace("True", "true").replace("False", "false")
                error_reason = json.loads(str_err)["reason"]    
                if error_reason == "Minutely API request limit exceeded. Please try again in one minute.":
                    logger.info("Minutely API request limit exceeded, sleep for one minute.")
                    time.sleep(60)
                    responses = openmeteo.weather_api(URL, params=params)
                elif error_reason == "Hourly API request limit exceeded. Please try again in the next hour.":
                    logger.info("Minutely API request limit exceeded, sleep for one minute.")
                    time.sleep(3600)
                    responses = openmeteo.weather_api(URL, params=params)
                else:
                    raise e
            else:
                raise e


        logger.debug(f"{len(times_page) = } vs. {len(responses) = }")

        for response in responses:
            hourly = response.Hourly()

            for j, var in enumerate(variables):
                hourly_data[var].append(hourly.Variables(j).ValuesAsNumpy().item())
    
    hourly_dataframe = pd.DataFrame(data=hourly_data)
    return hourly_dataframe 

# TODO : date : scheduled-arrival-date, airportcode : arrival
def predict_delay(input_date: str, input_airportcode: str, airport_df: pd.DataFrame = None):
    
    if len(input_airportcode) != 3:
        raise ValueError("Attention, le code aéroport doit contenir 3 caractères.")
    
    if airport_df is None:
        airport_df = pd.read_csv("/app/clean_data/airport_names.csv")
    
    model_path = "/app/clean_data/best_model.pickle"
    model = load(model_path)
    
    input_date = pd.to_datetime(input_date).floor('h').tz_localize(None)
    weather_df = get_weather_data([input_airportcode], [input_date], airport_df)
    ###
    ### REFAIRE LE DF A L'IDENTIQUE QUE POUR LE TRAIN
    ###
    if weather_df.empty:
        raise ValueError(f'Pas de données météo disponibles pour l\'aéroport {input_airportcode}.')
    
    features_predict = weather_df.drop(columns=['Flight_DateTime', 'Latitude', 'Longitude'])
    prediction = model.predict(features_predict)
    return float(prediction[0])
    
    

