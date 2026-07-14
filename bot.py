import os
import logging
import asyncio
import aiohttp
from aiohttp import web

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Токен бота и ID администратора из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
PORT = int(os.environ.get("PORT", 8080))

MAX_API_URL = "https://botapi.max.ru"

# Хранилище состояний пользователей
user_states = {}

# Состояния
STATE_IDLE = "idle"
STATE_WAITING_NAME = "waiting_name"
STATE_WAITING_PHONE = "waiting_phone"
STATE_WAITING_MESSAGE = "waiting_message"


async def send_message(chat_id: str, text: str, session: aiohttp.ClientSession):
    """Отправка сообщения пользователю"""
    url = f"{MAX_API_URL}/messages"
    params = {"access_token": BOT_TOKEN}
    payload = {
        "recipient": {"chat_id": int(chat_id)},
        "message": {
            "text": text
        }
    }
    try:
        async with session.post(url, params=params, json=payload) as resp:
            result = await resp.json()
            logger.info(f"Отправлено сообщение: {result}")
            return result
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")


async def send_buttons(chat_id: str, text: str, buttons: list, session: aiohttp.ClientSession):
    """Отправка сообщения с кнопками"""
    url = f"{MAX_API_URL}/messages"
    params = {"access_token": BOT_TOKEN}

    inline_buttons = []
    for btn in buttons:
        inline_buttons.append({
            "type": "callback",
            "text": btn["text"],
            "payload": btn["payload"]
        })

    payload = {
        "recipient": {"chat_id": int(chat_id)},
        "message": {
            "text": text,
            "attachments": [
                {
                    "type": "inline_keyboard",
                    "payload": {
                        "buttons": [inline_buttons]
                    }
                }
            ]
        }
    }
    try:
        async with session.post(url, params=params, json=payload) as resp:
            result = await resp.json()
            logger.info(f"Отправлены кнопки: {result}")
            return result
    except Exception as e:
        logger.error(f"Ошибка отправки кнопок: {e}")


async def notify_admin(user_data: dict, session: aiohttp.ClientSession):
    """Уведомление администратора о новом сообщении"""
    if not ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID не задан!")
        return

    text = (
        f"📩 *Новое обращение!*\n\n"
        f"👤 Имя: {user_data.get('name', 'не указано')}\n"
        f"📞 Телефон: {user_data.get('phone', 'не указан')}\n"
        f"💬 Сообщение: {user_data.get('message', 'не указано')}\n"
        f"🆔 Chat ID: {user_data.get('chat_id', '')}\n"
        f"👤 Username: @{user_data.get('username', 'нет')}"
    )

    await send_message(ADMIN_CHAT_ID, text, session)


async def handle_start(chat_id: str, username: str, session: aiohttp.ClientSession):
    """Обработка команды /start"""
    user_states[chat_id] = {"state": STATE_IDLE, "username": username}

    text = (
        f"👋 Добро пожаловать!\n\n"
        f"Это бот обратной связи компании *ТАВРИЯ*.\n"
        f"Мы всегда рады помочь вам!\n\n"
        f"Нажмите кнопку ниже, чтобы оставить обращение:"
    )

    buttons = [
        {"text": "✉️ Написать обращение", "payload": "start_feedback"}
    ]

    await send_buttons(chat_id, text, buttons, session)


async def handle_callback(chat_id: str, payload: str, session: aiohttp.ClientSession):
    """Обработка нажатий на кнопки"""
    if payload == "start_feedback":
        user_states[chat_id]["state"] = STATE_WAITING_NAME
        await send_message(
            chat_id,
            "📝 Пожалуйста, введите ваше *имя*:",
            session
        )

    elif payload == "confirm_send":
        user_data = user_states.get(chat_id, {})
        await notify_admin(user_data, session)
        user_states[chat_id]["state"] = STATE_IDLE

        await send_message(
            chat_id,
            "✅ Ваше обращение успешно отправлено!\n\n"
            "Мы свяжемся с вами в ближайшее время. Спасибо! 🙏",
            session
        )

        buttons = [
            {"text": "✉️ Написать ещё", "payload": "start_feedback"}
        ]
        await send_buttons(
            chat_id,
            "Хотите отправить ещё одно обращение?",
            buttons,
            session
        )

    elif payload == "cancel_send":
        user_states[chat_id]["state"] = STATE_IDLE

        await send_message(
            chat_id,
            "❌ Отправка отменена.\n\nЕсли захотите — нажмите кнопку ниже.",
            session
        )

        buttons = [
            {"text": "✉️ Написать обращение", "payload": "start_feedback"}
        ]
        await send_buttons(chat_id, "Главное меню:", buttons, session)


async def handle_message(chat_id: str, text: str, username: str, session: aiohttp.ClientSession):
    """Обработка текстовых сообщений"""

    if text.startswith("/start"):
        await handle_start(chat_id, username, session)
        return

    # Инициализация если нет состояния
    if chat_id not in user_states:
        await handle_start(chat_id, username, session)
        return

    state = user_states[chat_id].get("state", STATE_IDLE)

    if state == STATE_WAITING_NAME:
        user_states[chat_id]["name"] = text
        user_states[chat_id]["state"] = STATE_WAITING_PHONE
        await send_message(
            chat_id,
            f"Отлично, {text}! 👍\n\n📞 Введите ваш *номер телефона*:",
            session
        )

    elif state == STATE_WAITING_PHONE:
        user_states[chat_id]["phone"] = text
        user_states[chat_id]["state"] = STATE_WAITING_MESSAGE
        await send_message(
            chat_id,
            "💬 Теперь напишите ваше *сообщение* или вопрос:",
            session
        )

    elif state == STATE_WAITING_MESSAGE:
        user_states[chat_id]["message"] = text
        user_states[chat_id]["chat_id"] = chat_id
        user_states[chat_id]["state"] = STATE_IDLE

        # Показываем подтверждение
        name = user_states[chat_id].get("name", "")
        phone = user_states[chat_id].get("phone", "")

        confirm_text = (
            f"📋 *Проверьте данные перед отправкой:*\n\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"💬 Сообщение: {text}\n\n"
            f"Всё верно?"
        )

        buttons = [
            {"text": "✅ Отправить", "payload": "confirm_send"},
            {"text": "❌ Отменить", "payload": "cancel_send"}
        ]

        await send_buttons(chat_id, confirm_text, buttons, session)

    else:
        # Пользователь пишет без активного диалога
        buttons = [
            {"text": "✉️ Написать обращение", "payload": "start_feedback"}
        ]
        await send_buttons(
            chat_id,
            "Нажмите кнопку, чтобы оставить обращение:",
            buttons,
            session
        )


async def process_update(update: dict, session: aiohttp.ClientSession):
    """Обработка входящего обновления"""
    logger.info(f"Получено обновление: {update}")

    update_type = update.get("update_type", "")

    if update_type == "message_created":
        message = update.get("message", {})
        sender = message.get("sender", {})
        chat_id = str(message.get("recipient", {}).get("chat_id", ""))
        text = message.get("body", {}).get("text", "")
        username = sender.get("username", "")

        if chat_id and text:
            await handle_message(chat_id, text, username, session)

    elif update_type == "message_callback":
        callback = update.get("callback", {})
        chat_id = str(callback.get("message", {}).get("recipient", {}).get("chat_id", ""))
        payload = callback.get("payload", "")
        user = callback.get("user", {})
        username = user.get("username", "")

        if chat_id not in user_states:
            user_states[chat_id] = {"state": STATE_IDLE, "username": username}

        if chat_id and payload:
            await handle_callback(chat_id, payload, session)


async def webhook_handler(request: web.Request) -> web.Response:
    """Обработчик вебхука"""
    try:
        update = await request.json()
        async with aiohttp.ClientSession() as session:
            await process_update(update, session)
        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return web.Response(text="Error", status=500)


async def set_webhook(session: aiohttp.ClientSession):
    """Установка вебхука"""
    if not WEBHOOK_URL:
        logger.warning("WEBHOOK_URL не задан!")
        return

    url = f"{MAX_API_URL}/subscriptions"
    params = {"access_token": BOT_TOKEN}
    payload = {
        "url": WEBHOOK_URL,
        "update_types": ["message_created", "message_callback"],
        "version": "1.0"
    }

    try:
        async with session.post(url, params=params, json=payload) as resp:
            result = await resp.json()
            logger.info(f"Вебхук установлен: {result}")
    except Exception as e:
        logger.error(f"Ошибка установки вебхука: {e}")


async def main():
    """Запуск бота"""
    logger.info("Запуск бота обратной связи ТАВРИЯ...")

    async with aiohttp.ClientSession() as session:
        await set_webhook(session)

    # Запуск веб-сервера
    app = web.Application()
    app.router.add_post("/webhook", webhook_handler)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"Сервер запущен на порту {PORT}")

    # Держим сервер запущенным
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
