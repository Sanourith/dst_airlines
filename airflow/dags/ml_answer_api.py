import requests
from datetime import datetime
import pandas as pd
from joblib import load  # Attention : utilise joblib pour charger un modèle pickled
import logging
import sqlalchemy
from flatten_json import flatten
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup

from flatten_json import flatten
from dst_airlines.data.open_meteo_api_weather_hourly import fetch_weather_data
from dst_airlines import utils

logger = logging.getLogger(__name__)

client_id=os.getenv("CLIENT_ID")
client_secret=os.getenv("CLIENT_SECRET")

## DONNEES TEST :
# airport_code : PRG
# departure_UTC_time : 2024-09-24T20:15Z

def first_task(**kwargs):
    """
    Extracts data from the DAG run configuration (airport code and flight date).

    Args:
        kwargs: Additional keyword arguments passed from the DAG run.

    Returns:
        None: Pushes extracted data to XCom for further tasks.
    """
    print("Extracting data...")
    ti = kwargs['ti']
    conf = kwargs.get('dag_run').conf
    input_airportcode = conf.get('arrival_iata_code')
    input_flightdate = conf.get('scheduled_departure_utc_time')
    ti.xcom_push(key='input_airport_code', value=input_airportcode)
    ti.xcom_push(key='input_flightdate', value=input_flightdate)

def get_coordinates(airport_code: str, airports_df: pd.DataFrame):
    """
    Retrieves the latitude and longitude of a specified airport from the DataFrame.

    Args:
        airport_code (str): The 3-letter IATA airport code.
        airports_df (pd.DataFrame): DataFrame containing airport data.

    Returns:
        Tuple[float, float]: Latitude and longitude of the specified airport.
    """
    airport = airports_df[airports_df['iata_code'] == airport_code]
    if not airport.empty:
        latitude = airport.iloc[0]['latitude_deg']
        longitude = airport.iloc[0]['longitude_deg']
        return latitude, longitude
    else:
        return None, None


def get_weather_data(airports_df: pd.DataFrame = None, **kwargs):
    """
    Fetches weather data for the given airport and flight date using the OpenMeteo API.

    Args:
        airports_df (pd.DataFrame): DataFrame containing airport information. If None, it fetches from the SQL database.
        kwargs: Additional keyword arguments passed from the DAG run.

    Returns:
        pd.DataFrame: Weather data for the specified airport and flight date.
    """
    ti = kwargs['ti']
    input_airportcode = ti.xcom_pull(key='input_airport_code')
    input_flightdate = ti.xcom_pull(key='input_flightdate')   
    
    if airports_df == None:
        sql_user = "root"
        sql_password = "rootpassword123"
        sql_host = "mysql-db"
        sql_port = "3306"
        sql_database = "DST_AIRLINES"

        connection_string = f"mysql+pymysql://{sql_user}:{sql_password}@{sql_host}:{sql_port}/{sql_database}"
        engine = sqlalchemy.create_engine(connection_string)

        airports_df = pd.read_sql_table(table_name="airports", con=engine)
    # airports_df = pd.read_csv("/home/sanou/DST-Airlines/data/4_external/airport_names.csv")
    # input_airportcode = 'PMI'
    # input_flightdate = '2024-10-03T02:45'
    latitude, longitude = get_coordinates(input_airportcode, airports_df) 
    departure_time = datetime.strptime(input_flightdate, "%Y-%m-%dT%H:%MZ")
    formatted_date = departure_time.strftime("%Y-%m-%dT%H:%M")
    logger.info(f"{longitude = } {latitude = } {input_airportcode = } {formatted_date = }")
    weather_df = fetch_weather_data([input_airportcode], [latitude], [longitude], [formatted_date])
    ti.xcom_push(key='weather_data', value=weather_df)
    return weather_df

def fetch_future_flight_data(**kwargs):
    """
    Fetches future flight data from the Lufthansa API for the specified airport and flight date.

    Args:
        kwargs: Additional keyword arguments passed from the DAG run.

    Returns:
        pd.DataFrame: Flight data for the specified route and date.
    """
    ti = kwargs['ti']
    input_airportcode = ti.xcom_pull(key='input_airport_code')
    input_flightdate = ti.xcom_pull(key='input_flightdate')   
    
    # input_airportcode = 'AYT'
    # input_flightdate = '2024-09-29T06:00'

    departure_time = datetime.strptime(input_flightdate, "%Y-%m-%dT%H:%MZ")
    formatted_date = departure_time.strftime("%Y-%m-%d")
    access_token = utils.get_lh_api_token(client_id, client_secret)

    ip = utils.get_public_ip_address()
    departure_airportcode = "FRA"
    arrival_airportcode = input_airportcode
    url = f"https://api.lufthansa.com/v1/operations/flightstatus/route/{departure_airportcode}/{arrival_airportcode}/{formatted_date}"
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
        # input_flightdate += 'Z'
        flights_df = flights_df[flights_df['Departure_ScheduledTimeUTC_DateTime'] == input_flightdate]
        ti.xcom_push(key='flight_data', value=flights_df)
        logger.info(f"{flights_df = }")
        return flights_df
    else:
        raise Exception(f"Error fetching flight data: {response.status_code} - {response.text}")


def predict_delay(**kwargs):
    """
    Predicts the flight delay based on flight data and weather data using a pre-trained model.

    Args:
        kwargs: Additional keyword arguments passed from the DAG run.

    Returns:
        float: The predicted flight delay in minutes.
    """
    ti = kwargs['ti']
    weather_df = pd.DataFrame(ti.xcom_pull(key='weather_data'))
    flights_df = pd.DataFrame(ti.xcom_pull(key='flight_data'))
    for col in flights_df.columns:
        logger.info(col)
    logger.info(f"{flights_df = } {weather_df = }")
    ## traitement
    ## TARGET = ['Delay_minutes']

    col_flights = [
        'Departure_ScheduledTimeLocal_DateTime',
        # 'Departure_ScheduledTimeUTC_DateTime',
        'Departure_ActualTimeLocal_DateTime',
        'Departure_ActualTimeUTC_DateTime',
        # 'Departure_TimeStatus_Code', ##
        'Departure_TimeStatus_Definition',
        'Arrival_ScheduledTimeLocal_DateTime',
        # 'Arrival_ScheduledTimeUTC_DateTime',
        'Arrival_ActualTimeLocal_DateTime',
        'Arrival_ActualTimeUTC_DateTime',
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
    
    cols_to_drop = [col for col in col_flights if col in flights_df.columns]
    logger.info(f"{cols_to_drop = }")
    flights_df = flights_df.drop(cols_to_drop, axis=1)

    ### ETL flights_df
    # Convertir en format datetime avec fuseau horaire (UTC si les données sont en UTC)
    flights_df['Arrival_ScheduledTimeUTC_DateTime'] = pd.to_datetime(flights_df['Arrival_ScheduledTimeUTC_DateTime'], utc=True)
    # Calculer le délai avant toute modification de format de date
    
    # Convertir ensuite les dates au format souhaité YYYY-mm-ddTHH-MM
    flights_df['Arrival_ScheduledTimeUTC_DateTime'] = flights_df['Arrival_ScheduledTimeUTC_DateTime'].dt.strftime('%Y-%m-%dT%H')#-%M')

    ### ETL weather_df
    # Convertir en format datetime et appliquer le fuseau horaire UTC
    weather_df['Flight_DateTime'] = pd.to_datetime(weather_df['Flight_DateTime']).dt.tz_localize('UTC')
    # Convertir au format souhaité YYYY-mm-ddTHH-MM
    weather_df['Flight_DateTime'] = weather_df['Flight_DateTime'].dt.strftime('%Y-%m-%dT%H')#:%MZ')

    flights_df = flights_df.rename(str, axis="columns")
    weather_df = weather_df.rename(str, axis="columns")
    logger.info(f"XZ {flights_df = } {weather_df = }")
    df = pd.merge(flights_df, weather_df,
                    left_on=['Arrival_AirportCode', 'Arrival_ScheduledTimeUTC_DateTime'],
                    right_on=['Airport_Code', 'Flight_DateTime'],
                    how="left")
    logger.info(f"0 - {df = }")
    
    new_cols = [
        # 'Departure_ScheduledTimeUTC_DateTime',
        # 'Departure_TimeStatus_Code',
        # 'Arrival_AirportCode',
        # 'Arrival_ScheduledTimeUTC_DateTime',
        # 'Arrival_ActualTimeUTC_DateTime',
        # 'Arrival_TimeStatus_Code',
        # 'Delay_minutes',
        # 'Flight_DateTime',
        # 'Airport_Code',
        # 'Latitude',
        # 'Longitude',
        'temperature_2m',
        'relative_humidity_2m',
        'dew_point_2m',
        'apparent_temperature',
        'precipitation_probability',
        'precipitation',
        'rain',
        'showers',
        'snowfall',
        'snow_depth',
        'weather_code',
        'pressure_msl',
        'surface_pressure',
        'cloud_cover',
        'cloud_cover_low',
        'cloud_cover_mid',
        'cloud_cover_high',
        'visibility',
        'evapotranspiration',
        'et0_fao_evapotranspiration',
        'vapour_pressure_deficit',
        'wind_speed_10m',
        'wind_speed_80m',
        'wind_speed_120m',
        'wind_speed_180m',
        'wind_direction_10m',
        'wind_direction_80m',
        'wind_direction_120m',
        'wind_direction_180m',
        'wind_gusts_10m',
        'temperature_80m',
        'temperature_120m',
        'temperature_180m',
        'soil_temperature_0cm',
        'soil_temperature_6cm',
        'soil_temperature_18cm',
        'soil_temperature_54cm',
        'soil_moisture_0_to_1cm',
        'soil_moisture_1_to_3cm',
        'soil_moisture_3_to_9cm',
        'soil_moisture_9_to_27cm',
        'soil_moisture_27_to_81cm'
    ]

    new_cols = [col for col in new_cols if col in df.columns]
    # df = df.drop(columns=new_cols_drop, axis=1)
    df = df[new_cols]
    logger.info(f"1 - {df.columns = } {df.info}")
    # df = df.dropna(subset=['temperature_2m'])

    col_cat=df.select_dtypes(exclude='float')
    logger.info(f'\n\n{col_cat = }')
    # df = pd.get_dummies(df)

    model = load('/opt/airflow/best_model.pickle')

    prediction = model.predict(df)[0]
    logger.info(f'{prediction = }')
    ti.xcom_push(key='prediction', value=prediction)

#######  DAG  #######
with DAG(
    dag_id='predict_delay',
    schedule_interval=None, 
    default_args={
        'owner': 'airflow',
        'start_date': days_ago(1),
    },
    tags=['prediction', 'DST_Airlines'],
    catchup=False
) as dag_2:

    with TaskGroup('predict_tasks') as predict_tasks:
        get_conf = PythonOperator(
            task_id='get_API_conf',
            python_callable=first_task,
            # op_kwargs={}
            provide_context=True
        )

        get_weather_task = PythonOperator(
            task_id='get_weather_data',
            python_callable=get_weather_data,
            # op_kwargs={}
            provide_context=True
        )

        get_flight_data = PythonOperator(
            task_id='get_flight_data',
            python_callable=fetch_future_flight_data,
            # op_kwargs={}
            provide_context=True
        )

        get_conf >> [get_weather_task, get_flight_data]
    
    predict_delay_task = PythonOperator(
        task_id='predict_delay',
        python_callable=predict_delay,
        # op_kwargs={}
        provide_context=True
    )

predict_tasks >> predict_delay_task
