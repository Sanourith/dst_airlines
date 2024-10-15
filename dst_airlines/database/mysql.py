from sqlalchemy import create_engine, inspect
from logging import getLogger
import pandas as pd


logger = getLogger(__name__)


def upload_data_in_mysql(data: pd.DataFrame, table: str, sql_user: str, sql_password: str, if_exists: str="append", sql_host: str="localhost", sql_port: str="3306", sql_database: str="DST_AIRLINES") -> None:
    """Upload provided data into the named table from the MySQL database whose detailed are provided, 
    will either add new data into the table if it exists or create the table and insert data into it if it does not already exist

    Args:
        data (pd.DataFrame): Data to be inserted into the MySQL table
        table (str): Name of the MySQL table
        sql_user (str): Username to be used to connect to the MySQL database
        sql_password (str): Password
        if_exists (str, optional): Method to use if the table already exists, see `DataFrame.to_sql()` for more details. Defaults to "append".
        sql_host (str, optional): MySQL host to use to connect. Defaults to "localhost".
        sql_port (str, optional): MySQL port to use to connect. Defaults to "3306".
        sql_database (str, optional): MySQL database name to which to connect. Defaults to "DST_AIRLINES".
    """
    # Création de la connexion avec la base de données MySQL
    connection_string = f"mysql+pymysql://{sql_user}:{sql_password}@{sql_host}:{sql_port}/{sql_database}"
    engine = create_engine(connection_string)

    # Récupération du nom des tables, s'il y en a
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    # Si la table existe, ajout des nouvelles lignes uniquement, sinon création de la table et ajout des données
    if table in table_names:
        logger.info(f"{table = } is found in the {sql_database = }, appending new rows only into the table.")

        # Récupération des données existantes
        existing_data = pd.read_sql(f"SELECT * FROM {table}", con=engine)
        
        # Sélection des nouvelles données à ajouter uniquement
        new_data = data.merge(existing_data, on=list(data.columns), how='left', indicator=True)
        new_data = new_data[new_data['_merge'] == 'left_only'].drop(columns=['_merge'])

        new_data_row_number = new_data.shape[0]

        # Insertion des données à la base MySQL
        number_rows_appended = new_data.to_sql(name=table, con=engine, if_exists=if_exists, index=False)

        logger.info(f"New rows inserted in the {table = }, ({number_rows_appended = } vs. {new_data_row_number = }).")
        
    else:
        logger.info(f"{table = } not found in the {sql_database = }, creating the table and inserting data into it.")

        # Création de la table et insertion des données
        number_rows_appended = data.to_sql(name=table, con=engine, if_exists=if_exists, index=False)
        data_row_number = data.shape[0]

        logger.info(f"{table = } created and row inserted, ({number_rows_appended = } vs. {data_row_number = }).")