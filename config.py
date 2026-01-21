import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация базы данных
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# ID администратора (ваш Telegram ID)
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []

# Строка подключения для SQLAlchemy (если понадобится)
DATABASE_URL = os.getenv('DATABASE_URL')
