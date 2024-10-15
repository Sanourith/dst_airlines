from .. import utils
from logging import getLogger
import pandas as pd

logger = getLogger(__name__)


def generate_clean_airport_data(airport_file_path: str=None) -> pd.DataFrame:
    """Generate clean airport data from the provided file path 
    (if no file path is provided, the function will load the file from the standard location (in data/4_external))

    Args:
        airport_file_path (str, optional): Path to get the Airport data. Defaults to None.

    Returns:
        pd.DataFrame: Cleaned dataframe containing airport data (only unique, non empty, iata are kept, LAX name is properly added)
    """
    if not airport_file_path:
        airport_file_path = utils.build_data_storage_path(file_name="airport_names.csv", data_stage="external")

    airport_df = pd.read_csv(airport_file_path)

    ## Nettoyage des iata_code pour qu'ils soient uniques (clé primaire)
    # Suppression des valeurs vides
    airport_df = airport_df.dropna(subset=["iata_code"])
    
    # Correction d'un iata_code dont le nom est manquant
    airport_df.loc[airport_df["iata_code"] == "LAX", "name"] = "Los Angeles International Airport"
    
    # Suppression des duplicatas (aucun n'est gardé)
    airport_df = airport_df.drop_duplicates(subset=["iata_code"], keep=False)

    logger.info(f"Airport dataframe properly generated from {airport_file_path = }.")

    return airport_df