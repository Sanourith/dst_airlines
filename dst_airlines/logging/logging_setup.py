import json
import logging.config
import logging.handlers
import pathlib
import os
import sys


logger = logging.getLogger(__name__)  # __name__ is a common choice (refers to the module name)


def setup_logging():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = pathlib.Path(f"{script_dir}/config_log.json")
    logs_dir = os.path.join(script_dir, os.pardir, os.pardir, 'logs')
    
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        log_dir_created = True
    else:
        log_dir_created = False
    
    
    with open(config_file) as f_in:
        config = json.load(f_in)
        config["handlers"]["file_json"]["filename"] = f'{logs_dir}/{config["handlers"]["file_json"]["filename"]}'
    logging.config.dictConfig(config)

    logger.info(f"Création d'un nouveau dossier dédié aux logs à l'endroit suivant : {logs_dir}") if log_dir_created else None


def main():
    # Testing of the logging functionalities
    setup_logging()
    logging.basicConfig(level="INFO")
    logger.debug("debug message", extra={"x": "hello"})
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("exception message")


if __name__ == "__main__":
    main()

# Il est nécessaire d'ajouter le chemin du dossier dans les variables d'environnement 
# pour que le custom formatter "MyJSONFormatter" de "mylogger.py", utilisé dans config_setup.py
# pour configurer le logger soit reconnu
if __name__ != "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)