import telebot
import requests
import os
import datetime
import sqlite3
import time
import threading
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
        return r.json().get('films', [])[:5] if r.status_code == 200 else []
    except:
        return []

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🔍 Поиск', '⭐ Подписка')
    markup.add('💬 Поддержка', '👤 Профиль')
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📊 Статистика', '📨 Тикеты')
    markup.add('🔑 Выдать подписку', '📢 Рассылка')
    markup.add('◀️ Назад')
    return markup

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "Друг"
    add_user(user_id, message.from_user.username, name)
    
    # Приветствие админа
    if user_id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            f"👑 <b>Привет, Админ!</b>\n\nТвой ID: {user_id}\nБот работает и ждет сообщений в поддержку.",
            parse_mode='HTML',
            reply_markup=admin_menu()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"🎬 <b>Привет, {name}!</b>\n\nЯ помогу найти любой фильм!",
            parse_mode='HTML',
            reply_markup=main_menu()
        )

# ========== ПОИСК ==========
@bot.message_handler(func=lambda m: m.text == '🔍 Поиск')
def search_prompt(message):
    bot.send_message(
        message.chat.id,
        "🎬 Введи название фильма:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add('❌ Отмена')
    )

@bot.message_handler(func=lambda m: m.text and m.text not in ['🔍 Поиск', '⭐ Подписка', '💬 Поддержка', '👤 Профиль', '📊 Статистика', '📨 Тикеты', '🔑 Выдать подписку', '📢 Рассылка', '❌ Отмена', '◀️ Назад'])
def handle_search(message):
    query = message.text
    msg = bot.send_message(message.chat.id, "🔍 Ищу...")
    films = search_film(query)
    bot.delete_message(message.chat.id, msg.message_id)
    
    if not films:
        bot.send_message(message.chat.id, "😕 Ничего не найдено", reply_markup=main_menu())
        return
    
    for film in films:
        name = film.get('nameRu') or film.get('nameEn') or '?'
        year = film.get('year', '?')
        rating = film.get('rating', '?')
        desc = film.get('description', '')[:200]
        poster = film.get('posterUrl')
        
        text = f"🎬 <b>{name}</b> ({year})\n⭐ {rating}\n\n{desc}"
        
        if poster:
            try:
                bot.send_photo(message.chat.id, poster, caption=text, parse_mode='HTML')
            except:
                bot.send_message(message.chat.id, text, parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, text, parse_mode='HTML')
    
    bot.send_message(message.chat.id, "✅ Готово!", reply_markup=main_menu())

# ========== ПОДПИСКА ==========
@bot.message_handler(func=lambda m: m.text == '⭐ Подписка')
def subscription(message):
    text = f"""
⭐ <b>Премиум подписка</b>

🔥 <b>Тарифы:</b>
• 1 месяц — 199₽
• 3 месяца — 499₽
• 6 месяцев — 899₽
• 12 месяцев — 1499₽

💳 <b>Карта для оплаты:</b>
<code>{YOUR_CARD}</code>

📞 <b>После оплаты</b> напиши в поддержку и пришли скриншот чека.
    """
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# ========== ПОДДЕРЖКА (ИСПРАВЛЕННАЯ) ==========
@bot.message_handler(func=lambda m: m.text == '💬 Поддержка')
def support_start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('❌ Отмена')
    
    bot.send_message(
        message.chat.id,
        "📝 <b>Напиши свой вопрос:</b>\n\nЯ передам его администратору.",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text and m.text not in ['🔍 Поиск', '⭐ Подписка', '💬 Поддержка', '👤 Профиль', '❌ Отмена', '◀️ Назад'])
def handle_support(message):
    user_id = message.from_user.id
    user_text = message.text
    username = message.from_user.username or "нет"
    first_name = message.from_user.first_name or "Пользователь"
    
    # Сохраняем в БД
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('INSERT INTO tickets (user_id, message, created_at) VALUES (?, ?, ?)',
                  (user_id, user_text, now))
    conn.commit()
    ticket_id = cursor.lastrowid
    
    # Отправляем пользователю подтверждение
    bot.send_message(
        user_id,
        f"✅ <b>Обращение #{ticket_id} принято!</b>\n\nАдмин ответит в ближайшее время.",
        parse_mode='HTML',
        reply_markup=main_menu()
    )
    
    # ===== ВАЖНО: Отправляем тебе сообщение =====
    admin_text = f"""
📨 <b>НОВОЕ ОБРАЩЕНИЕ #{ticket_id}</b>

👤 <b>От:</b> {first_name}
🆔 <b>ID:</b> <code>{user_id}</code>
📱 <b>Username:</b> @{username}
💬 <b>Сообщение:</b>
{user_text}

⏰ <b>Время:</b> {now}

━━━━━━━━━━━━━━━━
<b>Чтобы ответить, отправь:</b>
<code>/reply {ticket_id} Ваш ответ</code>
    """
    
    # Пробуем отправить 3 раза с интервалом
    for attempt in range(3):
        try:
            bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML')
            print(f"✅ Уведомление о тикете #{ticket_id} отправлено админу (попытка {attempt+1})")
            break
        except Exception as e:
            print(f"❌ Ошибка отправки админу (попытка {attempt+1}): {e}")
            time.sleep(2)

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

# ========== ПРОФИЛЬ ==========
@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(message):
    user_id = message.from_user.id
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        text = f"""
👤 <b>Твой профиль</b>

🆔 ID: <code>{user_id}</code>
📱 Username: @{user[1] or 'нет'}
📅 Дата регистрации: {user[5]}
        """
    else:
        text = "❌ Профиль не найден"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_menu())

# ========== АДМИНКА ==========
@bot.message_handler(func=lambda m: m.text == '📊 Статистика' and m.from_user.id == ADMIN_ID)
def admin_stats(message):
    cursor.execute('SELECT COUNT(*) FROM users')
    users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tickets WHERE status = "open"')
    tickets = cursor.fetchone()[0]
    
    text = f"""
📊 <b>Статистика</b>

👥 Пользователей: {users}
📨 Открытых тикетов: {tickets}
    """
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '📨 Тикеты' and m.from_user.id == ADMIN_ID)
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
📅 {t[4]}

💬 {t[2]}

Ответить: <code>/reply {t[0]} [текст]</code>
        """
        bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '🔑 Выдать подписку' and m.from_user.id == ADMIN_ID)
def give_sub_prompt(message):
    bot.send_message(message.chat.id, "🔑 Введи ID пользователя и количество месяцев через пробел")
    bot.register_next_step_handler(message, give_sub_process)

def give_sub_process(message):
    try:
        user_id, months = map(int, message.text.split())
        until = (datetime.datetime.now() + datetime.timedelta(days=30*months)).strftime("%Y-%m-%d")
        cursor.execute('UPDATE users SET subscribed = 1, sub_until = ? WHERE user_id = ?', (until, user_id))
        conn.commit()
        bot.reply_to(message, f"✅ Подписка выдана пользователю {user_id}")
    except:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(func=lambda m: m.text == '📢 Рассылка' and m.from_user.id == ADMIN_ID)
def broadcast_prompt(message):
    bot.send_message(message.chat.id, "📢 Введи текст для рассылки:")
    bot.register_next_step_handler(message, broadcast_process)

def broadcast_process(message):
    text = message.text
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 <b>Рассылка</b>\n\n{text}", parse_mode='HTML')
            sent += 1
            time.sleep(0.3)  # Чтобы не забанили
        except:
            pass
    
    bot.reply_to(message, f"✅ Отправлено {sent} пользователям")

# ========== ОТМЕНА ==========
@bot.message_handler(func=lambda m: m.text == '❌ Отмена')
def cancel(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Отменено", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "❌ Отменено", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == '◀️ Назад' and m.from_user.id == ADMIN_ID)
def back_to_admin(message):
    bot.send_message(message.chat.id, "◀️ Админка", reply_markup=admin_menu())

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("=" * 50)
    print("🎬 БОТ ДЛЯ ПОИСКА ФИЛЬМОВ")
    print("=" * 50)
    print(f"✅ Твой ID: {ADMIN_ID}")
    print(f"✅ Твоя карта: {YOUR_CARD}")
    print("✅ Бот запущен!")
    print("=" * 50)
    print("📨 Сейчас проверим поддержку...")
    print("=" * 50)
    
    # Отправляем тестовое сообщение админу при запуске
    try:
        bot.send_message(
            ADMIN_ID,
            "✅ <b>Бот успешно запущен!</b>\n\nТеперь ты будешь получать уведомления о новых обращениях в поддержку.",
            parse_mode='HTML'
        )
        print("✅ Тестовое сообщение отправлено админу")
    except Exception as e:
        print(f"❌ Не удалось отправить тестовое сообщение: {e}")
        print("⚠️ Проверь: не заблокировал ли ты бота?")
    
    print("=" * 50)
    bot.infinity_polling()
