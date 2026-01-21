import logging
from datetime import datetime, date
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from config import BOT_TOKEN, ADMIN_IDS
from database import db
from keyboards import *
from states import *

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные для хранения данных во время диалога
user_data = {}

# === КОМАНДА /START ===
async def start(update: Update, context):
    """Обработка команды /start"""
    user = update.effective_user
    telegram_id = user.id
    
    # Проверяем, есть ли пользователь в базе
    db_user = db.get_user(telegram_id)
    
    if not db_user:
        # Если пользователя нет в базе
        await update.message.reply_text(
            "⛔ Доступ запрещен.\n\n"
            "Вы не зарегистрированы в системе. "
            "Обратитесь к администратору для получения доступа."
        )
        return
    
    # Пользователь найден, приветствуем
    welcome_text = f"👋 Привет, {user.full_name}!\n\n"
    
    if db_user['role'] == 'admin':
        welcome_text += "Вы вошли как **администратор**.\n"
        welcome_text += "Доступные функции:\n"
        welcome_text += "• Добавление встреч\n"
        welcome_text += "• Просмотр всех встреч\n"
        welcome_text += "• Редактирование и удаление встреч\n"
        welcome_text += "• Управление пользователями\n"
        welcome_text += "• Просмотр статистики\n"
    else:
        welcome_text += "Вы вошли как **пользователь**.\n"
        welcome_text += "Доступные функции:\n"
        welcome_text += "• Добавление встреч\n"
        welcome_text += "• Просмотр всех встреч (только чтение)\n"
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(db_user['role']),
        parse_mode='Markdown'
    )
    
    # Сохраняем роль пользователя в context
    context.user_data['role'] = db_user['role']

# === ДОБАВЛЕНИЕ ВСТРЕЧИ ===
async def add_meeting_start(update: Update, context):
    """Начало процесса добавления встречи"""
    user = update.effective_user
    
    # Проверяем, может ли пользователь добавлять встречи
    if 'role' not in context.user_data:
        await update.message.reply_text(
            "Сначала выполните команду /start",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END
    
    # Инициализируем данные встречи
    context.user_data['new_meeting'] = {
        'user_id': user.id,
        'user_name': user.full_name
    }
    
    # Показываем выбор комплекса
    await update.message.reply_text(
        "🏛️ *Выберите комплекс:*",
        reply_markup=get_complexes_keyboard(),
        parse_mode='Markdown'
    )
    
    return SELECT_COMPLEX

async def select_complex(update: Update, context):
    """Обработка выбора комплекса"""
    query = update.callback_query
    await query.answer()
    
    complex_id = int(query.data.split('_')[1])
    context.user_data['new_meeting']['complex_id'] = complex_id
    
    # Показываем ОИВ выбранного комплекса
    await query.edit_message_text(
        "🏢 *Выберите ОИВ:*",
        reply_markup=get_oivs_keyboard(complex_id),
        parse_mode='Markdown'
    )
    
    return SELECT_OIV

async def select_oiv(update: Update, context):
    """Обработка выбора ОИВ"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back_to_complexes':
        # Возврат к выбору комплекса
        await query.edit_message_text(
            "🏛️ *Выберите комплекс:*",
            reply_markup=get_complexes_keyboard(),
            parse_mode='Markdown'
        )
        return SELECT_COMPLEX
    
    oiv_id = int(query.data.split('_')[1])
    context.user_data['new_meeting']['oiv_id'] = oiv_id
    
    # Показываем календарь для выбора даты
    await query.edit_message_text(
        "📅 *Выберите дату встречи:*\n\n"
        "Используйте календарь ниже для выбора даты.",
        reply_markup=get_calendar_keyboard(),
        parse_mode='Markdown'
    )
    
    return SELECT_DATE

async def select_date(update: Update, context):
    """Обработка выбора даты из календаря"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'calendar_cancel':
        # Отмена выбора даты
        await query.edit_message_text(
            "❌ Выбор даты отменен.\n\n"
            "🏛️ *Выберите комплекс:*",
            reply_markup=get_complexes_keyboard(),
            parse_mode='Markdown'
        )
        return SELECT_COMPLEX
    
    if query.data == 'calendar_today':
        # Выбор сегодняшней даты
        today = datetime.now().date()
        context.user_data['new_meeting']['meeting_date'] = today
        date_str = today.strftime('%d.%m.%Y')
    elif query.data.startswith('calendar_day_'):
        # Выбор конкретного дня
        date_str = query.data.split('_')[2]
        meeting_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        context.user_data['new_meeting']['meeting_date'] = meeting_date
        date_str = meeting_date.strftime('%d.%m.%Y')
    elif query.data.startswith('calendar_nav_'):
        # Навигация по месяцам
        _, _, year, month = query.data.split('_')
        await query.edit_message_text(
            "📅 *Выберите дату встречи:*",
            reply_markup=get_calendar_keyboard(int(year), int(month)),
            parse_mode='Markdown'
        )
        return SELECT_DATE
    else:
        # Игнорируем другие callback_data
        return SELECT_DATE
    
    # После выбора даты переходим к выбору статуса
    await query.edit_message_text(
        f"📅 *Дата встречи:* {date_str}\n\n"
        "📊 *Выберите статус встречи:*",
        reply_markup=get_status_keyboard(),
        parse_mode='Markdown'
    )
    
    return SELECT_STATUS

async def select_status(update: Update, context):
    """Обработка выбора статуса встречи"""
    query = update.callback_query
    await query.answer()
    
    status = query.data.split('_')[1]
    context.user_data['new_meeting']['status'] = status
    
    # Запрашиваем длительность встречи (только для состоявшихся встреч)
    if status == 'Состоялась':
        await query.edit_message_text(
            f"📊 *Статус:* {status}\n\n"
            "⏱️ *Введите длительность встречи в минутах:*\n"
            "(только цифры, например: 60)",
            parse_mode='Markdown'
        )
        return INPUT_DURATION
    else:
        # Для других статусов длительность не требуется
        context.user_data['new_meeting']['duration_minutes'] = None
        await query.edit_message_text(
            f"📊 *Статус:* {status}\n\n"
            "📝 *Введите краткое содержание встречи:*\n"
            "(опишите ключевые моменты, договоренности)",
            parse_mode='Markdown'
        )
        return INPUT_SUMMARY

async def input_duration(update: Update, context):
    """Обработка ввода длительности"""
    if update.message:
        text = update.message.text
        
        # Проверяем, что введено число
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Пожалуйста, введите только цифры.\n"
                "Введите длительность встречи в минутах:"
            )
            return INPUT_DURATION
        
        duration = int(text)
        context.user_data['new_meeting']['duration_minutes'] = duration
        
        await update.message.reply_text(
            f"⏱️ *Длительность:* {duration} минут\n\n"
            "📝 *Введите краткое содержание встречи:*\n"
            "(опишите ключевые моменты, договоренности)",
            parse_mode='Markdown'
        )
        
        return INPUT_SUMMARY

async def input_summary(update: Update, context):
    """Обработка ввода краткого содержания"""
    if update.message:
        summary = update.message.text
        
        if len(summary.strip()) < 5:
            await update.message.reply_text(
                "❌ Слишком короткое описание. "
                "Пожалуйста, введите более подробное содержание:"
            )
            return INPUT_SUMMARY
        
        context.user_data['new_meeting']['summary'] = summary
        
        # Формируем сводку для подтверждения
        meeting_data = context.user_data['new_meeting']
        
        # Получаем информацию об ОИВ и комплексе
        oiv = db.get_oiv(meeting_data['oiv_id'])
        complexes = db.get_complexes()
        complex_name = next((c['name'] for c in complexes if c['id'] == meeting_data['complex_id']), "Неизвестно")
        
        # Форматируем дату
        date_str = meeting_data['meeting_date'].strftime('%d.%m.%Y')
        
        # Формируем текст сводки
        summary_text = (
            "📋 *Сводка встречи:*\n\n"
            f"🏛️ *Комплекс:* {complex_name}\n"
            f"🏢 *ОИВ:* {oiv['name']}\n"
            f"📅 *Дата:* {date_str}\n"
            f"📊 *Статус:* {meeting_data['status']}\n"
        )
        
        if meeting_data.get('duration_minutes'):
            summary_text += f"⏱️ *Длительность:* {meeting_data['duration_minutes']} мин\n"
        
        summary_text += f"📝 *Содержание:* {meeting_data['summary'][:200]}"
        if len(meeting_data['summary']) > 200:
            summary_text += "..."
        
        summary_text += "\n\n✅ *Всё верно?*"
        
        await update.message.reply_text(
            summary_text,
            reply_markup=get_confirmation_keyboard(),
            parse_mode='Markdown'
        )
        
        return CONFIRM_MEETING

async def confirm_meeting(update: Update, context):
    """Обработка подтверждения встречи"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'confirm_no':
        # Отмена создания встречи
        await query.edit_message_text(
            "❌ Создание встречи отменено.\n\n"
            "Вы можете начать заново, выбрав '➕ Добавить встречу' в главном меню."
        )
        
        # Очищаем данные
        if 'new_meeting' in context.user_data:
            del context.user_data['new_meeting']
        
        return ConversationHandler.END
    
    elif query.data == 'confirm_yes':
        # Сохранение встречи в БД
        meeting_data = context.user_data['new_meeting']
        
        try:
            meeting_id = db.add_meeting(
                user_id=meeting_data['user_id'],
                user_name=meeting_data['user_name'],
                oiv_id=meeting_data['oiv_id'],
                meeting_date=meeting_data['meeting_date'],
                status=meeting_data['status'],
                duration_minutes=meeting_data.get('duration_minutes'),
                summary=meeting_data['summary']
            )
            
            # Форматируем дату для ответа
            date_str = meeting_data['meeting_date'].strftime('%d.%m.%Y')
            
            await query.edit_message_text(
                f"✅ Встреча успешно сохранена!\n\n"
                f"📅 *Дата:* {date_str}\n"
                f"📊 *Статус:* {meeting_data['status']}\n"
                f"🆔 *ID записи:* {meeting_id}\n\n"
                "Вы можете добавить новую встречу или просмотреть существующие."
            )
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении встречи: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при сохранении встречи.\n"
                "Пожалуйста, попробуйте снова."
            )
        
        # Очищаем данные
        if 'new_meeting' in context.user_data:
            del context.user_data['new_meeting']
        
        return ConversationHandler.END

# === ПРОСМОТР ВСТРЕЧ ===
async def view_meetings_start(update: Update, context):
    """Начало просмотра встреч"""
    # Проверяем, есть ли встречи
    meetings = db.get_all_meetings()
    
    if not meetings:
        await update.message.reply_text(
            "📭 Встреч пока нет.\n"
            "Вы можете добавить первую встречу."
        )
        return
    
    # Получаем список годов с встречами
    years = db.get_meeting_years()
    
    if not years:
        await update.message.reply_text(
            "📭 Встреч пока нет.\n"
            "Вы можете добавить первую встречу."
        )
        return
    
    await update.message.reply_text(
        "📅 *Выберите год для просмотра встреч:*",
        reply_markup=get_years_keyboard(),
        parse_mode='Markdown'
    )

async def view_meetings_callback(update: Update, context):
    """Обработка callback при просмотре встреч"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('year_'):
        # Выбор года
        year = int(data.split('_')[1])
        context.user_data['view_year'] = year
        
        await query.edit_message_text(
            f"📅 *Год:* {year}\n\n"
            "*Выберите месяц:*",
            reply_markup=get_months_keyboard(year),
            parse_mode='Markdown'
        )
    
    elif data.startswith('month_'):
        # Выбор месяца
        _, year, month = data.split('_')
        year = int(year)
        month = int(month)
        
        # Получаем встречи за выбранный месяц
        meetings = db.get_all_meetings({'year': year, 'month': month})
        
        if not meetings:
            await query.edit_message_text(
                f"📭 За {month}/{year} встреч нет.\n\n"
                "Выберите другой месяц:",
                reply_markup=get_months_keyboard(year)
            )
            return
        
        # Сохраняем фильтры в context
        context.user_data['view_filters'] = {'year': year, 'month': month}
        context.user_data['view_meetings'] = meetings
        context.user_data['view_page'] = 0
        
        month_names = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        
        await query.edit_message_text(
            f"📅 *{month_names[month-1]} {year}*\n"
            f"📋 *Найдено встреч:* {len(meetings)}\n\n"
            "*Выберите встречу для просмотра деталей:*",
            reply_markup=get_meetings_keyboard(meetings, page=0),
            parse_mode='Markdown'
        )
    
    elif data.startswith('meeting_'):
        # Просмотр деталей встречи
        meeting_id = int(data.split('_')[1])
        meeting = db.get_meeting(meeting_id)
        
        if not meeting:
            await query.edit_message_text("❌ Встреча не найдена.")
            return
        
        # Форматируем дату
        date_str = meeting['meeting_date'].strftime('%d.%m.%Y')
        
        # Формируем текст встречи
        status_icons = {
            'Состоялась': '✅',
            'Запланирована': '⏰',
            'Отменена': '❌',
            'Перенесена': '↗️'
        }
        
        status_icon = status_icons.get(meeting['status'], '📊')
        
        meeting_text = (
            f"{status_icon} *Встреча #{meeting['id']}*\n\n"
            f"🏛️ *Комплекс:* {meeting['complex_name']}\n"
            f"🏢 *ОИВ:* {meeting['oiv_name']}\n"
            f"📅 *Дата:* {date_str}\n"
            f"📊 *Статус:* {meeting['status']}\n"
        )
        
        if meeting['duration_minutes']:
            meeting_text += f"⏱️ *Длительность:* {meeting['duration_minutes']} мин\n"
        
        meeting_text += f"👤 *Добавил:* {meeting['user_name']}\n"
        meeting_text += f"📝 *Содержание:*\n{meeting['summary']}"
        
        # Получаем роль пользователя
        user_role = context.user_data.get('role', 'user')
        
        await query.edit_message_text(
            meeting_text,
            reply_markup=get_meeting_details_keyboard(meeting_id, user_role),
            parse_mode='Markdown'
        )
    
    elif data.startswith('prev_page_') or data.startswith('next_page_'):
        # Навигация по страницам
        meetings = context.user_data.get('view_meetings', [])
        
        if not meetings:
            await query.answer("Нет данных для отображения")
            return
        
        if data.startswith('prev_page_'):
            page = int(data.split('_')[2])
        else:  # next_page_
            page = int(data.split('_')[2]) + 1
        
        context.user_data['view_page'] = page
        
        filters = context.user_data.get('view_filters', {})
        year = filters.get('year', '')
        month = filters.get('month', '')
        
        month_names = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        month_name = month_names[month-1] if month else ""
        
        await query.edit_message_text(
            f"📅 *{month_name} {year}*\n"
            f"📋 *Найдено встреч:* {len(meetings)}\n\n"
            "*Выберите встречу для просмотра деталей:*",
            reply_markup=get_meetings_keyboard(meetings, page=page),
            parse_mode='Markdown'
        )
    
    elif data == 'back_to_years':
        # Возврат к выбору года
        await query.edit_message_text(
            "📅 *Выберите год для просмотра встреч:*",
            reply_markup=get_years_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == 'back_to_months':
        # Возврат к выбору месяца
        year = context.user_data.get('view_year')
        if year:
            await query.edit_message_text(
                f"📅 *Год:* {year}\n\n"
                "*Выберите месяц:*",
                reply_markup=get_months_keyboard(year),
                parse_mode='Markdown'
            )
    
    elif data == 'back_to_meetings':
        # Возврат к списку встреч
        meetings = context.user_data.get('view_meetings', [])
        page = context.user_data.get('view_page', 0)
        
        if meetings:
            filters = context.user_data.get('view_filters', {})
            year = filters.get('year', '')
            month = filters.get('month', '')
            
            month_names = [
                "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
            ]
            month_name = month_names[month-1] if month else ""
            
            await query.edit_message_text(
                f"📅 *{month_name} {year}*\n"
                f"📋 *Найдено встреч:* {len(meetings)}\n\n"
                "*Выберите встречу для просмотра деталей:*",
                reply_markup=get_meetings_keyboard(meetings, page=page),
                parse_mode='Markdown'
            )

# === РЕДАКТИРОВАНИЕ ВСТРЕЧ (только для админа) ===
async def edit_meeting_start(update: Update, context):
    """Начало редактирования встречи"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем права (должен быть админом)
    if context.user_data.get('role') != 'admin':
        await query.edit_message_text(
            "⛔ У вас нет прав для редактирования встреч."
        )
        return
    
    meeting_id = int(query.data.split('_')[1])
    meeting = db.get_meeting(meeting_id)
    
    if not meeting:
        await query.edit_message_text("❌ Встреча не найдена.")
        return
    
    # Сохраняем ID встречи для редактирования
    context.user_data['editing_meeting_id'] = meeting_id
    
    await query.edit_message_text(
        f"✏️ *Редактирование встречи #{meeting_id}*\n\n"
        "Выберите поле для редактирования:",
        reply_markup=get_edit_meeting_keyboard(meeting_id),
        parse_mode='Markdown'
    )
    
    return EDIT_MEETING_FIELD

async def edit_meeting_field(update: Update, context):
    """Выбор поля для редактирования"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('cancel_edit_'):
        # Отмена редактирования
        meeting_id = int(query.data.split('_')[2])
        meeting = db.get_meeting(meeting_id)
        
        # Показываем детали встречи снова
        date_str = meeting['meeting_date'].strftime('%d.%m.%Y')
        
        meeting_text = (
            f"✅ *Встреча #{meeting['id']}*\n\n"
            f"🏛️ *Комплекс:* {meeting['complex_name']}\n"
            f"🏢 *ОИВ:* {meeting['oiv_name']}\n"
            f"📅 *Дата:* {date_str}\n"
            f"📊 *Статус:* {meeting['status']}\n"
        )
        
        if meeting['duration_minutes']:
            meeting_text += f"⏱️ *Длительность:* {meeting['duration_minutes']} мин\n"
        
        meeting_text += f"👤 *Добавил:* {meeting['user_name']}\n"
        meeting_text += f"📝 *Содержание:*\n{meeting['summary']}"
        
        await query.edit_message_text(
            meeting_text,
            reply_markup=get_meeting_details_keyboard(meeting_id, 'admin'),
            parse_mode='Markdown'
        )
        
        # Очищаем данные редактирования
        if 'editing_meeting_id' in context.user_data:
            del context.user_data['editing_meeting_id']
        if 'editing_field' in context.user_data:
            del context.user_data['editing_field']
        
        return ConversationHandler.END
    
    # Определяем какое поле редактируем
    parts = query.data.split('_')
    meeting_id = int(parts[3])
    field = parts[4]
    
    # Сохраняем информацию о редактируемом поле
    context.user_data['editing_field'] = field
    context.user_data['editing_meeting_id'] = meeting_id
    
    meeting = db.get_meeting(meeting_id)
    
    if field == 'date':
        await query.edit_message_text(
            f"✏️ *Редактирование даты встречи #{meeting_id}*\n\n"
            "Текущая дата: " + meeting['meeting_date'].strftime('%d.%m.%Y') + "\n\n"
            "Выберите новую дату:",
            reply_markup=get_calendar_keyboard(),
            parse_mode='Markdown'
        )
        return EDIT_MEETING_FIELD
    
    elif field == 'oiv':
        await query.edit_message_text(
            f"✏️ *Редактирование ОИВ встречи #{meeting_id}*\n\n"
            f"Текущий ОИВ: {meeting['oiv_name']}\n\n"
            "Выберите новый комплекс:",
            reply_markup=get_complexes_keyboard(),
            parse_mode='Markdown'
        )
        return EDIT_MEETING_FIELD
    
    elif field == 'status':
        await query.edit_message_text(
            f"✏️ *Редактирование статуса встречи #{meeting_id}*\n\n"
            f"Текущий статус: {meeting['status']}\n\n"
            "Выберите новый статус:",
            reply_markup=get_status_keyboard(),
            parse_mode='Markdown'
        )
        return EDIT_MEETING_FIELD
    
    elif field == 'duration':
        current_duration = meeting['duration_minutes'] or "не указана"
        await query.edit_message_text(
            f"✏️ *Редактирование длительности встречи #{meeting_id}*\n\n"
            f"Текущая длительность: {current_duration} мин\n\n"
            "Введите новую длительность в минутах (только цифры):"
        )
        return EDIT_MEETING_FIELD
    
    elif field == 'summary':
        await query.edit_message_text(
            f"✏️ *Редактирование содержания встречи #{meeting_id}*\n\n"
            f"Текущее содержание:\n{meeting['summary']}\n\n"
            "Введите новое содержание:"
        )
        return EDIT_MEETING_FIELD

async def edit_meeting_input(update: Update, context):
    """Обработка ввода новых данных для поля"""
    if update.message:
        text = update.message.text
        meeting_id = context.user_data.get('editing_meeting_id')
        field = context.user_data.get('editing_field')
        
        if not meeting_id or not field:
            await update.message.reply_text("Ошибка: данные редактирования не найдены.")
            return ConversationHandler.END
        
        meeting = db.get_meeting(meeting_id)
        
        if field == 'duration':
            # Проверяем, что введено число
            if not text.isdigit():
                await update.message.reply_text(
                    "❌ Пожалуйста, введите только цифры.\n"
                    "Введите длительность в минутах:"
                )
                return EDIT_MEETING_FIELD
            
            duration = int(text)
            db.update_meeting(meeting_id, duration_minutes=duration)
            
            await update.message.reply_text(
                f"✅ Длительность обновлена: {duration} мин\n\n"
                f"Продолжайте редактирование или вернитесь к просмотру встречи.",
                reply_markup=get_edit_meeting_keyboard(meeting_id)
            )
            
            # Очищаем поле редактирования
            del context.user_data['editing_field']
            return EDIT_MEETING_FIELD
        
        elif field == 'summary':
            if len(text.strip()) < 5:
                await update.message.reply_text(
                    "❌ Слишком короткое описание. "
                    "Пожалуйста, введите более подробное содержание:"
                )
                return EDIT_MEETING_FIELD
            
            db.update_meeting(meeting_id, summary=text)
            
            await update.message.reply_text(
                f"✅ Содержание обновлено.\n\n"
                f"Продолжайте редактирование или вернитесь к просмотру встречи.",
                reply_markup=get_edit_meeting_keyboard(meeting_id)
            )
            
            # Очищаем поле редактирования
            del context.user_data['editing_field']
            return EDIT_MEETING_FIELD

async def edit_meeting_callback(update: Update, context):
    """Обработка callback при редактировании (дата, ОИВ, статус)"""
    query = update.callback_query
    await query.answer()
    
    meeting_id = context.user_data.get('editing_meeting_id')
    field = context.user_data.get('editing_field')
    
    if not meeting_id or not field:
        await query.edit_message_text("Ошибка: данные редактирования не найдены.")
        return ConversationHandler.END
    
    if field == 'date':
        if query.data == 'calendar_cancel':
            # Отмена редактирования даты
            await query.edit_message_text(
                "❌ Редактирование даты отменено.",
                reply_markup=get_edit_meeting_keyboard(meeting_id)
            )
            del context.user_data['editing_field']
            return EDIT_MEETING_FIELD
        
        elif query.data.startswith('calendar_day_'):
            # Выбор новой даты
            date_str = query.data.split('_')[2]
            new_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            db.update_meeting(meeting_id, meeting_date=new_date)
            
            await query.edit_message_text(
                f"✅ Дата обновлена: {new_date.strftime('%d.%m.%Y')}\n\n"
                f"Продолжайте редактирование или вернитесь к просмотру встречи.",
                reply_markup=get_edit_meeting_keyboard(meeting_id)
            )
            
            del context.user_data['editing_field']
            return EDIT_MEETING_FIELD
        
        elif query.data.startswith('calendar_nav_'):
            # Навигация по календарю
            _, _, year, month = query.data.split('_')
            await query.edit_message_text(
                f"✏️ *Редактирование даты встречи #{meeting_id}*\n\n"
                "Выберите новую дату:",
                reply_markup=get_calendar_keyboard(int(year), int(month)),
                parse_mode='Markdown'
            )
            return EDIT_MEETING_FIELD
    
    elif field == 'oiv':
        if query.data == 'back_to_complexes':
            # Возврат к выбору комплекса
            await query.edit_message_text(
                f"✏️ *Редактирование ОИВ встречи #{meeting_id}*\n\n"
                "Выберите новый комплекс:",
                reply_markup=get_complexes_keyboard(),
                parse_mode='Markdown'
            )
            return EDIT_MEETING_FIELD
        
        elif query.data.startswith('complex_'):
            # Выбор комплекса
            complex_id = int(query.data.split('_')[1])
            context.user_data['editing_complex_id'] = complex_id
            
            await query.edit_message_text(
                f"✏️ *Редактирование ОИВ встречи #{meeting_id}*\n\n"
                "Выберите новый ОИВ:",
                reply_markup=get_oivs_keyboard(complex_id),
                parse_mode='Markdown'
            )
            return EDIT_MEETING_FIELD
        
        elif query.data.startswith('oiv_'):
            # Выбор ОИВ
            oiv_id = int(query.data.split('_')[1])
            
            db.update_meeting(meeting_id, oiv_id=oiv_id)
            
            # Получаем имя ОИВ для отображения
            oiv = db.get_oiv(oiv_id)
            oiv_name = oiv['name'] if oiv else "неизвестно"
            
            await query.edit_message_text(
                f"✅ ОИВ обновлен: {oiv_name}\n\n"
                f"Продолжайте редактирование или вернитесь к просмотру встречи.",
                reply_markup=get_edit_meeting_keyboard(meeting_id)
            )
            
            # Очищаем данные редактирования
            if 'editing_field' in context.user_data:
                del context.user_data['editing_field']
            if 'editing_complex_id' in context.user_data:
                del context.user_data['editing_complex_id']
            
            return EDIT_MEETING_FIELD
    
    elif field == 'status':
        if query.data.startswith('status_'):
            # Выбор статуса
            new_status = query.data.split('_')[1]
            
            db.update_meeting(meeting_id, status=new_status)
            
            await query.edit_message_text(
                f"✅ Статус обновлен: {new_status}\n\n"
                f"Продолжайте редактирование или вернитесь к просмотру встречи.",
                reply_markup=get_edit_meeting_keyboard(meeting_id)
            )
            
            del context.user_data['editing_field']
            return EDIT_MEETING_FIELD

# === УДАЛЕНИЕ ВСТРЕЧ (только для админа) ===
async def delete_meeting_start(update: Update, context):
    """Начало удаления встречи"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем права (должен быть админом)
    if context.user_data.get('role') != 'admin':
        await query.edit_message_text(
            "⛔ У вас нет прав для удаления встреч."
        )
        return
    
    meeting_id = int(query.data.split('_')[1])
    meeting = db.get_meeting(meeting_id)
    
    if not meeting:
        await query.edit_message_text("❌ Встреча не найдена.")
        return
    
    # Форматируем дату для сообщения
    date_str = meeting['meeting_date'].strftime('%d.%m.%Y')
    
    await query.edit_message_text(
        f"🗑️ *Удаление встречи #{meeting_id}*\n\n"
        f"🏢 *ОИВ:* {meeting['oiv_name']}\n"
        f"📅 *Дата:* {date_str}\n"
        f"📝 *Содержание:* {meeting['summary'][:100]}...\n\n"
        "❓ *Вы уверены, что хотите удалить эту встречу?*",
        reply_markup=get_delete_confirmation_keyboard(meeting_id),
        parse_mode='Markdown'
    )

async def delete_meeting_confirm(update: Update, context):
    """Подтверждение удаления встречи"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('delete_cancel_'):
        # Отмена удаления
        meeting_id = int(query.data.split('_')[2])
        meeting = db.get_meeting(meeting_id)
        
        # Возвращаемся к просмотру встречи
        date_str = meeting['meeting_date'].strftime('%d.%m.%Y')
        
        meeting_text = (
            f"✅ *Встреча #{meeting['id']}*\n\n"
            f"🏛️ *Комплекс:* {meeting['complex_name']}\n"
            f"🏢 *ОИВ:* {meeting['oiv_name']}\n"
            f"📅 *Дата:* {date_str}\n"
            f"📊 *Статус:* {meeting['status']}\n"
        )
        
        if meeting['duration_minutes']:
            meeting_text += f"⏱️ *Длительность:* {meeting['duration_minutes']} мин\n"
        
        meeting_text += f"👤 *Добавил:* {meeting['user_name']}\n"
        meeting_text += f"📝 *Содержание:*\n{meeting['summary']}"
        
        await query.edit_message_text(
            meeting_text,
            reply_markup=get_meeting_details_keyboard(meeting_id, 'admin'),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('delete_confirm_'):
        # Подтверждение удаления
        meeting_id = int(query.data.split('_')[2])
        
        # Удаляем встречу
        success = db.delete_meeting(meeting_id)
        
        if success:
            await query.edit_message_text(
                f"✅ Встреча #{meeting_id} успешно удалена.\n\n"
                "Вы можете продолжить просмотр других встреч."
            )
        else:
            await query.edit_message_text(
                f"❌ Не удалось удалить встречу #{meeting_id}.\n"
                "Попробуйте снова или обратитесь к разработчику."
            )

# === УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (только для админа) ===
async def admin_users_start(update: Update, context):
    """Начало управления пользователями"""
    # Проверяем права (должен быть админом)
    if context.user_data.get('role') != 'admin':
        await update.message.reply_text(
            "⛔ У вас нет прав для управления пользователями."
        )
        return
    
    await update.message.reply_text(
        "👥 *Управление пользователями*\n\n"
        "Выберите действие:",
        reply_markup=get_users_admin_keyboard(),
        parse_mode='Markdown'
    )

async def admin_users_callback(update: Update, context):
    """Обработка callback для управления пользователями"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'admin_list_users':
        # Список всех пользователей
        users = db.get_all_users()
        
        if not users:
            await query.edit_message_text("👥 Пользователей пока нет.")
            return
        
        users_text = "👥 *Список пользователей:*\n\n"
        for user in users:
            role_icon = "👑" if user['role'] == 'admin' else "👤"
            users_text += f"{role_icon} *{user['full_name']}*\n"
            users_text += f"   ID: `{user['telegram_id']}`\n"
            users_text += f"   Роль: {user['role']}\n"
            users_text += f"   Зарегистрирован: {user['registered_at'].strftime('%d.%m.%Y')}\n\n"
        
        await query.edit_message_text(
            users_text,
            reply_markup=get_users_admin_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == 'admin_add_user':
        # Начало добавления пользователя
        await query.edit_message_text(
            "➕ *Добавление нового пользователя*\n\n"
            "Введите Telegram ID пользователя (только цифры):",
            parse_mode='Markdown'
        )
        
        return ADMIN_ADD_USER_ID
    
    elif data == 'admin_delete_user':
        # Начало удаления пользователя
        await query.edit_message_text(
            "❌ *Удаление пользователя*\n\n"
            "Введите Telegram ID пользователя для удаления (только цифры):",
            parse_mode='Markdown'
        )
        
        return ADMIN_DELETE_USER
    
    elif data == 'admin_back_to_main':
        # Возврат в главное меню
        await query.edit_message_text(
            "Возврат в главное меню...",
            reply_markup=get_main_menu('admin')
        )

async def admin_add_user_id(update: Update, context):
    """Обработка ввода ID пользователя для добавления"""
    if update.message:
        telegram_id = update.message.text.strip()
        
        # Проверяем, что введены только цифры
        if not telegram_id.isdigit():
            await update.message.reply_text(
                "❌ ID должен содержать только цифры.\n"
                "Введите Telegram ID пользователя:"
            )
            return ADMIN_ADD_USER_ID
        
        telegram_id = int(telegram_id)
        
        # Проверяем, нет ли уже такого пользователя
        existing_user = db.get_user(telegram_id)
        if existing_user:
            await update.message.reply_text(
                f"❌ Пользователь с ID {telegram_id} уже существует.\n\n"
                "Введите другой Telegram ID:"
            )
            return ADMIN_ADD_USER_ID
        
        # Сохраняем ID для следующего шага
        context.user_data['new_user_id'] = telegram_id
        
        await update.message.reply_text(
            f"✅ ID пользователя: {telegram_id}\n\n"
            "Введите имя пользователя (как отображать в системе):"
        )
        
        return ADMIN_ADD_USER_NAME

async def admin_add_user_name(update: Update, context):
    """Обработка ввода имени пользователя"""
    if update.message:
        user_name = update.message.text.strip()
        telegram_id = context.user_data.get('new_user_id')
        
        if not telegram_id:
            await update.message.reply_text(
                "❌ Ошибка: ID пользователя не найден.\n"
                "Начните заново."
            )
            return ConversationHandler.END
        
        if len(user_name) < 2:
            await update.message.reply_text(
                "❌ Имя должно содержать хотя бы 2 символа.\n"
                "Введите имя пользователя:"
            )
            return ADMIN_ADD_USER_NAME
        
        # Добавляем пользователя
        try:
            db.add_user(telegram_id, user_name, role='user')
            
            await update.message.reply_text(
                f"✅ Пользователь успешно добавлен!\n\n"
                f"👤 *Имя:* {user_name}\n"
                f"🆔 *Telegram ID:* `{telegram_id}`\n"
                f"📊 *Роль:* пользователь\n\n"
                "Пользователь сможет войти в бот после команды /start.",
                parse_mode='Markdown',
                reply_markup=get_users_admin_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при добавлении пользователя: {e}\n\n"
                "Попробуйте снова.",
                reply_markup=get_users_admin_keyboard()
            )
        
        # Очищаем временные данные
        if 'new_user_id' in context.user_data:
            del context.user_data['new_user_id']
        
        return ConversationHandler.END

async def admin_delete_user_input(update: Update, context):
    """Обработка ввода ID пользователя для удаления"""
    if update.message:
        telegram_id = update.message.text.strip()
        
        # Проверяем, что введены только цифры
        if not telegram_id.isdigit():
            await update.message.reply_text(
                "❌ ID должен содержать только цифры.\n"
                "Введите Telegram ID пользователя для удаления:"
            )
            return ADMIN_DELETE_USER
        
        telegram_id = int(telegram_id)
        
        # Проверяем, существует ли пользователь
        user = db.get_user(telegram_id)
        if not user:
            await update.message.reply_text(
                f"❌ Пользователь с ID {telegram_id} не найден.\n\n"
                "Введите Telegram ID существующего пользователя:"
            )
            return ADMIN_DELETE_USER
        
        # Нельзя удалить самого себя
        if telegram_id == update.effective_user.id:
            await update.message.reply_text(
                "❌ Вы не можете удалить сами себя.\n\n"
                "Введите Telegram ID другого пользователя:"
            )
            return ADMIN_DELETE_USER
        
        # Удаляем пользователя
        success = db.delete_user(telegram_id)
        
        if success:
            await update.message.reply_text(
                f"✅ Пользователь {user['full_name']} (ID: {telegram_id}) успешно удален.",
                reply_markup=get_users_admin_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ Не удалось удалить пользователя с ID {telegram_id}.",
                reply_markup=get_users_admin_keyboard()
            )
        
        return ConversationHandler.END

# === СТАТИСТИКА (только для админа) ===
async def show_statistics(update: Update, context):
    """Показ статистики по встречам"""
    # Проверяем права (должен быть админом)
    if context.user_data.get('role') != 'admin':
        await update.message.reply_text(
            "⛔ У вас нет прав для просмотра статистики."
        )
        return
    
    # Получаем статистику
    stats = db.get_statistics()
    
    if not stats:
        await update.message.reply_text(
            "📊 Статистика пока недоступна.\n"
            "Добавьте несколько встреч для анализа."
        )
        return
    
    # Группируем статистику
    complex_stats = {}
    for row in stats:
        complex_name = row['complex_name']
        if complex_name not in complex_stats:
            complex_stats[complex_name] = {
                'total': 0,
                'by_status': {},
                'by_oiv': {}
            }
        
        # Общее количество
        complex_stats[complex_name]['total'] += row['count']
        
        # По статусам
        status = row['status']
        if status not in complex_stats[complex_name]['by_status']:
            complex_stats[complex_name]['by_status'][status] = 0
        complex_stats[complex_name]['by_status'][status] += row['count']
        
        # По ОИВ
        oiv_name = row['oiv_name']
        if oiv_name not in complex_stats[complex_name]['by_oiv']:
            complex_stats[complex_name]['by_oiv'][oiv_name] = {
                'total': 0,
                'by_status': {}
            }
        
        complex_stats[complex_name]['by_oiv'][oiv_name]['total'] += row['count']
        
        if status not in complex_stats[complex_name]['by_oiv'][oiv_name]['by_status']:
            complex_stats[complex_name]['by_oiv'][oiv_name]['by_status'][status] = 0
        complex_stats[complex_name]['by_oiv'][oiv_name]['by_status'][status] += row['count']
    
    # Формируем текст статистики
    stats_text = "📊 *Статистика встреч*\n\n"
    
    for complex_name, data in complex_stats.items():
        stats_text += f"🏛️ *{complex_name}*\n"
        stats_text += f"   Всего встреч: {data['total']}\n"
        
        # Статистика по статусам
        if data['by_status']:
            stats_text += "   По статусам:\n"
            for status, count in data['by_status'].items():
                stats_text += f"     {status}: {count}\n"
        
        # Топ ОИВ (первые 3)
        top_oivs = sorted(
            data['by_oiv'].items(),
            key=lambda x: x[1]['total'],
            reverse=True
        )[:3]
        
        if top_oivs:
            stats_text += "   Топ ОИВ:\n"
            for oiv_name, oiv_data in top_oivs:
                stats_text += f"     {oiv_name}: {oiv_data['total']} встреч\n"
        
        stats_text += "\n"
    
    # Общая статистика
    total_meetings = sum(data['total'] for data in complex_stats.values())
    stats_text += f"📈 *Общая статистика:*\n"
    stats_text += f"   Всего встреч в системе: {total_meetings}\n"
    stats_text += f"   Всего комплексов: {len(complex_stats)}\n"
    
    # Получаем последнюю встречу
    all_meetings = db.get_all_meetings()
    if all_meetings:
        last_meeting = all_meetings[0]
        last_date = last_meeting['meeting_date'].strftime('%d.%m.%Y')
        stats_text += f"   Последняя встреча: {last_date} ({last_meeting['oiv_name']})\n"
    
    await update.message.reply_text(
        stats_text,
        parse_mode='Markdown'
    )

# === ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ===
async def handle_text(update: Update, context):
    """Обработка текстовых сообщений (кнопки главного меню)"""
    text = update.message.text
    user_role = context.user_data.get('role', 'user')
    
    if text == "➕ Добавить встречу":
        # Начинаем процесс добавления встречи
        return await add_meeting_start(update, context)
    
    elif text == "📋 Просмотреть встречи":
        # Показываем встречи
        await view_meetings_start(update, context)
    
    elif text == "👥 Управление пользователями" and user_role == 'admin':
        # Управление пользователями
        await admin_users_start(update, context)
    
    elif text == "📊 Статистика" and user_role == 'admin':
        # Показ статистики
        await show_statistics(update, context)
    
    else:
        await update.message.reply_text(
            "Используйте кнопки меню или команды для взаимодействия с ботом.",
            reply_markup=get_main_menu(user_role)
        )

# === ОТМЕНА ДИАЛОГА ===
async def cancel(update: Update, context):
    """Отмена любого диалога"""
    user_role = context.user_data.get('role', 'user')
    
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=get_main_menu(user_role)
    )
    
    # Очищаем все временные данные
    for key in ['new_meeting', 'editing_meeting_id', 'editing_field', 
                'editing_complex_id', 'new_user_id', 
                'view_year', 'view_filters', 'view_meetings', 'view_page']:
        if key in context.user_data:
            del context.user_data[key]
    
    return ConversationHandler.END

# === ОСНОВНАЯ ФУНКЦИЯ ===
def main():
    """Основная функция запуска бота"""
    # Создаем приложение с явным указанием контекста
    context_types = ContextTypes()
    application = Application.builder().token(BOT_TOKEN).context_types(context_types).build()
    
    # Добавляем обработчик команды /start
    application.add_handler(CommandHandler("start", start))
    
    # Добавляем обработчик для добавления встречи (диалог)
    conv_handler_add_meeting = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("➕ Добавить встречу"), add_meeting_start)],
        states={
            SELECT_COMPLEX: [CallbackQueryHandler(select_complex)],
            SELECT_OIV: [CallbackQueryHandler(select_oiv)],
            SELECT_DATE: [CallbackQueryHandler(select_date)],
            SELECT_STATUS: [CallbackQueryHandler(select_status)],
            INPUT_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_duration)],
            INPUT_SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_summary)],
            CONFIRM_MEETING: [CallbackQueryHandler(confirm_meeting)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    
    # Добавляем обработчик для редактирования встречи
    conv_handler_edit_meeting = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_meeting_start, pattern="^edit_")],
        states={
            EDIT_MEETING_FIELD: [
                CallbackQueryHandler(edit_meeting_field),
                CallbackQueryHandler(edit_meeting_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_meeting_input)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    
    # Добавляем обработчик для управления пользователями (админ)
    conv_handler_admin_users = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_users_callback, pattern="^admin_")],
        states={
            ADMIN_ADD_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_user_id)],
            ADMIN_ADD_USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_user_name)],
            ADMIN_DELETE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_user_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler_add_meeting)
    application.add_handler(conv_handler_edit_meeting)
    application.add_handler(conv_handler_admin_users)
    
    # Обработчики для просмотра встреч
    application.add_handler(CallbackQueryHandler(view_meetings_callback, pattern="^(year_|month_|meeting_|prev_page_|next_page_|back_to_)"))
    
    # Обработчики для удаления встреч
    application.add_handler(CallbackQueryHandler(delete_meeting_start, pattern="^delete_"))
    application.add_handler(CallbackQueryHandler(delete_meeting_confirm, pattern="^delete_confirm_|^delete_cancel_"))
    
    # Обработчик текстовых сообщений (кнопки главного меню)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, start))
    
    # Запускаем бота ПРОСТО
    print("Бот запущен...")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
