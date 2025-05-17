from pathlib import Path
from . import utils
from logging import getLogger

logger = getLogger(__name__)

# Load environment variables 
utils.load_env_variables()

# Paths
PROJ_ROOT = Path(__file__).resolve().parents[1]
logger.info(f"Le chemin PROJ_ROOT est : {PROJ_ROOT}")

# DATA_DIR = PROJ_ROOT / "data"
# RAW_DATA_DIR = DATA_DIR / "raw"
# INTERIM_DATA_DIR = DATA_DIR / "interim"
# PROCESSED_DATA_DIR = DATA_DIR / "processed"
# EXTERNAL_DATA_DIR = DATA_DIR / "external"

# MODELS_DIR = PROJ_ROOT / "models"

# REPORTS_DIR = PROJ_ROOT / "reports"
# FIGURES_DIR = REPORTS_DIR / "figures"
