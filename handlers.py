from config import ADMIN_CHAT_ID

user_data = {}


def start(bot, message):
    keyboard = [
        ["📰 Новость"],
        ["📩 Обращение"],
        ["💬 Вопрос"]
    ]

    bot.send_message(
        chat_id=message.chat.id,
        text=(
            "Здравствуйте!\n\n"
            "Это официальный бот обратной связи.\n\n"
            "Выберите тип сообщения."
        ),
        keyboard=keyboard
    )


def select_type(bot, message):
    user_data[message.chat.id] = message.text

    bot.send_message(
        message.chat.id,
        "Напишите сообщение или прикрепите фотографию, видео либо документ."
    )


def receive_message(bot, message):
    msg_type = user_data.get(message.chat.id, "Не указан")

    text = f"""
📨 Новое обращение

Тип:
{msg_type}

Имя:
{message.from_user.first_name}

ID:
{message.from_user.id}

Username:
@{message.from_user.username}

Сообщение:

{message.text}
"""

    bot.send_message(
        ADMIN_CHAT_ID,
        text
    )

    if message.photo:
        bot.forward_message(
            ADMIN_CHAT_ID,
            message.chat.id,
            message.message_id
        )

    if message.document:
        bot.forward_message(
            ADMIN_CHAT_ID,
            message.chat.id,
            message.message_id
        )

    if message.video:
        bot.forward_message(
            ADMIN_CHAT_ID,
            message.chat.id,
            message.message_id
        )

    bot.send_message(
        message.chat.id,
        "Спасибо! Ваше обращение принято."
    )
