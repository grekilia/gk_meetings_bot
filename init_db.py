#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных.
Заполняет справочники complexes и oivs данными.
"""

import psycopg  # Изменено
from psycopg.rows import dict_row
from config import DB_CONFIG

# Данные комплексов и ОИВ (из вашего списка)
COMPLEXES_OIVS = {
    "1. Градостроительство и имущество": [
        "ДГП",
        "ДГС", 
        "ДСТиИИ",
        "ДГИ",
        "МГЭ"
    ],
    "2. Транспорт и промышленность": [
        "Дептранс",
        "МАДИ",
        "ДИиПП"
    ],
    "3. Городское хозяйство, ГО и борьба с ЧС": [
        "ДКР",
        "ДЖКХ",
        "ГОЧСиПБ",
        "МЖИ"
    ],
    "4. Социальное развитие": [
        "ДЗМ",
        "ДОНМ",
        "ДТСЗН",
        "МФЦ",
        "КГУ",
        "Москомвет",
        "УЗАГС",
        "Главархив",
        "МосГИК"
    ],
    "5. Региональная безопасность и информационная политика": [
        "Москомспорт",
        "ДРБиПК",
        "ДСМИР",
        "ДВиМС",
        "ДНПиМС",
        "ДОДМС"
    ],
    "6. Аппарат Мэра и Правительства Москвы": [
        "УДМПМ/АМПМ",
        "Депкульт",
        "ДТУ",
        "ДПиИР",
        "ДИТ",
        "ДКН",
        "ДТОИВ",
        "Мостуризм",
        "КОСиМП"
    ],
    "7. Экономическая политика и развитие": [
        "ДЭПиР",
        "Тендерный комитет"
    ],
    "8. Контрольный комплекс": [
        "Главконтроль",
        "ОАТИ",
        "ДПиООС",
        "МГСН",
        "ГИН"
    ],
    "9. Департамент финансов": [
        "Депфин"
    ]
}

def init_database():
    """Инициализация базы данных"""
    print("Инициализация базы данных...")
    
    try:
        # Подключаемся к базе данных
        if 'dsn' in DB_CONFIG:
            conn = psycopg.connect(DB_CONFIG['dsn'])
        else:
            conn = psycopg.connect(**DB_CONFIG)
        
        cursor = conn.cursor(row_factory=dict_row)
        
        # Создаем таблицы (если их нет)
        print("Создание таблиц...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL UNIQUE,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complexes (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oivs (
                id SERIAL PRIMARY KEY,
                complex_id INTEGER NOT NULL REFERENCES complexes(id),
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                user_name TEXT,
                oiv_id INTEGER NOT NULL REFERENCES oivs(id),
                meeting_date DATE NOT NULL,
                status TEXT NOT NULL,
                duration_minutes INTEGER,
                summary TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("Таблицы созданы успешно.")
        
        # Заполняем справочник комплексов
        print("Заполнение справочника комплексов...")
        
        for complex_name in COMPLEXES_OIVS.keys():
            cursor.execute(
                "INSERT INTO complexes (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (complex_name,)
            )
        
        conn.commit()
        print("Комплексы добавлены.")
        
        # Заполняем справочник ОИВ
        print("Заполнение справочника ОИВ...")
        
        for complex_name, oiv_list in COMPLEXES_OIVS.items():
            # Получаем ID комплекса
            cursor.execute("SELECT id FROM complexes WHERE name = %s", (complex_name,))
            result = cursor.fetchone()
            
            if result:
                complex_id = result['id']
                
                # Добавляем ОИВ этого комплекса
                for oiv_name in oiv_list:
                    cursor.execute(
                        "INSERT INTO oivs (complex_id, name) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                        (complex_id, oiv_name)
                    )
        
        conn.commit()
        print("ОИВ добавлены.")
        
        # Добавляем администратора (вас) если еще нет
        print("Добавление администратора...")
        
        # Ваш Telegram ID нужно будет указать в переменных окружения
        from config import ADMIN_IDS
        
        if ADMIN_IDS:
            admin_id = ADMIN_IDS[0]  # Берем первого администратора из списка
            
            cursor.execute("""
                INSERT INTO users (telegram_id, full_name, role) 
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE 
                SET role = EXCLUDED.role
            """, (admin_id, "Администратор", "admin"))
            
            conn.commit()
            print(f"Администратор с ID {admin_id} добавлен.")
        
        print("\n✅ Инициализация базы данных завершена успешно!")
        print(f"Добавлено комплексов: {len(COMPLEXES_OIVS)}")
        
        # Подсчет ОИВ
        total_oivs = sum(len(oiv_list) for oiv_list in COMPLEXES_OIVS.values())
        print(f"Добавлено ОИВ: {total_oivs}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации базы данных: {e}")
        raise

if __name__ == '__main__':
    init_database()
