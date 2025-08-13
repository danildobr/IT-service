import os 
from dotenv import load_dotenv
load_dotenv()

# Конфигурация
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN = os.getenv('ADMIN')
IT_SPECIALIST = os.getenv('IT_SPECIALIST').split(',')