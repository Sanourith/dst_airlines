import os
import pandas as pd
import sqlalchemy
import logging

from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from joblib import dump

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup

logger = logging.getLogger(__name__)

sql_user = os.getenv("MYSQL_USER")
sql_password = os.getenv("MYSQL_ROOT_PASSWORD")
sql_host = os.getenv("MYSQL_HOST")
sql_port = int(os.getenv("MYSQL_PORT"))
sql_database = os.getenv("MYSQL_DATABASE")

def prepare_data_to_ml():
    """
    Prepares the dataset for machine learning by merging flight and weather data,
    cleaning unnecessary columns, handling missing values, and engineering features.

    Steps Involved:
        - Connects to the MySQL database and retrieves flight and weather data.
        - Drops irrelevant columns from the flight data.
        - Calculates the delay in minutes based on scheduled and actual arrival times.
        - Formats datetime fields for merging.
        - Merges flight data with corresponding weather data.
        - Drops duplicate and rows with missing values.
        - Separates features and target variable for modeling.

    Returns:
        Tuple[pd.DataFrame, pd.Series]: 
            - Features DataFrame containing explanatory variables.
            - Target Series containing the delay in minutes.
    """

    connection_string = f"mysql+pymysql://{sql_user}:{sql_password}@{sql_host}:{sql_port}/{sql_database}"
    engine = sqlalchemy.create_engine(connection_string)

    flights_df = pd.read_sql_table(table_name="flights", con=engine)
    weather_df = pd.read_sql_table(table_name="weather_forecasts", con=engine)

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
        'Arrival_Terminal_Gate',
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

    cols_to_drop = [col for col in cols_to_drop if col in flights_df.columns]
    logger.info(f"{cols_to_drop = }")
    flights_df = flights_df.drop(cols_to_drop, axis=1)
    flights_df = flights_df.dropna(subset=['Arrival_ActualTimeUTC_DateTime'])

    ### ETL flights_df
    # Convertir en format datetime avec fuseau horaire (UTC si les données sont en UTC)
    flights_df['Arrival_ScheduledTimeUTC_DateTime'] = pd.to_datetime(flights_df['Arrival_ScheduledTimeUTC_DateTime'], utc=True)
    flights_df['Arrival_ActualTimeUTC_DateTime'] = pd.to_datetime(flights_df['Arrival_ActualTimeUTC_DateTime'], utc=True)
    # Calculer le délai avant toute modification de format de date
    flights_df['Delay_minutes'] = (flights_df['Arrival_ActualTimeUTC_DateTime'] - flights_df['Arrival_ScheduledTimeUTC_DateTime']).dt.total_seconds() / 60
    # Convertir ensuite les dates au format souhaité YYYY-mm-ddTHH-MM
    flights_df['Arrival_ScheduledTimeUTC_DateTime'] = flights_df['Arrival_ScheduledTimeUTC_DateTime'].dt.strftime('%Y-%m-%dT%H')#-%M')
    flights_df['Arrival_ActualTimeUTC_DateTime'] = flights_df['Arrival_ActualTimeUTC_DateTime'].dt.strftime('%Y-%m-%dT%H')#-%M')

    ### ETL weather_df
    # Convertir en format datetime et appliquer le fuseau horaire UTC
    weather_df['Flight_DateTime'] = pd.to_datetime(weather_df['Flight_DateTime']).dt.tz_localize('UTC')
    # Convertir au format souhaité YYYY-mm-ddTHH-MM
    weather_df['Flight_DateTime'] = weather_df['Flight_DateTime'].dt.strftime('%Y-%m-%dT%H')#:%MZ')

    ### MERGE
    flights_df = flights_df.rename(str, axis="columns")
    weather_df = weather_df.rename(str, axis="columns")
    df = pd.merge(flights_df, weather_df,
                    left_on=['Arrival_AirportCode', 'Arrival_ScheduledTimeUTC_DateTime'],
                    right_on=['Airport_Code', 'Flight_DateTime'],
                    how="left")

    new_cols = [
        # 'Departure_ScheduledTimeUTC_DateTime',
        # 'Departure_TimeStatus_Code',
        # 'Arrival_AirportCode',
        # 'Arrival_ScheduledTimeUTC_DateTime',
        # 'Arrival_ActualTimeUTC_DateTime',
        # 'Arrival_TimeStatus_Code',
        'Delay_minutes',
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
    df = df.drop_duplicates(subset=['Delay_minutes', 'temperature_2m'])
    # df = df.dropna(subset=['temperature_2m'])

    col_cat=df.select_dtypes(exclude='float')
    logger.info(f'\n\n{col_cat = }')
    # df = pd.get_dummies(df)

    df = df.dropna()

    features = df.drop(['Delay_minutes'], axis=1)
    features.columns = features.columns.astype(str)

    target = df['Delay_minutes']
    
    return features, target

def compute_model_score(model, X, y):
    """
    Computes the cross-validated score of a given machine learning model using negative mean squared error.

    Args:
        model (sklearn estimator): The machine learning model to evaluate.
        X (pd.DataFrame): The feature matrix.
        y (pd.Series): The target variable.

    Returns:
        float: The average cross-validated score (negative MSE).
    """
    print(X.head())
    X.to_csv(f'/opt/airflow/X{model}.csv', index=False)
    print("\n\n\n\n")
    print(y.head())
    y.to_csv(f'/opt/airflow/y{model}.csv', index=False)
    cross_validation = cross_val_score(
        model,
        X,
        y,
        cv=3,
        scoring='neg_mean_squared_error')

    model_score = cross_validation.mean()
    return model_score

def train_and_save_model(model, X, y, path_to_model='./app/model.pckl'):
    """
    Trains a machine learning model on the provided data and saves the trained model to a file.

    Args:
        model (sklearn estimator): The machine learning model to train.
        X (pd.DataFrame): The feature matrix.
        y (pd.Series): The target variable.
        path_to_model (str, optional): The file path to save the trained model. Defaults to './app/model.pckl'.
    """
    model.fit(X, y)
    print(str(model), 'saved at ', path_to_model)
    dump(model, path_to_model)

def train_model(model_name, **kwargs):
    """
    Trains a specified machine learning model, evaluates its performance, and saves the trained model.

    Args:
        model_name (str): The name of the model to train. Supported models are:
            - 'LinearRegression'
            - 'DecisionTreeRegressor'
            - 'RandomForestRegressor'
        **kwargs: Additional keyword arguments, including 'ti' for XCom interactions.
    """
    X, y = prepare_data_to_ml()
    
    if model_name == 'LinearRegression':
        model = LinearRegression()
    elif model_name == 'DecisionTreeRegressor':
        model = DecisionTreeRegressor()
    elif model_name == 'RandomForestRegressor':
        model = RandomForestRegressor()
    else:
        raise ValueError(f'Unknown model name: {model_name}')
    
    score = compute_model_score(model, X, y)
    path_to_model = f'/opt/airflow/{model_name}_model.pickle'
    train_and_save_model(model, X, y, path_to_model)
    kwargs['ti'].xcom_push(key=f'{model_name}', value=score)

def select_best_model(**kwargs):
    """
    Selects the best performing machine learning model based on cross-validated scores
    and saves it as the best model.

    Args:
        **kwargs: Additional keyword arguments, including 'ti' for XCom interactions.
    """
    ti = kwargs['ti']
    score_lr = ti.xcom_pull(key='LinearRegression')
    score_dtr = ti.xcom_pull(key='DecisionTreeRegressor')
    score_rfr = ti.xcom_pull(key='RandomForestRegressor')
    
    X, y = prepare_data_to_ml()
    best_score = max(score_lr, score_dtr, score_rfr)
    
    if best_score == score_lr:
        print(f'LinearRegression selected with score : {score_lr}')
        train_and_save_model(
            LinearRegression(),
            X, y,
            '/opt/airflow/best_model.pickle'
        )
    if best_score == score_dtr:
        print(f'DecisionTreeRegressor selected with score : {score_lr}')
        train_and_save_model(
            DecisionTreeRegressor(),
            X, y,
            '/opt/airflow/best_model.pickle'
        )
    else:
        print(f'RandomForestRegressor selected with score : {score_lr}')
        train_and_save_model(
            RandomForestRegressor(),
            X, y,
            '/opt/airflow/best_model.pickle'
        )


with DAG(
    dag_id='model_training_dag',
    schedule_interval=None,
    default_args={
        'owner': 'airflow',
        'start_date': days_ago(1)
    },
    tags=['training', 'regression', 'models'],
    catchup=False,
) as dag_1:
    
    with TaskGroup('training_tasks') as training_tasks:
        train_lr = PythonOperator(
            task_id='train_linear_regression',
            python_callable=train_model,
            op_kwargs={'model_name': 'LinearRegression'}
        )
        
        train_dtr = PythonOperator(
            task_id='train_decision_tree_regressor',
            python_callable=train_model,
            op_kwargs={'model_name': 'DecisionTreeRegressor'}
        )
        
        train_rfr = PythonOperator(
            task_id='train_random_forest_regressor',
            python_callable=train_model,
            op_kwargs={'model_name': 'RandomForestRegressor'}
        )
        
    select_best_model_task = PythonOperator(
        task_id='select_best_model',
        python_callable=select_best_model,
        provide_context=True
    )

training_tasks >> select_best_model_task