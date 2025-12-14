import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Используем http://backend:8000 (имя сервиса в docker-compose)
# Если не работает - используем localhost:8005
API_BASE_URL = os.getenv("API_BASE_URL") or "http://backend:8000"
