import logging

# Initialiser le logger une seule fois
logging.basicConfig(
    filename="coucou_main_log.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Créer un logger accessible depuis d'autres modules
logger = logging.getLogger("coucou")


def get_logger():
    return logger
