from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from database import db

# === ГЛАВНОЕ МЕНЮ ===
def get_main_menu(user_role='user'):
    """Главное меню в зависимости от роли пользователя"""
    buttons = [
        [KeyboardButton("➕ Добавить встречу")],
        [KeyboardButton("📋 Просмотреть встречи")]
    ]
    
    if user_role == 'admin':
        buttons.append([KeyboardButton("👥 Управление пользователями")])
        buttons.append([KeyboardButton("📊 Статистика")])
    
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# === КОМПЛЕКСЫ ===
def get_complexes_keyboard():
    """Клавиатура для выбора комплекса"""
    complexes = db.get_complexes()
    keyboard = []
    
    # Разбиваем на ряды по 2 кнопки
    for i in range(0, len(complexes), 2):
        row = []
        for complex in complexes[i:i+2]:
            row.append(InlineKeyboardButton(
                complex['name'], 
                callback_data=f"complex_{complex['id']}"
            ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

# === ОИВ ===
def get_oivs_keyboard(complex_id):
    """Клавиатура для выбора ОИВ в комплексе"""
    oivs = db.get_oivs_by_complex(complex_id)
    keyboard = []
    
    # Разбиваем на ряды по 2 кнопки
    for i in range(0, len(oivs), 2):
        row = []
        for oiv in oivs[i:i+2]:
            row.append(InlineKeyboardButton(
                oiv['name'], 
                callback_data=f"oiv_{oiv['id']}"
            ))
        keyboard.append(row)
    
    # Кнопка "Назад к комплексам"
    keyboard.append([InlineKeyboardButton("⬅️ Назад к комплексам", callback_data="back_to_complexes")])
    
    return InlineKeyboardMarkup(keyboard)

# === СТАТУС ВСТРЕЧИ ===
def get_status_keyboard():
    """Клавиатура для выбора статуса встречи"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Состоялась", callback_data="status_Состоялась"),
            InlineKeyboardButton("⏰ Запланирована", callback_data="status_Запланирована")
        ],
        [
            InlineKeyboardButton("❌ Отменена", callback_data="status_Отменена"),
            InlineKeyboardButton("↗️ Перенесена", callback_data="status_Перенесена")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ПОДТВЕРЖДЕНИЕ ===
def get_confirmation_keyboard():
    """Клавиатура подтверждения"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, сохранить", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data="confirm_no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ГОДА ===
def get_years_keyboard():
    """Клавиатура с годами для просмотра встреч"""
    years = db.get_meeting_years()
    keyboard = []
    
    if not years:
        return None
    
    # Разбиваем на ряды по 3 кнопки
    for i in range(0, len(years), 3):
        row = []
        for year in years[i:i+3]:
            row.append(InlineKeyboardButton(
                str(int(year)), 
                callback_data=f"year_{int(year)}"
            ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

# === МЕСЯЦЫ ===
def get_months_keyboard(year):
    """Клавиатура с месяцами для выбранного года"""
    months = db.get_meeting_months(year)
    month_names = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    
    keyboard = []
    row = []
    for month_num in months:
        row.append(InlineKeyboardButton(
            month_names[month_num],
            callback_data=f"month_{year}_{month_num}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Кнопка "Назад к годам"
    keyboard.append([InlineKeyboardButton("⬅️ Назад к годам", callback_data="back_to_years")])
    
    return InlineKeyboardMarkup(keyboard)

# === ВСТРЕЧИ ЗА МЕСЯЦ ===
def get_meetings_keyboard(meetings, page=0, meetings_per_page=10):
    """Клавиатура со списком встреч"""
    start_idx = page * meetings_per_page
    end_idx = start_idx + meetings_per_page
    page_meetings = meetings[start_idx:end_idx]
    
    keyboard = []
    for meeting in page_meetings:
        # Форматируем дату для отображения
        meeting_date = meeting['meeting_date'].strftime('%d.%m.%Y')
        button_text = f"{meeting_date} - {meeting['oiv_name']}"
        
        # Обрезаем если слишком длинное
        if len(button_text) > 35:
            button_text = button_text[:32] + "..."
        
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f"meeting_{meeting['id']}"
        )])
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"prev_page_{page-1}"))
    
    if end_idx < len(meetings):
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"next_page_{page}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопка "Назад к месяцам"
    keyboard.append([InlineKeyboardButton("⬅️ Назад к месяцам", callback_data="back_to_months")])
    
    return InlineKeyboardMarkup(keyboard)

# === ДЕТАЛИ ВСТРЕЧИ (для пользователя) ===
def get_meeting_details_keyboard(meeting_id, user_role='user'):
    """Клавиатура для просмотра деталей встречи"""
    keyboard = []
    
    if user_role == 'admin':
        keyboard.append([
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{meeting_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{meeting_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_meetings")])
    
    return InlineKeyboardMarkup(keyboard)

# === РЕДАКТИРОВАНИЕ ВСТРЕЧИ ===
def get_edit_meeting_keyboard(meeting_id):
    """Клавиатура для выбора поля редактирования"""
    keyboard = [
        [
            InlineKeyboardButton("📅 Дата", callback_data=f"edit_field_{meeting_id}_date"),
            InlineKeyboardButton("🏛️ ОИВ", callback_data=f"edit_field_{meeting_id}_oiv")
        ],
        [
            InlineKeyboardButton("📊 Статус", callback_data=f"edit_field_{meeting_id}_status"),
            InlineKeyboardButton("⏱️ Длительность", callback_data=f"edit_field_{meeting_id}_duration")
        ],
        [
            InlineKeyboardButton("📝 Содержание", callback_data=f"edit_field_{meeting_id}_summary")
        ],
        [
            InlineKeyboardButton("❌ Отменить редактирование", callback_data=f"cancel_edit_{meeting_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ===
def get_delete_confirmation_keyboard(meeting_id):
    """Клавиатура подтверждения удаления"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_confirm_{meeting_id}"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data=f"delete_cancel_{meeting_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# === УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (админ) ===
def get_users_admin_keyboard():
    """Клавиатура для управления пользователями"""
    keyboard = [
        [
            InlineKeyboardButton("👥 Список пользователей", callback_data="admin_list_users"),
            InlineKeyboardButton("➕ Добавить пользователя", callback_data="admin_add_user")
        ],
        [
            InlineKeyboardButton("❌ Удалить пользователя", callback_data="admin_delete_user")
        ],
        [
            InlineKeyboardButton("⬅️ В главное меню", callback_data="admin_back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# === КАЛЕНДАРЬ (упрощенный) ===
def get_calendar_keyboard(year=None, month=None):
    """Упрощенная клавиатура-календарь"""
    import datetime
    
    if year is None or month is None:
        now = datetime.datetime.now()
        year = now.year
        month = now.month
    
    # Заголовок с месяцем и годом
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Определяем первый день месяца и количество дней
    first_day = datetime.date(year, month, 1)
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    
    days_in_month = (next_month - first_day).days
    
    # Создаем клавиатуру
    keyboard = []
    
    # Заголовок
    keyboard.append([
        InlineKeyboardButton(
            f"{month_names[month-1]} {year}",
            callback_data="calendar_header"
        )
    ])
    
    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([
        InlineKeyboardButton(day, callback_data="ignore") for day in week_days
    ])
    
    # Дни месяца
    day_buttons = []
    # Пустые кнопки для дней до первого дня месяца
    first_weekday = first_day.weekday()  # 0=понедельник, 6=воскресенье
    for _ in range(first_weekday):
        day_buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
    
    # Кнопки с днями
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        day_buttons.append(InlineKeyboardButton(
            str(day), 
            callback_data=f"calendar_day_{date_str}"
        ))
        
        if len(day_buttons) == 7:
            keyboard.append(day_buttons)
            day_buttons = []
    
    if day_buttons:
        # Добиваем последнюю строку пустыми кнопками
        while len(day_buttons) < 7:
            day_buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
        keyboard.append(day_buttons)
    
    # Кнопки навигации по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    nav_row = [
        InlineKeyboardButton(
            "⬅️", 
            callback_data=f"calendar_nav_{prev_year}_{prev_month}"
        ),
        InlineKeyboardButton("Сегодня", callback_data="calendar_today"),
        InlineKeyboardButton(
            "➡️", 
            callback_data=f"calendar_nav_{next_year}_{next_month}"
        )
    ]
    keyboard.append(nav_row)
    
    # Кнопка отмены
    keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="calendar_cancel")])
    
    return InlineKeyboardMarkup(keyboard)
