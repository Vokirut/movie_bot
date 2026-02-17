import telebot
import requests
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

# ========== КЛАВИАТУРЫ ==========
def main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('🔍 Поиск фильма'),
        KeyboardButton('❓ Помощь')
    )
    return markup

def cancel_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('❌ Отмена'))
    return markup

# ========== ФУНКЦИЯ ПОИСКА ==========
def search_movie(query):
    # Используем публичное API Кинопоиска
    url = f"https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword={query}"
    headers = {
        'X-API-KEY': '8c8e7a9c-8b5c-4b3e-9f5a-3d5c5e5f7b8a',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('films', [])[:5]
        return []
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

# ========== ОБРАБОТЧИКИ ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    welcome_text = f"""
🎬 <b>Привет, {user_name}!</b>

Я бот для поиска фильмов. Просто отправь мне название фильма, и я найду информацию о нем!

🔍 <b>Примеры запросов:</b>
• Аватар
• Матрица
• Титаник

<i>Нажми кнопку "Поиск фильма" чтобы начать!</i>
    """
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode='HTML',
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == '❓ Помощь')
def help_message(message):
    help_text = """
❓ <b>Как пользоваться ботом:</b>

1️⃣ Нажми кнопку <b>"🔍 Поиск фильма"</b>
2️⃣ Отправь название фильма
3️⃣ Получи информацию о фильме

<b>📝 Команды:</b>
/start - Перезапустить бота
    """
    bot.send_message(
        message.chat.id, 
        help_text, 
        parse_mode='HTML',
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == '🔍 Поиск фильма')
def search_prompt(message):
    bot.send_message(
        message.chat.id, 
        "🎬 <b>Введите название фильма:</b>", 
        parse_mode='HTML',
        reply_markup=cancel_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == '❌ Отмена')
def cancel_search(message):
    bot.send_message(
        message.chat.id, 
        "❌ <b>Поиск отменен</b>", 
        parse_mode='HTML',
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    query = message.text.strip()
    
    # Отправляем статус
    status_msg = bot.send_message(
        message.chat.id, 
        "🔎 <i>Ищу фильмы...</i>", 
        parse_mode='HTML'
    )
    
    # Ищем фильмы
    films = search_movie(query)
    
    # Удаляем статус
    bot.delete_message(message.chat.id, status_msg.message_id)
    
    if not films:
        bot.send_message(
            message.chat.id,
            f"😕 Ничего не найдено по запросу: '{query}'",
            parse_mode='HTML',
            reply_markup=main_keyboard()
        )
        return
    
    # Отправляем каждый фильм
    for film in films:
        name_ru = film.get('nameRu', '')
        name_en = film.get('nameEn', '')
        name = name_ru if name_ru else name_en if name_en else 'Неизвестно'
        year = film.get('year', 'Неизвестно')
        rating = film.get('rating', '?')
        description = film.get('description', 'Описание отсутствует')
        film_id = film.get('filmId')
        poster = film.get('posterUrl')
        
        # Обрезаем описание
        if description and len(description) > 300:
            description = description[:300] + '...'
        
        text = f"""
🎬 <b>{name}</b>
📅 Год: {year}
⭐️ Рейтинг: {rating}

📝 {description}
        """
        
        # Создаем кнопку
        markup = None
        if film_id:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(
                "📺 Смотреть на Кинопоиске",
                url=f"https://www.kinopoisk.ru/film/{film_id}/"
            ))
        
        # Отправляем
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
                bot.send_message(
                    message.chat.id,
                    text,
                    parse_mode='HTML',
                    reply_markup=markup
                )
        else:
            bot.send_message(
                message.chat.id,
                text,
                parse_mode='HTML',
                reply_markup=markup
            )

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("=" * 40)
    print("🤖 Бот для поиска фильмов запущен!")
    print("🔄 Нажми Ctrl+C для остановки")
    print("=" * 40)
    
    bot.infinity_polling()
