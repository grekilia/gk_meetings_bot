import os
from dotenv import load_dotenv

load_dotenv()

# Получаем строку подключения из DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Если есть DATABASE_URL, используем ее
    DB_CONFIG = {
        'dsn': DATABASE_URL
    }
else:
    # Иначе используем отдельные параметры
    DB_CONFIG = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# ID администратора (ваш Telegram ID)
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []
