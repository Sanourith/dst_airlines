import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
from dst_airlines.database import mysql
from dst_airlines.data.airports import generate_clean_airport_data

main_path = os.path.dirname(os.path.abspath(__file__))

env_file = os.path.join(main_path, "../env/private.env")
load_dotenv(env_file)

sql_user = os.getenv("MYSQL_USER")
sql_password = os.getenv("MYSQL_ROOT_PASSWORD")
sql_host = os.getenv("MYSQL_HOST")
sql_port = int(os.getenv("MYSQL_PORT"))
sql_database = os.getenv("MYSQL_DATABASE")

sql = "mysql+pymysql"
db_url = f"{sql}://{sql_user}:{sql_password}@{sql_host}:{sql_port}/{sql_database}"

root_path = Path(__file__).resolve().parents[1]
airports_data_file = f"{root_path}/data/4_external/airport_names.csv"

logger = logging.getLogger(__name__)


def main():
    # setup_logger()
    engine = create_engine(db_url)
    with engine.connect() as connection:
        result = connection.execute(text(f"SHOW DATABASES LIKE '{sql_database}';"))
        exists = result.fetchone()

        # if not exists, create database :
        if not exists:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {sql_database};"))
            logger.info(f"Database {sql_database} created successfully.")
        else:
            logger.info(f"Database {sql_database} already exists.")

    logger.info("Starting to collect & structure airports_data from csv...")
    airports_df = generate_clean_airport_data(airports_data_file)

    table_name = "airports"

    logger.info(f"Starting the insertion of airports into MySQL table: {table_name}.")
    mysql.upload_data_in_mysql(
        data=airports_df,
        sql_database=sql_database,
        table=table_name,
        sql_user=sql_user,
        sql_password=sql_password,
        sql_host=sql_host,
        sql_port=sql_port,
    )
    logger.info(f"Insertion of the airports data into {table_name} finalized.")


if __name__ == "__main__":
    main()
