from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from logging import getLogger
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

logger = getLogger(__name__)


def get_mysql_engine(
    sql_user: str,
    sql_password: str,
    sql_host: str,
    sql_port: str,
    sql_database: str,
) -> Engine:
    """Return a SQLAlchemy engine to connect to MySQL."""
    connection_string = (
        f"mysql+pymysql://{sql_user}:{sql_password}@{sql_host}:{sql_port}/{sql_database}"
    )
    return create_engine(connection_string)


def upload_data_in_mysql(
    data: pd.DataFrame,
    table: str,
    sql_user: str,
    sql_password: str,
    sql_host: str = "localhost",
    sql_port: str = "3306",
    sql_database: str = "DST_AIRLINES",
    if_exists: str = "append",
) -> None:
    """Upload provided data into the named table from the MySQL database."""
    try:
        # Create connection to MySQL
        engine = get_mysql_engine(sql_user, sql_password, sql_host, sql_port, sql_database)

        # Inspect the database to get table names
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        if table in table_names:
            logger.info(f"{table} found in {sql_database}, appending new rows.")

            # Read existing data to compare with
            existing_data = pd.read_sql(f"SELECT * FROM {table}", con=engine)

            # Avoid inserting duplicates
            new_data = data.merge(existing_data, on=list(data.columns), how="left", indicator=True)
            new_data = new_data[new_data["_merge"] == "left_only"].drop(columns=["_merge"])

            if new_data.empty:
                logger.info(f"No new rows to insert into {table}. Skipping.")
                return

            # Insert new data
            new_data.to_sql(name=table, con=engine, if_exists=if_exists, index=False)
            logger.info(f"{new_data.shape[0]} new rows inserted into {table}.")

        else:
            # Create table and insert data if table doesn't exist
            logger.info(f"{table} not found in {sql_database}, creating, inserting.")
            data.to_sql(name=table, con=engine, if_exists=if_exists, index=False)
            logger.info(f"{data.shape[0]} rows inserted into new table {table}.")

    except SQLAlchemyError as e:
        logger.error(f"Error occurred while uploading data to {table}: {e}")
