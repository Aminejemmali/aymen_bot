import os
import logging
from dotenv import load_dotenv

class Config:
    """Configuration class for environment variables and constants"""
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
    DB_FILE = "users.db"

    # Logging setup
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
    logger = logging.getLogger(__name__)

    @classmethod
    def log(cls, level, message):
        """Log messages with specified level"""
        if level == "info":
            cls.logger.info(message)
        elif level == "error":
            cls.logger.error(message)
        elif level == "warning":
            cls.logger.warning(message)