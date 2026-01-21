from telegram.ext import ConversationHandler

# Состояния для добавления встречи
(
    SELECT_COMPLEX,
    SELECT_OIV,
    SELECT_DATE,
    SELECT_STATUS,
    INPUT_DURATION,
    INPUT_SUMMARY,
    CONFIRM_MEETING
) = range(7)

# Состояния для редактирования встречи
EDIT_MEETING_FIELD = 10

# Состояния для управления пользователями
(
    ADMIN_ADD_USER_ID,
    ADMIN_ADD_USER_NAME,
    ADMIN_DELETE_USER
) = range(20, 23)
