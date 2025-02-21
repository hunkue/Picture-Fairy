import os
from logger import logger
from dotenv import load_dotenv

load_dotenv()

# 檢查環境變數
required_env_vars = [
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_CHANNEL_SECRET",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_API_VERSION",
    "GOOGLE_API_KEY",
    "CSE_ID",
    "GOOGLE_SEARCH_API_URL",
]


def check_env_variables():
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(
                f"Enviroment variable {var} is not set. Please check your .env file."
            )
            raise EnvironmentError(
                f"Enviroment variable {var} is not set. Please check your .env file."
            )

check_env_variables()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("CSE_ID")
GOOGLE_SEARCH_API_URL = os.getenv("GOOGLE_SEARCH_API_URL")