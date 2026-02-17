import telebot
import requests
import os
import datetime
import sqlite3
import time
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ Ошибка: Токен не найден!")
    exit(1)

# ТВОЙ ID
ADMIN_ID = 635440209
YOUR_CARD = "2202 2081 7050 3883"

bot = telebot.TeleBot(BOT_TOKEN)

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        subscribed INTEGER DEFAULT 0,
        sub_until TEXT,
        is_admin INTEGER DEFAULT 0,
        joined_date TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        answer TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT
    )
''')
conn.commit()

# ========== ХРАНИЛИЩЕ СОСТОЯНИЙ ==========
# Здесь будем запоминать, кто сейчас в режиме поддержки
user_state = {}

# ========== ФУНКЦИИ ==========
def add_user(user_id, username, first_name):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date) VALUES (?, ?, ?, ?)',
                  (user_id, username, first_name, now))
    conn.commit()

def is_admin(user_id):
    return user_id == ADMIN_ID

def search_film(query):
    url = f"https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword={query}"
    headers = {'X-API-KEY': '8c8e7a9c-8b5c-4b3e-9f5a-3d5c5e5f7b8a'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get('films', [])[:5]
        return []
    except:
        return []

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('🔍 Поиск фильма'),
        KeyboardButton('⭐️ Подписка')
    )
    markup.add(
        KeyboardButton('💬 Написать в поддержку'),
        KeyboardButton('👤 Мой профиль')
    )
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('📊 Статистика'),
        KeyboardButton('📨 Открытые тикеты')
    )
    markup.add(
        KeyboardButton('🔑 Выдать подписку'),
        KeyboardButton('📢 Рассылка')
    )
    markup.add(KeyboardButton('◀️ Выйти из админки'))
    return markup

def cancel_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('❌ Отмена'))
    return markup

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "Друг"
    add_user(user_id, message.from_user.username, name)
    
    # Если это админ
    if user_id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            f"👑 <b>Привет, Админ!</b>\n\n"
            f"🆔 Твой ID: <code>{user_id}</code>\n"
            f"💳 Твоя карта: <code>{YOUR_CARD}</code>\n\n"
            f"📨 Новые обращения будут приходить сразу сюда",
            parse_mode='HTML',
            reply_markup=admin_menu()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"🎬 <b>Привет, {name}!</b>\n\n"
            f"Я помогу найти любой фильм. Используй кнопки ниже:",
            parse_mode='HTML',
            reply_markup=main_menu()
        )

# ========== ПОИСК ==========
@bot.message_handler(func=lambda m: m.text == '🔍 Поиск фильма')
def search_prompt(message):
    user_state[message.from_user.id] = 'searching'
    bot.send_message(
        message.chat.id,
        "🎬 Введи название фильма:",
        reply_markup=cancel_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == '❌ Отмена')
def cancel_action(message):
    user_id = message.from_user.id
    if user_id in user_state:
        del user_state[user_id]
    
    if user_id == ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Отменено", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "❌ Отменено", reply_markup=main_menu())

# ========== ПОДДЕРЖКА (ИСПРАВЛЕННАЯ) ==========
@bot.message_handler(func=lambda m: m.text == '💬 Написать в поддержку')
def support_start(message):
    user_id = message.from_user.id
    user_state[user_id] = 'support'  # Запоминаем, что пользователь в режиме поддержки
    
    bot.send_message(
        message.chat.id,
        "📝 <b>Напиши свой вопрос:</b>\n\n"
        "Опиши проблему подробно. Я передам сообщение администратору.",
        parse_mode='HTML',
        reply_markup=cancel_keyboard()
    )

# Обработка сообщений в режиме поддержки
@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id] == 'support')
def handle_support_message(message):
    user_id = message.from_user.id
    user_text = message.text
    username = message.from_user.username or "нет"
    first_name = message.from_user.first_name or "Пользователь"
    
    # Удаляем из состояния
    if user_id in user_state:
        del user_state[user_id]
    
    # Сохраняем в БД
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('INSERT INTO tickets (user_id, message, created_at) VALUES (?, ?, ?)',
                  (user_id, user_text, now))
    conn.commit()
    ticket_id = cursor.lastrowid
    
    # Подтверждение пользователю
    bot.send_message(
        user_id,
        f"✅ <b>Обращение #{ticket_id} принято!</b>\n\n"
        f"Твой вопрос: {user_text}\n\n"
        f"Админ ответит в ближайшее время.",
        parse_mode='HTML',
        reply_markup=main_menu()
    )
    
    # ===== ОТПРАВКА АДМИНУ =====
    admin_message = f"""
📨 <b>НОВОЕ ОБРАЩЕНИЕ #{ticket_id}</b>

━━━━━━━━━━━━━━━━━━━━━
👤 <b>От:</b> {first_name}
🆔 <b>ID:</b> <code>{user_id}</code>
📱 <b>Username:</b> @{username}
⏰ <b>Время:</b> {now}
━━━━━━━━━━━━━━━━━━━━━

💬 <b>Сообщение:</b>
{user_text}

━━━━━━━━━━━━━━━━━━━━━
<b>Чтобы ответить, отправь:</b>
<code>/reply {ticket_id} Твой ответ</code>
    """
    
    # Отправляем с подтверждением доставки
    try:
        sent_msg = bot.send_message(ADMIN_ID, admin_message, parse_mode='HTML')
        print(f"✅ Уведомление о тикете #{ticket_id} отправлено админу (ID сообщения: {sent_msg.message_id})")
        
        # Дополнительно отправляем уведомление со звуком
        bot.send_message(
            ADMIN_ID,
            f"🔔 <b>Внимание!</b> Новое обращение #{ticket_id}",
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось отправить админу: {e}")
        # Пробуем еще раз через 3 секунды
        time.sleep(3)
        try:
            bot.send_message(ADMIN_ID, admin_message, parse_mode='HTML')
            print("✅ Со второй попытки успешно!")
        except:
            print("❌ Вторая попытка тоже провалилась")

# ========== ОБРАБОТКА ПОИСКА ==========
@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id] == 'searching')
def handle_search(message):
    user_id = message.from_user.id
    query = message.text
    
    # Удаляем из состояния
    if user_id in user_state:
        del user_state[user_id]
    
    # Поиск
    msg = bot.send_message(message.chat.id, "🔍 Ищу...")
    films = search_film(query)
    bot.delete_message(message.chat.id, msg.message_id)
    
    if not films:
        bot.send_message(
            message.chat.id,
            "😕 Ничего не найдено. Попробуй другое название.",
            reply_markup=main_menu()
        )
        return
    
    for film in films:
        name = film.get('nameRu') or film.get('nameEn') or '?'
        year = film.get('year', '?')
        rating = film.get('rating', '?')
        desc = film.get('description', '')[:200]
        poster = film.get('posterUrl')
        
        text = f"🎬 <b>{name}</b> ({year})\n⭐ Рейтинг: {rating}\n\n{desc}"
        
        if poster:
            try:
                bot.send_photo(message.chat.id, poster, caption=text, parse_mode='HTML')
            except:
                bot.send_message(message.chat.id, text, parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, text, parse_mode='HTML')
    
    bot.send_message(message.chat.id, "✅ Поиск завершен!", reply_markup=main_menu())

# ========== ПОДПИСКА ==========
@bot.message_handler(func=lambda m: m.text == '⭐️ Подписка')
def subscription(message):
    text = f"""
⭐️ <b>Премиум подписка</b>

🔥 <b>Тарифы:</b>
• 1 месяц — 199₽
• 3 месяца — 499₽ (экономия 100₽)
• 6 месяцев — 899₽ (экономия 300₽)
• 12 месяцев — 1499₽ (экономия 900₽)

💳 <b>Карта для оплаты:</b>
<code>{YOUR_CARD}</code>

📞 <b>После оплаты</b> нажми "💬 Написать в поддержку" и пришли скриншот честа.
    """
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# ========== ПРОФИЛЬ ==========
@bot.message_handler(func=lambda m: m.text == '👤 Мой профиль')
def profile(message):
    user_id = message.from_user.id
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        text = f"""
👤 <b>Твой профиль</b>

🆔 ID: <code>{user_id}</code>
📱 Username: @{user[1] or 'нет'}
📅 Зарегистрирован: {user[5]}
        """
    else:
        text = "❌ Профиль не найден"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_menu())

# ========== ОТВЕТ АДМИНА ==========
@bot.message_handler(commands=['reply'])
def admin_reply(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Нет доступа")
        return
    
    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Используй: /reply [номер] [текст]")
            return
        
        ticket_id = int(parts[1])
        reply_text = parts[2]
        
        # Получаем данные тикета
        cursor.execute('SELECT user_id FROM tickets WHERE id = ?', (ticket_id,))
        result = cursor.fetchone()
        
        if not result:
            bot.reply_to(message, "❌ Тикет не найден")
            return
        
        user_id = result[0]
        
        # Отправляем ответ пользователю
        try:
            bot.send_message(
                user_id,
                f"📨 <b>Ответ от поддержки по обращению #{ticket_id}:</b>\n\n{reply_text}",
                parse_mode='HTML'
            )
        except Exception as e:
            bot.reply_to(message, f"❌ Не удалось отправить пользователю: {e}")
            return
        
        # Обновляем тикет
        cursor.execute('UPDATE tickets SET status = "closed", answer = ? WHERE id = ?',
                      (reply_text, ticket_id))
        conn.commit()
        
        bot.reply_to(message, f"✅ Ответ на тикет #{ticket_id} отправлен!")
        
    except ValueError:
        bot.reply_to(message, "❌ Номер тикета должен быть числом")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== АДМИНКА ==========
@bot.message_handler(func=lambda m: m.text == '📊 Статистика' and m.from_user.id == ADMIN_ID)
def admin_stats(message):
    cursor.execute('SELECT COUNT(*) FROM users')
    users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tickets WHERE status = "open"')
    open_tickets = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tickets')
    total_tickets = cursor.fetchone()[0]
    
    text = f"""
📊 <b>Статистика бота</b>

👥 Пользователей: {users}
📨 Всего обращений: {total_tickets}
🟢 Открытых тикетов: {open_tickets}
    """
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '📨 Открытые тикеты' and m.from_user.id == ADMIN_ID)
def admin_tickets(message):
    cursor.execute('''
        SELECT t.*, u.username, u.first_name 
        FROM tickets t
        JOIN users u ON t.user_id = u.user_id
        WHERE t.status = 'open'
        ORDER BY t.created_at DESC
    ''')
    tickets = cursor.fetchall()
    
    if not tickets:
        bot.send_message(message.chat.id, "📨 Нет открытых тикетов")
        return
    
    for t in tickets:
        text = f"""
📨 <b>Тикет #{t[0]}</b>

👤 От: @{t[6] or 'нет'} ({t[7]})
📅 Создан: {t[4]}

💬 <b>Сообщение:</b>
{t[2]}

━━━━━━━━━━━━━━━━
<b>Ответить:</b> <code>/reply {t[0]} [текст]</code>
        """
        bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '🔑 Выдать подписку' and m.from_user.id == ADMIN_ID)
def give_sub_prompt(message):
    bot.send_message(
        message.chat.id,
        "🔑 Введи ID пользователя и количество месяцев через пробел\nНапример: 123456789 3"
    )
    bot.register_next_step_handler(message, give_sub_process)

def give_sub_process(message):
    try:
        parts = message.text.split()
        user_id = int(parts[0])
        months = int(parts[1])
        
        until = (datetime.datetime.now() + datetime.timedelta(days=30*months)).strftime("%Y-%m-%d")
        cursor.execute('UPDATE users SET subscribed = 1, sub_until = ? WHERE user_id = ?', (until, user_id))
        conn.commit()
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                user_id,
                f"🎉 <b>Вам выдана подписка!</b>\n\nДействует до: {until}",
                parse_mode='HTML'
            )
        except:
            pass
        
        bot.reply_to(message, f"✅ Подписка выдана пользователю {user_id}")
    except:
        bot.reply_to(message, "❌ Ошибка. Используй: ID месяц")

@bot.message_handler(func=lambda m: m.text == '📢 Рассылка' and m.from_user.id == ADMIN_ID)
def broadcast_prompt(message):
    bot.send_message(message.chat.id, "📢 Введи текст для рассылки всем пользователям:")
    bot.register_next_step_handler(message, broadcast_process)

def broadcast_process(message):
    text = message.text
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    
    sent = 0
    failed = 0
    
    msg = bot.send_message(message.chat.id, "📢 Начинаю рассылку...")
    
    for user in users:
        try:
            bot.send_message(user[0], f"📢 <b>Рассылка</b>\n\n{text}", parse_mode='HTML')
            sent += 1
            time.sleep(0.1)  # Небольшая задержка
        except:
            failed += 1
    
    bot.edit_message_text(
        f"✅ Рассылка завершена!\n\n📨 Отправлено: {sent}\n❌ Не доставлено: {failed}",
        message.chat.id,
        msg.message_id
    )

@bot.message_handler(func=lambda m: m.text == '◀️ Выйти из админки' and m.from_user.id == ADMIN_ID)
def exit_admin(message):
    bot.send_message(message.chat.id, "👋 Выход из админки", reply_markup=main_menu())

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🎬 БОТ ДЛЯ ПОИСКА ФИЛЬМОВ")
    print("=" * 60)
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"💳 Карта: {YOUR_CARD}")
    print("=" * 60)
    print("🚀 Бот запущен!")
    print("📨 Режим поддержки АКТИВЕН")
    print("=" * 60)
    
    # Отправляем приветствие админу
    try:
        bot.send_message(
            ADMIN_ID,
            "✅ <b>Бот успешно перезапущен!</b>\n\n"
            "📨 <b>Поддержка работает так:</b>\n"
            "1. Пользователь нажимает '💬 Написать в поддержку'\n"
            "2. Пишет сообщение\n"
            "3. Тебе сюда приходит уведомление\n\n"
            "📝 <b>Чтобы ответить:</b> /reply [номер] [текст]",
            parse_mode='HTML'
        )
        print("✅ Приветствие отправлено админу")
    except Exception as e:
        print(f"❌ Не удалось отправить приветствие: {e}")
    
    print("=" * 60)
    bot.infinity_polling()
