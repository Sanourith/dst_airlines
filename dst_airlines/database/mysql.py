from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from logging import getLogger
import pandas as pd


logger = getLogger(__name__)


def get_mysql_engine(
    sql_user: str,
    sql_password: str,
    sql_host: str,
    sql_port: str,
    sql_database: str,
) -> Engine:
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
    """Upload provided data into the named table from the MySQL database whose detailed
    are provided,
    will either add new data into the table if it exists or create the table and insert
    data into it if it does not already exist

    Args:
        data (pd.DataFrame): Data to be inserted into the MySQL table
        table (str): Name of the MySQL table
        sql_user (str): Username to be used to connect to the MySQL database
        sql_password (str): Password
        if_exists (str, optional): Method to use if the table already exists, see
            `DataFrame.to_sql()` for more details. Defaults to "append".
        sql_host (str, optional): MySQL host to use to connect. Defaults to "localhost".
        sql_port (str, optional): MySQL port to use to connect. Defaults to "3306".
        sql_database (str, optional): MySQL database name to which to connect.
            Defaults to "DST_AIRLINES".
    """
    # Création de la connexion avec la base de données MySQL
    engine = get_mysql_engine(sql_user, sql_password, sql_host, sql_port, sql_database)

    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if table in table_names:
        logger.info(f"{table = } found in the {sql_database = }, appending new rows.")

        existing_data = pd.read_sql(f"SELECT * FROM {table}", con=engine)

        # Comparaison pour ne pas insérer de doublons
        new_data = data.merge(existing_data, on=list(data.columns), how="left", indicator=True)
        new_data = new_data[new_data["_merge"] == "left_only"].drop(columns=["_merge"])

        if new_data.empty:
            logger.info(f"No new rows to insert into {table}. Skipping.")
            return

        new_data.to_sql(name=table, con=engine, if_exists=if_exists, index=False)
        logger.info(f"{new_data.shape[0]} new rows inserted into {table}.")

    else:
        logger.info(f"{table = } not found in {sql_database = }, creating, inserting.")
        data.to_sql(name=table, con=engine, if_exists=if_exists, index=False)
        logger.info(f"{data.shape[0]} rows inserted into new table {table}.")
