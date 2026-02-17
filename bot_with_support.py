import telebot
import os
import time
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 635440209  # Твой ID

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище состояний
user_state = {}

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('🔍 Поиск'),
        KeyboardButton('⭐ Подписка'),
        KeyboardButton('💬 Поддержка'),
        KeyboardButton('👤 Профиль')
    )
    return markup

def cancel_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('❌ Отмена'))
    return markup

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "Друг"
    
    bot.send_message(
        message.chat.id,
        f"👋 <b>Привет, {name}!</b>\n\n"
        f"Я бот для поиска фильмов. Выбери действие:",
        parse_mode='HTML',
        reply_markup=main_menu()
    )

# ========== ПОИСК ==========
@bot.message_handler(func=lambda m: m.text == '🔍 Поиск')
def search_start(message):
    user_state[message.from_user.id] = 'search'
    bot.send_message(
        message.chat.id,
        "🎬 Введи название фильма:",
        reply_markup=cancel_menu()
    )

# ========== ПОДПИСКА ==========
@bot.message_handler(func=lambda m: m.text == '⭐ Подписка')
def subscription(message):
    bot.send_message(
        message.chat.id,
        "⭐ <b>Подписка</b>\n\n"
        "• 1 месяц — 199₽\n"
        "• 3 месяца — 499₽\n"
        "• 6 месяцев — 899₽\n"
        "• 12 месяцев — 1499₽\n\n"
        "💳 Карта: 2202 2081 7050 3883\n\n"
        "После оплаты напиши в поддержку",
        parse_mode='HTML'
    )

# ========== ПРОФИЛЬ ==========
@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(message):
    user_id = message.from_user.id
    bot.send_message(
        message.chat.id,
        f"👤 <b>Твой профиль</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👋 Имя: {message.from_user.first_name}\n"
        f"📱 Username: @{message.from_user.username or 'нет'}",
        parse_mode='HTML'
    )

# ========== ПОДДЕРЖКА (ИСПРАВЛЕННАЯ) ==========
@bot.message_handler(func=lambda m: m.text == '💬 Поддержка')
def support_start(message):
    user_state[message.from_user.id] = 'support'
    bot.send_message(
        message.chat.id,
        "📝 <b>Напиши свой вопрос</b>\n\nОпиши проблему подробно. Я передам админу.",
        parse_mode='HTML',
        reply_markup=cancel_menu()
    )

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
@bot.message_handler(func=lambda m: m.text == '❌ Отмена')
def cancel(message):
    user_id = message.from_user.id
    if user_id in user_state:
        del user_state[user_id]
    bot.send_message(message.chat.id, "❌ Отменено", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    user_id = message.from_user.id
    text = message.text
    
    # Режим поиска
    if user_id in user_state and user_state[user_id] == 'search':
        del user_state[user_id]
        bot.send_message(
            user_id,
            f"🔍 Ищем: {text}\n\n(Функция поиска временно отключена)",
            reply_markup=main_menu()
        )
    
    # Режим поддержки
    elif user_id in user_state and user_state[user_id] == 'support':
        del user_state[user_id]
        
        # Подтверждение пользователю
        bot.send_message(
            user_id,
            "✅ <b>Сообщение отправлено админу!</b>\n\nОжидай ответа в этом чате.",
            parse_mode='HTML',
            reply_markup=main_menu()
        )
        
        # Отправка админу
        try:
            admin_msg = f"""
📨 <b>НОВОЕ СООБЩЕНИЕ В ПОДДЕРЖКУ</b>

👤 <b>От:</b> {message.from_user.first_name}
🆔 <b>ID:</b> <code>{user_id}</code>
📱 <b>Username:</b> @{message.from_user.username or 'нет'}

💬 <b>Сообщение:</b>
{text}

━━━━━━━━━━━━━━━━
<b>Чтобы ответить, отправь:</b>
<code>/reply {user_id} Твой ответ</code>
"""
            bot.send_message(ADMIN_ID, admin_msg, parse_mode='HTML')
            print(f"✅ Сообщение от {user_id} отправлено админу")
        except Exception as e:
            print(f"❌ Ошибка отправки админу: {e}")
    
    # Обычное сообщение
    else:
        bot.send_message(
            user_id,
            "Используй кнопки меню",
            reply_markup=main_menu()
        )

# ========== ОТВЕТ АДМИНА ==========
@bot.message_handler(commands=['reply'])
def admin_reply(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Нет доступа")
        return
    
    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Используй: /reply [ID пользователя] [текст]")
            return
        
        user_id = int(parts[1])
        reply_text = parts[2]
        
        bot.send_message(
            user_id,
            f"📨 <b>Ответ от поддержки:</b>\n\n{reply_text}",
            parse_mode='HTML'
        )
        
        bot.reply_to(message, f"✅ Ответ отправлен пользователю {user_id}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("=" * 50)
    print("🤖 БОТ С ПОДДЕРЖКОЙ")
    print("=" * 50)
    print(f"✅ Админ ID: {ADMIN_ID}")
    print("✅ Бот запущен!")
    print("=" * 50)
    
    # Тест отправки админу при запуске
    try:
        bot.send_message(ADMIN_ID, "✅ Бот с поддержкой запущен!")
        print("✅ Тестовое сообщение админу отправлено")
    except:
        print("⚠️ Не удалось отправить тест админу")
    
    bot.infinity_polling()
