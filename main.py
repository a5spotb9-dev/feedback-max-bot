from maxbot import Bot

from handlers import start, select_type, receive_message

bot = Bot()

bot.command("start")(start)

bot.message("📰 Новость")(select_type)
bot.message("📩 Обращение")(select_type)
bot.message("💬 Вопрос")(select_type)

bot.message()(receive_message)

bot.run()
