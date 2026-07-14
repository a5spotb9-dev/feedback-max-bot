from bothost import BotHost
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = BotHost()

# ID администратора для получения обращений (замените на свой)
ADMIN_ID = "YOUR_ADMIN_MAX_ID"

# Состояния пользователей
user_states = {}

# Константы состояний
STATE_WAITING_MESSAGE = "waiting_message"
STATE_WAITING_CONTACT = "waiting_contact"


@bot.message_handler(commands=['start'])
def start_handler(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_states[user_id] = None
    
    bot.send_message(
        message.chat.id,
        "👋 Здравствуйте! Я бот обратной связи.\n\n"
        "Вы можете:\n"
        "📝 /feedback - Отправить обращение\n"
        "❓ /help - Получить помощь\n"
        "❌ /cancel - Отменить текущее действие"
    )


@bot.message_handler(commands=['help'])
def help_handler(message):
    """Обработчик команды /help"""
    bot.send_message(
        message.chat.id,
        "ℹ️ Помощь по боту:\n\n"
        "• /start - Начать работу с ботом\n"
        "• /feedback - Отправить сообщение администрации\n"
        "• /cancel - Отменить текущее действие\n\n"
        "Для обратной связи просто напишите команду /feedback и следуйте инструкциям."
    )


@bot.message_handler(commands=['cancel'])
def cancel_handler(message):
    """Отмена текущего действия"""
    user_id = message.from_user.id
    
    if user_id in user_states and user_states[user_id]:
        user_states[user_id] = None
        bot.send_message(
            message.chat.id,
            "❌ Действие отменено. Используйте /feedback для новой попытки."
        )
    else:
        bot.send_message(
            message.chat.id,
            "Нет активных действий для отмены."
        )


@bot.message_handler(commands=['feedback'])
def feedback_handler(message):
    """Начало процесса обратной связи"""
    user_id = message.from_user.id
    user_states[user_id] = STATE_WAITING_MESSAGE
    
    bot.send_message(
        message.chat.id,
        "📝 Напишите ваше сообщение администрации.\n\n"
        "Вы можете отправить текст, фото или документ.\n"
        "Для отмены используйте /cancel"
    )


@bot.message_handler(func=lambda message: 
                     message.from_user.id in user_states and 
                     user_states[message.from_user.id] == STATE_WAITING_MESSAGE)
def receive_feedback_message(message):
    """Получение сообщения обратной связи"""
    user_id = message.from_user.id
    
    # Сохраняем сообщение пользователя
    user_states[user_id] = {
        'state': STATE_WAITING_CONTACT,
        'message': message
    }
    
    bot.send_message(
        message.chat.id,
        "✅ Сообщение получено!\n\n"
        "Теперь укажите ваши контактные данные (имя, телефон или email):\n"
        "Или напишите 'пропустить' если не хотите оставлять контакты."
    )


@bot.message_handler(func=lambda message: 
                     message.from_user.id in user_states and 
                     isinstance(user_states[message.from_user.id], dict) and
                     user_states[message.from_user.id].get('state') == STATE_WAITING_CONTACT)
def receive_contact_info(message):
    """Получение контактной информации"""
    user_id = message.from_user.id
    contact_info = message.text
    
    # Получаем сохраненное сообщение
    original_message = user_states[user_id]['message']
    
    # Формируем сообщение для администратора
    user_info = f"👤 Пользователь: {message.from_user.first_name}"
    if message.from_user.username:
        user_info += f" (@{message.from_user.username})"
    user_info += f"\n🆔 ID: {user_id}"
    
    if contact_info.lower() != 'пропустить':
        user_info += f"\n📞 Контакты: {contact_info}"
    
    admin_message = (
        "📬 НОВОЕ ОБРАЩЕНИЕ\n\n"
        f"{user_info}\n\n"
        "💬 Сообщение:\n"
        f"{original_message.text if hasattr(original_message, 'text') else '[Медиа]'}"
    )
    
    # Отправляем администратору
    try:
        bot.send_message(ADMIN_ID, admin_message)
        
        # Если было медиа, отправляем его отдельно
        if hasattr(original_message, 'photo') and original_message.photo:
            bot.send_photo(ADMIN_ID, original_message.photo[-1].file_id)
        elif hasattr(original_message, 'document') and original_message.document:
            bot.send_document(ADMIN_ID, original_message.document.file_id)
        
        # Подтверждение пользователю
        bot.send_message(
            message.chat.id,
            "✅ Ваше обращение успешно отправлено!\n\n"
            "Администрация свяжется с вами в ближайшее время.\n\n"
            "Используйте /feedback для нового обращения."
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения администратору: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при отправке. Попробуйте позже или используйте /feedback снова."
        )
    
    # Сброс состояния
    user_states[user_id] = None


@bot.message_handler(func=lambda message: True)
def default_handler(message):
    """Обработчик всех остальных сообщений"""
    bot.send_message(
        message.chat.id,
        "Используйте команды:\n"
        "📝 /feedback - Отправить обращение\n"
        "❓ /help - Помощь\n"
        "🏠 /start - Главное меню"
    )


# Запуск бота
if __name__ == '__main__':
    logger.info("Бот запущен!")
    bot.polling()
