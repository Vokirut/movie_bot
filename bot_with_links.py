import telebot
import os
import requests
import datetime
import urllib.parse
import re
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 635440209
CARD_NUMBER = "2202 2081 7050 3883"

# ⭐ ТВОЙ API КЛЮЧ
KINOPOISK_API_KEY = "KSBPX6X-M124ZM3-MWJMXHE-W9NZZK1"

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище режимов
user_mode = {}
tickets = {}
ticket_counter = 0

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('🔍 Поиск'),
        KeyboardButton('⭐ Подписка'),
        KeyboardButton('📞 Поддержка'),
        KeyboardButton('👤 Профиль'),
        KeyboardButton('❓ Помощь')
    )
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('📨 Тикеты'),
        KeyboardButton('📊 Статистика'),
        KeyboardButton('◀️ Назад')
    )
    return markup

def cancel_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('❌ Отмена'))
    return markup

# ========== ПОИСК ФИЛЬМОВ ==========
def search_movie(query):
    url = f"https://api.kinopoisk.dev/v1.4/movie/search?page=1&limit=5&query={query}"
    headers = {
        'X-API-KEY': KINOPOISK_API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            films = data.get('docs', [])
            results = []
            for film in films:
                results.append({
                    'name': film.get('name', 'Неизвестно'),
                    'year': film.get('year', 'Неизвестно'),
                    'rating': film.get('rating', {}).get('kp', '?'),
                    'description': film.get('description', 'Описание отсутствует'),
                    'poster': film.get('poster', {}).get('url', None)
                })
            return results[:5]
        return []
    except:
        return []

# ========== НОВЫЙ ПАРСЕР ССЫЛОК ==========
def get_watch_links(movie_name, movie_year):
    """
    Парсит ссылки на просмотр фильма с разных сайтов
    """
    # Кодируем название для URL
    query = urllib.parse.quote(f"{movie_name} {movie_year}")
    search_query = urllib.parse.quote(f"{movie_name} {movie_year} смотреть онлайн")
    
    # База киносайтов (можно легко добавлять новые)
    sites = [
        {
            "name": "🎬 Кинопоиск",
            "url": f"https://www.kinopoisk.ru/index.php?kp_query={query}",
            "icon": "🎬"
        },
        {
            "name": "📺 YouTube",
            "url": f"https://www.youtube.com/results?search_query={search_query}",
            "icon": "📺"
        },
        {
            "name": "🎥 HDRezka",
            "url": f"https://hdrezka.ag/index.php?do=search&subaction=search&q={query}",
            "icon": "🎥"
        },
        {
            "name": "🍿 Filmix",
            "url": f"https://filmix.ac/search/{query}/",
            "icon": "🍿"
        },
        {
            "name": "🎞️ LordFilm",
            "url": f"https://v5.lordfilm.black/index.php?do=search&subaction=search&q={query}",
            "icon": "🎞️"
        },
        {
            "name": "🎬 Киного",
            "url": f"https://kinogo.biz/index.php?do=search&subaction=search&story={query}",
            "icon": "🎬"
        },
        {
            "name": "📱 VK Видео",
            "url": f"https://vkvideo.ru/video/search?q={search_query}",
            "icon": "📱"
        },
        {
            "name": "🌐 Mail.ru",
            "url": f"https://video.mail.ru/search?q={search_query}",
            "icon": "🌐"
        }
    ]
    
    # Добавляем торрент-трекеры (для продвинутых пользователей)
    torrent_sites = [
        {
            "name": "⚡ RuTracker",
            "url": f"http://rutracker.org/forum/tracker.php?nm={query}",
            "icon": "⚡"
        },
        {
            "name": "⚡ RuTor",
            "url": f"https://rutor.info/search/{query}",
            "icon": "⚡"
        }
    ]
    
    return sites + torrent_sites

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id in user_mode:
        del user_mode[user_id]
    
    if user_id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            f"👑 <b>Админ панель</b>\nID: {user_id}",
            parse_mode='HTML',
            reply_markup=admin_menu()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"👋 <b>Привет, {message.from_user.first_name}!</b>\n\n"
            f"🎬 Теперь я умею не только искать фильмы, но и давать ссылки на просмотр!",
            parse_mode='HTML',
            reply_markup=main_menu()
        )

# ========== ПРОФИЛЬ ==========
@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(m):
    bot.send_message(
        m.chat.id,
        f"👤 <b>Твой профиль</b>\n\n🆔 ID: <code>{m.from_user.id}</code>",
        parse_mode='HTML',
        reply_markup=main_menu()
    )

# ========== ПОДПИСКА ==========
@bot.message_handler(func=lambda m: m.text == '⭐ Подписка')
def subscription(m):
    text = f"""
⭐ <b>Премиум подписка</b>

🔥 <b>Тарифы:</b>
• 1 месяц — 199₽
• 3 месяца — 499₽
• 6 месяцев — 899₽
• 12 месяцев — 1499₽

💳 <b>Карта:</b> <code>{CARD_NUMBER}</code>

📞 <b>После оплаты</b> напиши в поддержку и пришли скриншот.

🎁 <b>Бонус:</b> Подписчики получают доступ к торрент-трекерам!
    """
    bot.send_message(m.chat.id, text, parse_mode='HTML', reply_markup=main_menu())

# ========== ПОМОЩЬ ==========
@bot.message_handler(func=lambda m: m.text == '❓ Помощь')
def help_msg(m):
    text = """
❓ <b>Как пользоваться:</b>

🔍 <b>Поиск</b> - найди любой фильм
⭐ <b>Подписка</b> - купи доступ
📞 <b>Поддержка</b> - связь с админом
👤 <b>Профиль</b> - твой ID

🎬 <b>Новая функция!</b>
После поиска фильма ты увидишь кнопки с ссылками на просмотр:
• Кинопоиск
• YouTube
• HDRezka
• Filmix
• И другие...

📝 <b>Примеры поиска:</b>
• Аватар
• Матрица
• Титаник
• 1+1
    """
    bot.send_message(m.chat.id, text, parse_mode='HTML', reply_markup=main_menu())

# ========== ПОИСК ==========
@bot.message_handler(func=lambda m: m.text == '🔍 Поиск')
def search_start(m):
    user_mode[m.from_user.id] = 'search'
    bot.send_message(
        m.chat.id,
        "🎬 <b>Введи название фильма:</b>",
        parse_mode='HTML',
        reply_markup=cancel_menu()
    )

# ========== ПОДДЕРЖКА ==========
@bot.message_handler(func=lambda m: m.text == '📞 Поддержка')
def support_start(m):
    user_mode[m.from_user.id] = 'support'
    bot.send_message(
        m.chat.id,
        "📝 <b>Напиши сообщение для админа:</b>",
        parse_mode='HTML',
        reply_markup=cancel_menu()
    )

# ========== ОТМЕНА ==========
@bot.message_handler(func=lambda m: m.text == '❌ Отмена')
def cancel(m):
    user_id = m.from_user.id
    if user_id in user_mode:
        del user_mode[user_id]
    
    if user_id == ADMIN_ID:
        bot.send_message(m.chat.id, "❌ Отменено", reply_markup=admin_menu())
    else:
        bot.send_message(m.chat.id, "❌ Отменено", reply_markup=main_menu())

# ========== АДМИНКА ==========
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in ['📨 Тикеты', '📊 Статистика', '◀️ Назад'])
def admin_commands(m):
    if m.text == '◀️ Назад':
        bot.send_message(m.chat.id, "👋 Выход", reply_markup=admin_menu())
    
    elif m.text == '📊 Статистика':
        bot.send_message(m.chat.id, f"📊 Статистика:\n👥 Всего тикетов: {len(tickets)}")

    elif m.text == '📨 Тикеты':
        if not tickets:
            bot.send_message(m.chat.id, "📨 Нет новых тикетов")
        else:
            for ticket_id, (user_id, user_msg) in list(tickets.items()):
                bot.send_message(
                    m.chat.id,
                    f"📨 <b>Тикет #{ticket_id}</b>\n"
                    f"👤 ID: {user_id}\n"
                    f"💬 {user_msg[:100]}\n\n"
                    f"👉 /reply {ticket_id} [текст]",
                    parse_mode='HTML'
                )

# ========== ОТВЕТ АДМИНА ==========
@bot.message_handler(commands=['reply'])
def admin_reply(m):
    if m.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = m.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(m, "❌ Используй: /reply [номер] [текст]")
            return
        
        ticket_id = int(parts[1])
        reply_text = parts[2]
        
        if ticket_id in tickets:
            user_id, _ = tickets[ticket_id]
            
            bot.send_message(
                user_id,
                f"📨 <b>Ответ от поддержки:</b>\n\n{reply_text}",
                parse_mode='HTML'
            )
            
            del tickets[ticket_id]
            bot.reply_to(m, f"✅ Ответ отправлен пользователю {user_id}")
        else:
            bot.reply_to(m, "❌ Тикет не найден")
    except Exception as e:
        bot.reply_to(m, f"❌ Ошибка: {e}")

# ========== ОБРАБОТКА СООБЩЕНИЙ (ОСНОВНАЯ) ==========
@bot.message_handler(func=lambda m: True)
def handle_all(m):
    global ticket_counter
    user_id = m.from_user.id
    text = m.text
    
    # ПОДДЕРЖКА
    if user_id in user_mode and user_mode[user_id] == 'support':
        del user_mode[user_id]
        
        ticket_counter += 1
        ticket_id = ticket_counter
        tickets[ticket_id] = (user_id, text)
        
        bot.send_message(
            user_id,
            f"✅ <b>Обращение #{ticket_id} принято!</b>\n\nАдмин ответит в ближайшее время.",
            parse_mode='HTML',
            reply_markup=main_menu()
        )
        
        bot.send_message(
            ADMIN_ID,
            f"📨 <b>Новое обращение #{ticket_id}</b>\n\n"
            f"👤 От: @{m.from_user.username or 'нет'} (ID:{user_id})\n"
            f"💬 Сообщение:\n{text}\n\n"
            f"👉 /reply {ticket_id} [ответ]",
            parse_mode='HTML'
        )
        return
    
    # ПОИСК (С НОВЫМИ КНОПКАМИ ПРОСМОТРА)
    if user_id in user_mode and user_mode[user_id] == 'search':
        del user_mode[user_id]
        
        status_msg = bot.send_message(user_id, "🔍 <i>Ищу...</i>", parse_mode='HTML')
        films = search_movie(text)
        bot.delete_message(user_id, status_msg.message_id)
        
        if not films:
            bot.send_message(
                user_id,
                "😕 <b>Ничего не найдено</b>\n\nПопробуй другое название.",
                parse_mode='HTML',
                reply_markup=main_menu()
            )
            return
        
        for film in films:
            name = film.get('name', 'Неизвестно')
            year = film.get('year', 'Неизвестно')
            rating = film.get('rating', '?')
            desc = film.get('description', '')[:200]
            poster = film.get('poster')
            
            answer = f"🎬 <b>{name}</b> ({year})\n⭐ Рейтинг: {rating}\n\n{desc}"
            
            # ПОЛУЧАЕМ ССЫЛКИ ДЛЯ ПРОСМОТРА
            watch_links = get_watch_links(name, year)
            
            # Проверяем подписку (если есть - показываем все ссылки, если нет - только основные)
            # Пока для всех показываем все ссылки
            markup = InlineKeyboardMarkup(row_width=1)
            
            # Добавляем основные киносайты (первые 5)
            for link in watch_links[:5]:
                markup.add(InlineKeyboardButton(
                    f"{link['icon']} {link['name']}", 
                    url=link['url']
                ))
            
            # Добавляем кнопку "Ещё варианты" с остальными ссылками
            if len(watch_links) > 5:
                more_markup = InlineKeyboardMarkup(row_width=1)
                for link in watch_links[5:]:
                    more_markup.add(InlineKeyboardButton(
                        f"{link['icon']} {link['name']}", 
                        url=link['url']
                    ))
                
                markup.add(InlineKeyboardButton(
                    "🔽 Ещё варианты 🔽", 
                    callback_data=f"more_{name}_{year}"
                ))
            
            # Отправляем результат
            if poster:
                try:
                    bot.send_photo(user_id, poster, caption=answer, parse_mode='HTML', reply_markup=markup)
                except:
                    bot.send_message(user_id, answer, parse_mode='HTML', reply_markup=markup)
            else:
                bot.send_message(user_id, answer, parse_mode='HTML', reply_markup=markup)
        
        bot.send_message(
            user_id,
            "✅ <b>Поиск завершен!</b>\n\nНажми на любую кнопку чтобы перейти к просмотру.",
            parse_mode='HTML',
            reply_markup=main_menu()
        )
        return
    
    # НЕТ РЕЖИМА
    if user_id != ADMIN_ID:
        bot.send_message(
            user_id,
            "👇 Используй кнопки внизу",
            reply_markup=main_menu()
        )

# ========== ОБРАБОТКА КНОПКИ "ЕЩЁ ВАРИАНТЫ" ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('more_'))
def show_more_links(call):
    user_id = call.from_user.id
    
    # Парсим название и год из callback_data
    parts = call.data.split('_')
    name = parts[1]
    year = parts[2]
    
    # Получаем все ссылки
    all_links = get_watch_links(name, year)
    
    # Создаем клавиатуру со всеми ссылками
    markup = InlineKeyboardMarkup(row_width=1)
    for link in all_links[5:]:  # Пропускаем первые 5 (они уже были показаны)
        markup.add(InlineKeyboardButton(
            f"{link['icon']} {link['name']}", 
            url=link['url']
        ))
    
    # Добавляем кнопку назад
    markup.add(InlineKeyboardButton(
        "◀️ Назад к фильму", 
        callback_data=f"back_{name}_{year}"
    ))
    
    bot.edit_message_reply_markup(
        user_id,
        call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

# ========== КНОПКА НАЗАД ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('back_'))
def back_to_main(call):
    user_id = call.from_user.id
    
    # Парсим название и год
    parts = call.data.split('_')
    name = parts[1]
    year = parts[2]
    
    # Получаем ссылки и создаем основную клавиатуру
    all_links = get_watch_links(name, year)
    
    markup = InlineKeyboardMarkup(row_width=1)
    for link in all_links[:5]:
        markup.add(InlineKeyboardButton(
            f"{link['icon']} {link['name']}", 
            url=link['url']
        ))
    
    if len(all_links) > 5:
        markup.add(InlineKeyboardButton(
            "🔽 Ещё варианты 🔽", 
            callback_data=f"more_{name}_{year}"
        ))
    
    bot.edit_message_reply_markup(
        user_id,
        call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🎬 БОТ С ПАРСЕРОМ ССЫЛОК")
    print("=" * 60)
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"💳 Карта: {CARD_NUMBER}")
    print(f"🔑 API ключ: {KINOPOISK_API_KEY[:10]}...")
    print("=" * 60)
    print("✅ Поиск - РАБОТАЕТ")
    print("✅ Поддержка - РАБОТАЕТ")
    print("✅ Парсер ссылок - РАБОТАЕТ")
    print("=" * 60)
    
    try:
        bot.send_message(ADMIN_ID, "🚀 Бот с парсером ссылок запущен!")
        print("✅ Сообщение админу отправлено")
    except:
        print("⚠️ Не удалось отправить сообщение админу")
    
    bot.infinity_polling()
