import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")
COMPANY_ID = int(os.getenv("COMPANY_ID", 1))
