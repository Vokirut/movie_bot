import telebot
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

print("=" * 50)
print(f"🤖 Токен загружен: {BOT_TOKEN[:10]}...")
print("=" * 50)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    print(f"✅ Start от {user_name} (ID: {user_id})")
    bot.reply_to(message, f"Привет, {user_name}! Бот работает!")

@bot.message_handler(func=lambda message: True)
def echo(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text = message.text
    print(f"📨 Сообщение от {user_name} (ID: {user_id}): {text}")
    bot.reply_to(message, f"Получил: {text}")

print("🚀 Бот запущен и ждет сообщения...")
print("📝 Смотри логи выше")
bot.infinity_polling()
