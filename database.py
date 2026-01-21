import psycopg
from psycopg.rows import dict_row
from config import DB_CONFIG
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Установка соединения с базой данных"""
        try:
            if 'dsn' in DB_CONFIG:
                # Используем строку подключения
                self.conn = psycopg.connect(DB_CONFIG['dsn'])
            else:
                # Используем отдельные параметры
                self.conn = psycopg.connect(**DB_CONFIG)
            
            self.conn.autocommit = False
            print("Подключение к базе данных установлено")
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            raise
    
    def get_cursor(self):
        """Получение курсора с поддержкой именованных параметров"""
        return self.conn.cursor(row_factory=dict_row)
    
    # === ПОЛЬЗОВАТЕЛИ ===
    def add_user(self, telegram_id, full_name, role='user'):
        """Добавление нового пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (telegram_id, full_name, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id) DO NOTHING
                RETURNING id
            """, (telegram_id, full_name, role))
            return cursor.fetchone()
    
    def get_user(self, telegram_id):
        """Получение пользователя по Telegram ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
            return cursor.fetchone()
    
    def get_all_users(self):
        """Получение всех пользователей"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users ORDER BY id")
            return cursor.fetchall()
    
    def delete_user(self, telegram_id):
        """Удаление пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE telegram_id = %s", (telegram_id,))
            self.conn.commit()
            return cursor.rowcount > 0
    
    # === КОМПЛЕКСЫ И ОИВ ===
    def get_complexes(self):
        """Получение списка всех комплексов"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM complexes ORDER BY id")
            return cursor.fetchall()
    
    def get_oivs_by_complex(self, complex_id):
        """Получение ОИВ по ID комплекса"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM oivs WHERE complex_id = %s ORDER BY name", (complex_id,))
            return cursor.fetchall()
    
    def get_oiv(self, oiv_id):
        """Получение ОИВ по ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM oivs WHERE id = %s", (oiv_id,))
            return cursor.fetchone()
    
    def get_all_oivs(self):
        """Получение всех ОИВ с комплексами"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT o.*, c.name as complex_name 
                FROM oivs o 
                JOIN complexes c ON o.complex_id = c.id 
                ORDER BY c.id, o.name
            """)
            return cursor.fetchall()
    
    # === ВСТРЕЧИ ===
    def add_meeting(self, user_id, user_name, oiv_id, meeting_date, status, duration_minutes, summary):
        """Добавление новой встречи"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO meetings 
                (user_id, user_name, oiv_id, meeting_date, status, duration_minutes, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, user_name, oiv_id, meeting_date, status, duration_minutes, summary))
            self.conn.commit()
            result = cursor.fetchone()
            return result['id'] if result else None
    
    def get_meeting(self, meeting_id):
        """Получение встречи по ID с полной информацией"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT m.*, o.name as oiv_name, c.name as complex_name
                FROM meetings m
                JOIN oivs o ON m.oiv_id = o.id
                JOIN complexes c ON o.complex_id = c.id
                WHERE m.id = %s
            """, (meeting_id,))
            return cursor.fetchone()
    
    def get_user_meetings(self, user_id):
        """Получение всех встреч пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT m.*, o.name as oiv_name, c.name as complex_name
                FROM meetings m
                JOIN oivs o ON m.oiv_id = o.id
                JOIN complexes c ON o.complex_id = c.id
                WHERE m.user_id = %s
                ORDER BY m.meeting_date DESC, m.created_at DESC
            """, (user_id,))
            return cursor.fetchall()
    
    def get_all_meetings(self, filters=None):
        """Получение всех встреч с фильтрами"""
        query = """
            SELECT m.*, o.name as oiv_name, c.name as complex_name
            FROM meetings m
            JOIN oivs o ON m.oiv_id = o.id
            JOIN complexes c ON o.complex_id = c.id
            WHERE 1=1
        """
        params = []
        
        if filters:
            if filters.get('year'):
                query += " AND EXTRACT(YEAR FROM m.meeting_date) = %s"
                params.append(filters['year'])
            if filters.get('month'):
                query += " AND EXTRACT(MONTH FROM m.meeting_date) = %s"
                params.append(filters['month'])
            if filters.get('complex_id'):
                query += " AND c.id = %s"
                params.append(filters['complex_id'])
            if filters.get('oiv_id'):
                query += " AND o.id = %s"
                params.append(filters['oiv_id'])
            if filters.get('status'):
                query += " AND m.status = %s"
                params.append(filters['status'])
        
        query += " ORDER BY m.meeting_date DESC, m.created_at DESC"
        
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_meeting_years(self):
        """Получение списка годов, в которые были встречи"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT EXTRACT(YEAR FROM meeting_date) as year
                FROM meetings 
                ORDER BY year DESC
            """)
            results = cursor.fetchall()
            return [int(row['year']) for row in results if row['year']]
    
    def get_meeting_months(self, year):
        """Получение списка месяцев с встречами для указанного года"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT EXTRACT(MONTH FROM meeting_date) as month
                FROM meetings 
                WHERE EXTRACT(YEAR FROM meeting_date) = %s
                ORDER BY month DESC
            """, (year,))
            results = cursor.fetchall()
            return [int(row['month']) for row in results if row['month']]
    
    def update_meeting(self, meeting_id, **fields):
        """Обновление данных встречи"""
        if not fields:
            return False
        
        set_clause = ", ".join([f"{key} = %s" for key in fields.keys()])
        values = list(fields.values())
        values.append(meeting_id)
        
        with self.get_cursor() as cursor:
            cursor.execute(f"""
                UPDATE meetings 
                SET {set_clause}
                WHERE id = %s
            """, values)
            self.conn.commit()
            return cursor.rowcount > 0
    
    def delete_meeting(self, meeting_id):
        """Удаление встречи"""
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM meetings WHERE id = %s", (meeting_id,))
            self.conn.commit()
            return cursor.rowcount > 0
    
    # === СТАТИСТИКА ===
    def get_statistics(self, start_date=None, end_date=None):
        """Получение статистики по встречам"""
        query = """
            SELECT 
                c.name as complex_name,
                o.name as oiv_name,
                m.status,
                COUNT(*) as count
            FROM meetings m
            JOIN oivs o ON m.oiv_id = o.id
            JOIN complexes c ON o.complex_id = c.id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND m.meeting_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND m.meeting_date <= %s"
            params.append(end_date)
        
        query += """
            GROUP BY c.name, o.name, m.status
            ORDER BY c.name, o.name, m.status
        """
        
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            print("Соединение с базой данных закрыто")

# Глобальный экземпляр базы данных
db = Database()
