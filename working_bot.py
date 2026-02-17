import telebot
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Твой ID
ADMIN_ID = 635440209

bot = telebot.TeleBot(BOT_TOKEN)

# Простые кнопки
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('🔍 Поиск'))
    markup.add(KeyboardButton('📞 Поддержка'))
    return markup

# Состояния пользователей
waiting_for = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"👋 Привет! Я простой бот.\nТвой ID: {message.from_user.id}",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == '🔍 Поиск')
def search(message):
    waiting_for[message.from_user.id] = 'search'
    bot.send_message(
        message.chat.id,
        "Введи название фильма:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    )

@bot.message_handler(func=lambda m: m.text == '📞 Поддержка')
def support(message):
    waiting_for[message.from_user.id] = 'support'
    bot.send_message(
        message.chat.id,
        "📝 Напиши свой вопрос:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    )

@bot.message_handler(func=lambda m: m.text == '❌ Отмена')
def cancel(message):
    if message.from_user.id in waiting_for:
        del waiting_for[message.from_user.id]
    bot.send_message(message.chat.id, "❌ Отменено", reply_markup=main_menu())

# Обработка сообщений
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    user_id = message.from_user.id
    text = message.text
    
    # Если пользователь в режиме поиска
    if user_id in waiting_for and waiting_for[user_id] == 'search':
        del waiting_for[user_id]
        bot.send_message(
            user_id,
            f"🔍 Ищем: {text}\n(Функция поиска временно отключена)",
            reply_markup=main_menu()
        )
    
    # Если пользователь в режиме поддержки
    elif user_id in waiting_for and waiting_for[user_id] == 'support':
        del waiting_for[user_id]
        
        # Отправляем пользователю подтверждение
        bot.send_message(
            user_id,
            "✅ Твое сообщение отправлено админу!",
            reply_markup=main_menu()
        )
        
        # Отправляем админу
        try:
            admin_text = f"""
📨 Сообщение в поддержку

От: {message.from_user.first_name}
ID: {user_id}
Текст: {text}
            """
            bot.send_message(ADMIN_ID, admin_text)
            print(f"✅ Сообщение отправлено админу {ADMIN_ID}")
        except Exception as e:
            print(f"❌ Ошибка отправки админу: {e}")
    
    # Если пользователь не в режиме - отправляем в меню
    else:
        bot.send_message(
            user_id,
            "Используй кнопки в меню",
            reply_markup=main_menu()
        )

print("=" * 50)
print("🤖 СУПЕР-ПРОСТОЙ БОТ")
print("=" * 50)
print(f"✅ Твой ID: {ADMIN_ID}")
print("✅ Бот запущен!")
print("=" * 50)

bot.infinity_polling()
