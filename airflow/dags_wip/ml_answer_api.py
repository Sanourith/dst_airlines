import os
import requests
from datetime import datetime
import pandas as pd
from joblib import load  # Attention : utilise joblib pour charger un modèle pickled
import openmeteo_requests
import requests_cache
from retry_requests import retry
from typing import List
import logging
import time
import re
from typing import List, Dict
from openmeteo_requests.Client import OpenMeteoRequestsError
import pymysql
import sqlalchemy
from flatten_json import flatten
import json
   
from sklearn.impute import SimpleImputer
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from joblib import dump

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup

from dst_airlines.data.open_meteo_api_weather_hourly import fetch_weather_data
from dst_airlines import utils

utils.setup_logging()

## DONNEES TEST :
# airport_code : PRG
# departure_UTC_time : 2024-09-24T20:15Z

def first_task(**kwargs):
    print("Extracting data...")
    conf = kwargs.get('dag_run').conf
    input_airportcode = conf.get('arrival_iata_code')
    input_flightdate = conf.get('scheduled_departure_utc_time')
    return [input_airportcode, input_flightdate]

def get_coordinates(airport_code: str, airports_df: pd.DataFrame):
    ''' Get latitude, longitude from airports_df with flights_df AirportCode
    
    Args :
    airport_code (str) : 3 letters to indicate which Airport is chosen
    airports_df (df) : /home/sanou/DST-Airlines/data/4_external/airport_names.csv
    
    Returns :
    latitude (float) : latitude of the Airport
    longitude (float) : longitude of the Airport
    '''
    airport = airports_df[airports_df['iata_code'] == airport_code]
    if not airport.empty:
        latitude = airport.iloc[0]['latitude_deg']
        longitude = airport.iloc[0]['longitude_deg']
        return latitude, longitude
    else:
        return None, None


def get_weather_data(airports_df: pd.DataFrame = None, **kwargs):
    ti = kwargs['ti']    
    input_airportcode = ti.xcom_pull(key='input_airportcode')
    input_flightdate = ti.xcom_pull(key='input_flightdate')
    
    if airports_df == None:
        sql_user = "root"
        sql_password = "password"
        sql_host = "mysql-db"
        sql_port = "3306"
        sql_database = "DST_AIRLINES"

        connection_string = f"mysql+pymysql://{sql_user}:{sql_password}@{sql_host}:{sql_port}/{sql_database}"
        engine = sqlalchemy.create_engine(connection_string)

        airports_df = pd.read_sql_table(table_name="airports", con=engine)
    
    # TEST EN LOCAL
    # airports_df = pd.read_csv("/home/sanou/DST-Airlines/data/4_external/airport_names.csv")
    # input_airportcode = 'AYT'
    # input_flightdate = '2024-09-29T06:00'
    latitude, longitude = get_coordinates(input_airportcode, airports_df) 
    weather_df = fetch_weather_data([input_airportcode], [latitude], [longitude], [input_flightdate])
    
    return weather_df


# curl "https://api.lufthansa.com/v1/oauth/token" -X POST -d "client_id=wd4b8gk6uu2psa6ywp65s8m7b" -d "client_secret=PjFqxXDe9R" -d "grant_type=client_credentials"
def fetch_future_flight_data(**kwargs):
    ti = kwargs['ti']
    input_airportcode = ti.xcom_pull(key='input_airportcode')
    input_flightdate = ti.xcom_pull(key='input_flightdate')
    
    # TEST LOCAL
    # input_airportcode = 'AYT'
    # input_flightdate = '2024-09-29T06:00'

    departure_time = datetime.strptime(input_flightdate, '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d')
    client_id="wd4b8gk6uu2psa6ywp65s8m7b"
    client_secret="PjFqxXDe9R"
    access_token = utils.get_lh_api_token(client_id, client_secret)

    ip = utils.get_public_ip_address()
    departure_airportcode = "FRA"
    arrival_airportcode = input_airportcode
    url = f"https://api.lufthansa.com/v1/operations/flightstatus/route/{departure_airportcode}/{arrival_airportcode}/{departure_time}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-originating-IP': ip
    }

    # Effectuer la requête GET à l'API Lufthansa
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        flights_data = response.json()
        flights_data = flights_data['FlightStatusResource']['Flights']['Flight']
        flights_df = pd.DataFrame([flatten(d) for d in flights_data])
        input_flightdate += 'Z'
        flights_df = flights_df[flights_df['Departure_ScheduledTimeUTC_DateTime'] == input_flightdate]
        ti.xcom_push(key='weather_data', value=flights_df)
        return flights_df
    else:
        raise Exception(f"Error fetching flight data: {response.status_code} - {response.text}")

flights_df = fetch_future_flight_data()

def predict_delay(flights_df, weather_df, **kwargs):
    ti = kwargs['ti']
    weather_df = ti.xcom_pull(key='weather_data') 
    flights_df = ti.xcom_pull(key='flight_data')
 
    ## traitement
    ## TARGET = ['Delay_minutes']
    
    cols_to_drop = [
        'Departure_ScheduledTimeLocal_DateTime',
        # 'Departure_ScheduledTimeUTC_DateTime',
        'Departure_ActualTimeLocal_DateTime',
        'Departure_ActualTimeUTC_DateTime',
        # 'Departure_TimeStatus_Code', ##
        'Departure_TimeStatus_Definition',
        'Arrival_ScheduledTimeLocal_DateTime',
        # 'Arrival_ScheduledTimeUTC_DateTime',
        'Arrival_ActualTimeLocal_DateTime',
        # 'Arrival_ActualTimeUTC_DateTime',
        'Arrival_EstimatedTimeLocal_DateTime',
        'Arrival_EstimatedTimeUTC_DateTime',
        # 'Departure_EstimatedTimeLocal_DateTime', ##
        # 'Departure_EstimatedTimeUTC_DateTime', ##
        # 'Flight_DateTime',
        # 'Flight_DateTime_Hour',
        'Departure_Terminal_Name',
        'Departure_Terminal_Gate',
        'Arrival_Terminal_Name',
        # 'Arrival_Terminal_Gate', ##
        'ServiceType',
        'Departure_AirportCode',
        # 'Arrival_AirportCode',
        'MarketingCarrier_AirlineID',
        'MarketingCarrier_FlightNumber',
        'OperatingCarrier_AirlineID',
        'OperatingCarrier_FlightNumber',
        'Equipment_AircraftCode',
        'Equipment_AircraftRegistration',
        'FlightStatus_Code',
        # 'Airport_Code',
        # 'Latitude',
        # 'Longitude',
        # Valeurs status = inutiles car nous cherchons à déterminer le retard, chiffré
        'FlightStatus_Definition',
        'Arrival_TimeStatus_Definition',
        'FlightStatus_Definition'
    ]

    flights_df = flights_df.drop(cols_to_drop, axis=1)
    flights_df = flights_df.dropna(subset=['Arrival_ActualTimeUTC_DateTime'])

    ### ETL flights_df
    # Convertir en format datetime avec fuseau horaire (UTC si les données sont en UTC)
    flights_df['Arrival_ScheduledTimeUTC_DateTime'] = pd.to_datetime(flights_df['Arrival_ScheduledTimeUTC_DateTime'], utc=True)
    flights_df['Arrival_ActualTimeUTC_DateTime'] = pd.to_datetime(flights_df['Arrival_ActualTimeUTC_DateTime'], utc=True)
    # Calculer le délai avant toute modification de format de date

    # flights_df['Delay_minutes'] = (flights_df['Arrival_ActualTimeUTC_DateTime'] - flights_df['Arrival_ScheduledTimeUTC_DateTime']).dt.total_seconds() / 60
    
    
    # Convertir ensuite les dates au format souhaité YYYY-mm-ddTHH-MM
    flights_df['Arrival_ScheduledTimeUTC_DateTime'] = flights_df['Arrival_ScheduledTimeUTC_DateTime'].dt.strftime('%Y-%m-%dT%H')#-%M')
    flights_df['Arrival_ActualTimeUTC_DateTime'] = flights_df['Arrival_ActualTimeUTC_DateTime'].dt.strftime('%Y-%m-%dT%H')#-%M')

    ### ETL weather_df
    # Convertir en format datetime et appliquer le fuseau horaire UTC
    weather_df['Flight_DateTime'] = pd.to_datetime(weather_df['Flight_DateTime']).dt.tz_localize('UTC')
    # Convertir au format souhaité YYYY-mm-ddTHH-MM
    weather_df['Flight_DateTime'] = weather_df['Flight_DateTime'].dt.strftime('%Y-%m-%dT%H')#:%MZ')

    flights_df = flights_df.rename(str, axis="columns")
    weather_df = weather_df.rename(str, axis="columns")
    df = pd.merge(flights_df, weather_df,
                    left_on=['Arrival_AirportCode', 'Arrival_ScheduledTimeUTC_DateTime'],
                    right_on=['Airport_Code', 'Flight_DateTime'],
                    how="left")
    new_cols_drop = [
            'Departure_ScheduledTimeUTC_DateTime',
            'Departure_TimeStatus_Code',
            'Arrival_AirportCode',
            'Arrival_ScheduledTimeUTC_DateTime',
            'Arrival_ActualTimeUTC_DateTime',
            'Arrival_TimeStatus_Code',
            # 'Delay_minutes',
            'Flight_DateTime',
            'Airport_Code',
            'Latitude',
            'Longitude',
            # 'temperature_2m',
            # 'relative_humidity_2m',
            # 'dew_point_2m',
            # 'apparent_temperature',
            # 'precipitation_probability',
            # 'precipitation',
            # 'rain',
            # 'showers',
            # 'snowfall',
            # 'snow_depth',
            # 'weather_code',
            # 'pressure_msl',
            # 'surface_pressure',
            # 'cloud_cover',
            # 'cloud_cover_low',
            # 'cloud_cover_mid',
            # 'cloud_cover_high',
            # 'visibility',
            # 'evapotranspiration',
            # 'et0_fao_evapotranspiration',
            # 'vapour_pressure_deficit',
            # 'wind_speed_10m',
            # 'wind_speed_80m',
            # 'wind_speed_120m',
            # 'wind_speed_180m',
            # 'wind_direction_10m',
            # 'wind_direction_80m',
            # 'wind_direction_120m',
            # 'wind_direction_180m',
            # 'wind_gusts_10m',
            # 'temperature_80m',
            # 'temperature_120m',
            # 'temperature_180m',
            # 'soil_temperature_0cm',
            # 'soil_temperature_6cm',
            # 'soil_temperature_18cm',
            # 'soil_temperature_54cm',
            # 'soil_moisture_0_to_1cm',
            # 'soil_moisture_1_to_3cm',
            # 'soil_moisture_3_to_9cm',
            # 'soil_moisture_9_to_27cm',
            # 'soil_moisture_27_to_81cm'
        ]


    df = df.drop(columns=new_cols_drop, axis=1)
    # df = df.dropna()
    
    # Encodage des variables catégorielles
    df = pd.get_dummies(df)

    model = load('/home/sanou/DST-Airlines/airflow/clean_data/best_model.pickle')

    prediction = model.predict(df)
    ti.xcom_push(key='prediction', value=prediction)
    return float(prediction[0])

## DAGs :

with DAG(
    dag_id="answer_api",
    schedule_interval=None,
    default_args={
        'owner': 'airflow',
        'start_date': days_ago(1),
    },
    tags=['prediction', 'regression', 'models'],
    catchup=False
) as dag:

    with TaskGroup('get_data') as get_data_group:
        first_task_first = PythonOperator(
            task_id='recup_config_API',
            python_callable=first_task,
            provide_context=True
        )

        get_weather_data_task = PythonOperator(
            task_id='get_weather_data',
            python_callable=get_weather_data,
            provide_context=True
        )

        get_future_flight_data_task = PythonOperator(
            task_id='get_flight_data',
            python_callable=fetch_future_flight_data,
            provide_context=True
        )

        first_task_first >> (get_weather_data_task, get_future_flight_data_task)

    predict_delay_task = PythonOperator(
        task_id='predict_delay',
        python_callable=predict_delay,
        provide_context=True
    )

get_data_group >> predict_delay_task
