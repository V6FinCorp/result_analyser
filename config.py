import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')
    DB_TABLE = os.getenv('DB_TABLE', 'TB_QUARTERLY_ANALYSIS_GPT_TST')

    # Scaling Factor: Values in PDF are in Lakhs, Table expects Crores
    # 1 Crore = 100 Lakhs
    LAKHS_TO_CRORES = 0.01

config = Config()
