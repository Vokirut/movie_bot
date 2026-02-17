import telebot
import requests
import os
import datetime
import sqlite3
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загрузка токена
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ Ошибка: Токен не найден в .env файле!")
    exit(1)

# ТВОЙ ID АДМИНА
ADMIN_ID = 635440209

bot = telebot.TeleBot(BOT_TOKEN)

# ========== ПРОСТАЯ БАЗА ДАННЫХ ==========

def init_db():
    conn = sqlite3.connect('movies.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Таблица пользователей
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
    
    # Таблица для поддержки
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
    return conn, cursor

conn, cursor = init_db()

# ========== ПРОСТЫЕ ФУНКЦИИ ДЛЯ БД ==========

def add_user(user_id, username, first_name):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, now))
    conn.commit()

def check_sub(user_id):
    cursor.execute('SELECT subscribed, sub_until FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result and result[0] == 1 and result[1]:
        try:
            until = datetime.datetime.strptime(result[1], "%Y-%m-%d")
            return until > datetime.datetime.now()
        except:
            return False
    return False

def give_sub(user_id, months):
    now = datetime.datetime.now()
    until = now + datetime.timedelta(days=30*months)
    until_str = until.strftime("%Y-%m-%d")
    cursor.execute('''
        UPDATE users SET subscribed = 1, sub_until = ? WHERE user_id = ?
    ''', (until_str, user_id))
    conn.commit()
    return until_str

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

# ========== КЛАВИАТУРЫ ==========

def main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ['🔍 Поиск', '⭐ Подписка', '💬 Поддержка', '👤 Профиль']
    
    if is_admin(user_id):
        buttons.append('⚙️ Админка')
    
    markup.add(*buttons)
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        '📊 Статистика',
        '🔑 Выдать подписку',
        '📨 Тикеты',
        '📢 Рассылка',
        '◀️ Назад'
    )
    return markup

def sub_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("⭐ 1 месяц - 199₽", callback_data="sub_1"),
        InlineKeyboardButton("⭐ 3 месяца - 499₽", callback_data="sub_3"),
        InlineKeyboardButton("⭐ 6 месяцев - 899₽", callback_data="sub_6"),
        InlineKeyboardButton("⭐ 12 месяцев - 1499₽", callback_data="sub_12")
    )
    return markup

# ========== ПОИСК ФИЛЬМОВ ==========

def search_film(query):
    url = f"https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword={query}"
    headers = {'X-API-KEY': '8c8e7a9c-8b5c-4b3e-9f5a-3d5c5e5f7b8a'}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get('films', [])[:5]
    except:
        pass
    return []

# ========== КОМАНДЫ ==========

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "Друг"
    username = message.from_user.username
    
    add_user(user_id, username, name)
    
    # Если это админ - назначаем
    if user_id == ADMIN_ID:
        cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        print(f"👑 Админ {user_id} авторизован")
    
    text = f"""
🎬 <b>Привет, {name}!</b>

Я бот для поиска фильмов. Что умею:

🔍 <b>Поиск фильмов</b> - информация, постеры, рейтинг
⭐ <b>Подписка</b> - доступ к просмотру
💬 <b>Поддержка</b> - помощь 24/7
👤 <b>Профиль</b> - твои данные

Просто нажимай кнопки и пользуйся!
    """
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=main_menu(user_id)
    )

# ========== ПОИСК ==========

@bot.message_handler(func=lambda m: m.text == '🔍 Поиск')
def ask_film(message):
    bot.send_message(
        message.chat.id,
        "🎬 <b>Введи название фильма:</b>",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add('❌ Отмена')
    )

@bot.message_handler(func=lambda m: m.text and m.text not in ['🔍 Поиск', '⭐ Подписка', '💬 Поддержка', '👤 Профиль', '⚙️ Админка', '❌ Отмена', '◀️ Назад'])
def search_handler(message):
    query = message.text
    msg = bot.send_message(message.chat.id, "🔎 Ищу...")
    
    films = search_film(query)
    bot.delete_message(message.chat.id, msg.message_id)
    
    if not films:
        bot.send_message(
            message.chat.id,
            "😕 Ничего не найдено. Попробуй другое название.",
            reply_markup=main_menu(message.from_user.id)
        )
        return
    
    for film in films:
        name = film.get('nameRu') or film.get('nameEn') or '?'
        year = film.get('year', '?')
        rating = film.get('rating', '?')
        desc = film.get('description', '')[:200]
        poster = film.get('posterUrl')
        film_id = film.get('filmId')
        
        text = f"🎬 <b>{name}</b> ({year})\n⭐ Рейтинг: {rating}\n\n{desc}"
        
        markup = None
        if check_sub(message.from_user.id):
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(
                "🎬 Смотреть",
                url=f"https://www.kinopoisk.ru/film/{film_id}/"
            ))
        
        if poster:
            try:
                bot.send_photo(
                    message.chat.id,
                    poster,
                    caption=text,
                    parse_mode='HTML',
                    reply_markup=markup
                )
            except:
                bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)
    
    bot.send_message(
        message.chat.id,
        "✅ Готово!",
        reply_markup=main_menu(message.from_user.id)
    )

# ========== ПОДПИСКА ==========

@bot.message_handler(func=lambda m: m.text == '⭐ Подписка')
def sub_info(message):
    if check_sub(message.from_user.id):
        text = "✅ <b>У тебя есть подписка!</b>\n\nСпасибо за поддержку!"
    else:
        text = """
⭐ <b>Премиум подписка</b>

🔥 <b>Тарифы:</b>
• 1 месяц — 199₽
• 3 месяца — 499₽ (экономия 100₽)
• 6 месяцев — 899₽ (экономия 300₽)
• 12 месяцев — 1499₽ (экономия 900₽)

💳 <b>Оплата:</b> Сбербанк
💳 <b>Карта:</b> 2202 2081 7050 3883
📞 <b>После оплаты:</b> напиши в поддержку и пришли чек
        """
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=sub_menu()
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith('sub_'))
def sub_choose(call):
    months = {'sub_1': 1, 'sub_3': 3, 'sub_6': 6, 'sub_12': 12}
    price = {'sub_1': 199, 'sub_3': 499, 'sub_6': 899, 'sub_12': 1499}
    
    m = months.get(call.data, 1)
    p = price.get(call.data, 199)
    
    text = f"""
💳 <b>Оплата подписки</b>

Тариф: {m} месяц(ев)
Сумма: {p}₽

<b>Реквизиты:</b>
💳 Карта: 2202 2081 7050 3883
👤 Получатель: Никита С.

<b>Как получить подписку:</b>
1️⃣ Переведи {p}₽ на карту
2️⃣ Сохрани чек (скриншот)
3️⃣ Напиши в 💬 Поддержка
4️⃣ Пришли чек
    """
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )

# ========== ПОДДЕРЖКА ==========

@bot.message_handler(func=lambda m: m.text == '💬 Поддержка')
def support_start(message):
    bot.send_message(
        message.chat.id,
        "📝 <b>Напиши свой вопрос:</b>\n\nОпиши проблему подробно, админ ответит в ближайшее время.",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add('❌ Отмена')
    )

@bot.message_handler(func=lambda m: m.text and m.text not in ['🔍 Поиск', '⭐ Подписка', '💬 Поддержка', '👤 Профиль', '⚙️ Админка', '❌ Отмена', '◀️ Назад'])
def support_message(message):
    user_id = message.from_user.id
    text = message.text
    
    # Сохраняем в БД
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO tickets (user_id, message, created_at)
        VALUES (?, ?, ?)
    ''', (user_id, text, now))
    conn.commit()
    ticket_id = cursor.lastrowid
    
    print(f"📨 Новый тикет #{ticket_id} от пользователя {user_id}")
    
    # Отправляем админу
    try:
        admin_text = f"""
📨 <b>Новое обращение #{ticket_id}</b>

👤 От: @{message.from_user.username or 'нет'} (ID: {user_id})
👤 Имя: {message.from_user.first_name}
💬 Сообщение: {text}

Ответить: /reply {ticket_id} [текст]
        """
        bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML')
        print(f"✅ Уведомление отправлено админу {ADMIN_ID}")
    except Exception as e:
        print(f"❌ Ошибка отправки админу: {e}")
    
    bot.send_message(
        message.chat.id,
        f"✅ <b>Обращение #{ticket_id} принято!</b>\n\nАдмин ответит в ближайшее время.",
        parse_mode='HTML',
        reply_markup=main_menu(user_id)
    )

@bot.message_handler(commands=['reply'])
def reply_ticket(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У тебя нет прав администратора")
        return
    
    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Используй: /reply [номер] [текст]")
            return
            
        ticket_id = int(parts[1])
        answer = parts[2]
        
        # Получаем user_id
        cursor.execute('SELECT user_id FROM tickets WHERE id = ?', (ticket_id,))
        result = cursor.fetchone()
        
        if result:
            user_id = result[0]
            
            # Отправляем ответ пользователю
            try:
                bot.send_message(
                    user_id,
                    f"📨 <b>Ответ от поддержки по обращению #{ticket_id}:</b>\n\n{answer}",
                    parse_mode='HTML'
                )
            except Exception as e:
                bot.reply_to(message, f"❌ Не удалось отправить пользователю: {e}")
                return
            
            # Обновляем тикет
            cursor.execute('''
                UPDATE tickets SET status = 'closed', answer = ? WHERE id = ?
            ''', (answer, ticket_id))
            conn.commit()
            
            bot.reply_to(message, f"✅ Ответ на тикет #{ticket_id} отправлен!")
        else:
            bot.reply_to(message, "❌ Тикет не найден")
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
        sub_status = "✅ Есть" if check_sub(user_id) else "❌ Нет"
        text = f"""
👤 <b>Твой профиль</b>

🆔 ID: <code>{user_id}</code>
📱 Username: @{user[1] or 'нет'}
👋 Имя: {user[2]}
📅 Зарегистрирован: {user[5]}
⭐ Подписка: {sub_status}
        """
    else:
        text = "❌ Профиль не найден"
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=main_menu(user_id)
    )

# ========== АДМИНКА ==========

@bot.message_handler(func=lambda m: m.text == '⚙️ Админка')
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Нет доступа")
        return
    bot.send_message(message.chat.id, "⚙️ Админ панель", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == '📊 Статистика')
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
    subs = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tickets WHERE status = "open"')
    tickets = cursor.fetchone()[0]
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"""
📊 <b>Статистика на {now}</b>

👥 Всего пользователей: {total_users}
⭐ Подписчиков: {subs}
📨 Открытых тикетов: {tickets}
    """
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '📨 Тикеты')
def admin_tickets(message):
    if message.from_user.id != ADMIN_ID:
        return
    
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

Ответить: <code>/reply {t[0]} [текст]</code>
        """
        bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '🔑 Выдать подписку')
def admin_give_sub(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    bot.send_message(
        message.chat.id,
        "🔑 Введи ID пользователя и количество месяцев через пробел\nНапример: 123456789 3"
    )
    bot.register_next_step_handler(message, give_sub_process)

def give_sub_process(message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Используй: [ID] [месяцы]")
            return
            
        user_id = int(parts[0])
        months = int(parts[1])
        
        until = give_sub(user_id, months)
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                user_id,
                f"🎉 <b>Тебе выдана подписка!</b>\n\nДействует до: {until}",
                parse_mode='HTML'
            )
            bot.reply_to(message, f"✅ Подписка выдана пользователю {user_id}")
        except:
            bot.reply_to(message, f"✅ Подписка выдана, но пользователь {user_id} не найден или заблокировал бота")
    except ValueError:
        bot.reply_to(message, "❌ ID и месяцы должны быть числами")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda m: m.text == '📢 Рассылка')
def admin_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    bot.send_message(
        message.chat.id,
        "📢 Введи текст для рассылки (отправлю всем пользователям):"
    )
    bot.register_next_step_handler(message, broadcast_process)

def broadcast_process(message):
    text = message.text
    
    msg = bot.send_message(message.chat.id, "📢 Начинаю рассылку...")
    
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(
                user[0],
                f"📢 <b>Рассылка от администрации</b>\n\n{text}",
                parse_mode='HTML'
            )
            sent += 1
        except:
            failed += 1
    
    bot.edit_message_text(
        f"✅ Рассылка завершена!\n\n📨 Отправлено: {sent}\n❌ Не доставлено: {failed}",
        message.chat.id,
        msg.message_id
    )

# ========== ОТМЕНА И НАЗАД ==========

@bot.message_handler(func=lambda m: m.text == '❌ Отмена')
def cancel(message):
    bot.send_message(
        message.chat.id,
        "❌ Отменено",
        reply_markup=main_menu(message.from_user.id)
    )

@bot.message_handler(func=lambda m: m.text == '◀️ Назад')
def back(message):
    bot.send_message(
        message.chat.id,
        "◀️ Главное меню",
        reply_markup=main_menu(message.from_user.id)
    )

# ========== ЗАПУСК ==========

print("=" * 50)
print("🎬 БОТ ДЛЯ ПОИСКА ФИЛЬМОВ")
print("=" * 50)
print(f"✅ Твой ID администратора: {ADMIN_ID}")
print(f"✅ Номер карты: 2202 2081 7050 3883")
print("✅ Бот запущен!")
print("🔄 Ctrl+C для остановки")
print("=" * 50)
print("📨 Сообщения в поддержку будут приходить сюда")
print("=" * 50)

bot.infinity_polling()
