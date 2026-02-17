import sqlite3
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_file='movie_bot.db'):
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Подключение к базе данных"""
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Для удобного доступа по именам колонок
        self.cursor = self.conn.cursor()
        logger.info("✅ Подключение к БД установлено")
    
    def create_tables(self):
        """Создание всех таблиц"""
        
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT DEFAULT 'ru',
                subscription_end TEXT,
                subscription_type TEXT DEFAULT 'free',
                is_admin INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                registered_at TEXT,
                last_activity TEXT,
                total_searches INTEGER DEFAULT 0,
                invited_by INTEGER,
                FOREIGN KEY (invited_by) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица подписок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                price REAL,
                months INTEGER,
                started_at TEXT,
                ended_at TEXT,
                payment_method TEXT,
                payment_id TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица платежей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                months INTEGER,
                payment_date TEXT,
                payment_method TEXT,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                confirmed_by INTEGER,
                confirmed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (confirmed_by) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица тикетов поддержки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject TEXT,
                message TEXT,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'medium',
                created_at TEXT,
                updated_at TEXT,
                closed_at TEXT,
                closed_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (closed_by) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица ответов поддержки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                user_id INTEGER,
                message TEXT,
                created_at TEXT,
                is_admin INTEGER DEFAULT 0,
                FOREIGN KEY (ticket_id) REFERENCES support_tickets (id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица логов поиска
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT,
                results_count INTEGER,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица избранного
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                film_id TEXT,
                film_name TEXT,
                film_year TEXT,
                film_poster TEXT,
                added_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, film_id)
            )
        ''')
        
        # Таблица рефералов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                created_at TEXT,
                bonus_given INTEGER DEFAULT 0,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
        logger.info("✅ Таблицы созданы/проверены")
    
    # ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========
    
    def add_user(self, user_id, username=None, first_name=None, last_name=None, language_code='ru', invited_by=None):
        """Добавление нового пользователя"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, language_code, registered_at, last_activity, invited_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, language_code, now, now, invited_by))
            
            if invited_by:
                self.cursor.execute('''
                    INSERT INTO referrals (referrer_id, referred_id, created_at)
                    VALUES (?, ?, ?)
                ''', (invited_by, user_id, now))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
            return False
    
    def update_user(self, user_id, **kwargs):
        """Обновление данных пользователя"""
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)}, last_activity = ? WHERE user_id = ?"
        
        try:
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления пользователя: {e}")
            return False
    
    def get_user(self, user_id):
        """Получение информации о пользователе"""
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def get_user_by_username(self, username):
        """Поиск пользователя по username"""
        self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        return self.cursor.fetchone()
    
    # ========== ПОДПИСКИ ==========
    
    def has_subscription(self, user_id):
        """Проверка наличия активной подписки"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            SELECT * FROM users 
            WHERE user_id = ? AND subscription_end > ?
        ''', (user_id, now))
        return self.cursor.fetchone() is not None
    
    def add_subscription(self, user_id, months, payment_id=None):
        """Добавление подписки пользователю"""
        now = datetime.datetime.now()
        
        # Получаем текущую подписку
        self.cursor.execute('SELECT subscription_end FROM users WHERE user_id = ?', (user_id,))
        current = self.cursor.fetchone()
        
        if current and current['subscription_end']:
            try:
                current_end = datetime.datetime.strptime(current['subscription_end'], "%Y-%m-%d %H:%M:%S")
                if current_end > now:
                    new_end = current_end + datetime.timedelta(days=30*months)
                else:
                    new_end = now + datetime.timedelta(days=30*months)
            except:
                new_end = now + datetime.timedelta(days=30*months)
        else:
            new_end = now + datetime.timedelta(days=30*months)
        
        new_end_str = new_end.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self.cursor.execute('''
                UPDATE users 
                SET subscription_end = ?, subscription_type = ? 
                WHERE user_id = ?
            ''', (new_end_str, 'premium', user_id))
            
            self.cursor.execute('''
                INSERT INTO subscriptions (user_id, type, months, started_at, ended_at, payment_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, 'premium', months, now.strftime("%Y-%m-%d %H:%M:%S"), new_end_str, payment_id))
            
            self.conn.commit()
            return new_end_str
        except Exception as e:
            logger.error(f"Ошибка добавления подписки: {e}")
            return None
    
    # ========== АДМИНИСТРАТОРЫ ==========
    
    def is_admin(self, user_id):
        """Проверка является ли пользователь администратором"""
        self.cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result and result['is_admin'] == 1
    
    def set_admin(self, user_id, admin=1):
        """Назначение/снятие администратора"""
        self.cursor.execute('UPDATE users SET is_admin = ? WHERE user_id = ?', (admin, user_id))
        self.conn.commit()
    
    def get_admins(self):
        """Получение списка администраторов"""
        self.cursor.execute('SELECT * FROM users WHERE is_admin = 1')
        return self.cursor.fetchall()
    
    # ========== ПОДДЕРЖКА ==========
    
    def create_ticket(self, user_id, subject, message):
        """Создание тикета поддержки"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self.cursor.execute('''
                INSERT INTO support_tickets (user_id, subject, message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, subject, message, now, now))
            
            ticket_id = self.cursor.lastrowid
            
            self.cursor.execute('''
                INSERT INTO support_replies (ticket_id, user_id, message, created_at)
                VALUES (?, ?, ?, ?)
            ''', (ticket_id, user_id, message, now))
            
            self.conn.commit()
            return ticket_id
        except Exception as e:
            logger.error(f"Ошибка создания тикета: {e}")
            return None
    
    def reply_to_ticket(self, ticket_id, user_id, message, is_admin=False):
        """Ответ на тикет"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self.cursor.execute('''
                INSERT INTO support_replies (ticket_id, user_id, message, created_at, is_admin)
                VALUES (?, ?, ?, ?, ?)
            ''', (ticket_id, user_id, message, now, 1 if is_admin else 0))
            
            self.cursor.execute('''
                UPDATE support_tickets 
                SET updated_at = ?, status = ? 
                WHERE id = ?
            ''', (now, 'answered' if is_admin else 'open', ticket_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка ответа на тикет: {e}")
            return False
    
    def close_ticket(self, ticket_id, closed_by):
        """Закрытие тикета"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self.cursor.execute('''
                UPDATE support_tickets 
                SET status = 'closed', closed_at = ?, closed_by = ?
                WHERE id = ?
            ''', (now, closed_by, ticket_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка закрытия тикета: {e}")
            return False
    
    def get_user_tickets(self, user_id):
        """Получение тикетов пользователя"""
        self.cursor.execute('''
            SELECT * FROM support_tickets 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        return self.cursor.fetchall()
    
    def get_open_tickets(self):
        """Получение открытых тикетов"""
        self.cursor.execute('''
            SELECT t.*, u.username, u.first_name 
            FROM support_tickets t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status IN ('open', 'answered')
            ORDER BY t.priority DESC, t.created_at ASC
        ''')
        return self.cursor.fetchall()
    
    # ========== ПОИСК И СТАТИСТИКА ==========
    
    def log_search(self, user_id, query, results_count=0):
        """Логирование поиска"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self.cursor.execute('''
                INSERT INTO search_logs (user_id, query, results_count, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, query, results_count, now))
            
            self.cursor.execute('''
                UPDATE users 
                SET total_searches = total_searches + 1, last_activity = ?
                WHERE user_id = ?
            ''', (now, user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка логирования поиска: {e}")
            return False
    
    def get_stats(self, days=7):
        """Получение статистики за последние N дней"""
        from datetime import datetime, timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        stats = {}
        
        # Всего пользователей
        self.cursor.execute('SELECT COUNT(*) as count FROM users')
        stats['total_users'] = self.cursor.fetchone()['count']
        
        # Новых пользователей за период
        self.cursor.execute('SELECT COUNT(*) as count FROM users WHERE registered_at > ?', (start_date,))
        stats['new_users'] = self.cursor.fetchone()['count']
        
        # Активных пользователей
        self.cursor.execute('SELECT COUNT(DISTINCT user_id) as count FROM search_logs WHERE created_at > ?', (start_date,))
        stats['active_users'] = self.cursor.fetchone()['count']
        
        # Активных подписок
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('SELECT COUNT(*) as count FROM users WHERE subscription_end > ?', (now,))
        stats['active_subscriptions'] = self.cursor.fetchone()['count']
        
        # Всего поисков
        self.cursor.execute('SELECT COUNT(*) as count FROM search_logs')
        stats['total_searches'] = self.cursor.fetchone()['count']
        
        # Поисков за период
        self.cursor.execute('SELECT COUNT(*) as count FROM search_logs WHERE created_at > ?', (start_date,))
        stats['searches_period'] = self.cursor.fetchone()['count']
        
        # Открытых тикетов
        self.cursor.execute('SELECT COUNT(*) as count FROM support_tickets WHERE status IN ("open", "answered")')
        stats['open_tickets'] = self.cursor.fetchone()['count']
        
        return stats
    
    # ========== ИЗБРАННОЕ ==========
    
    def add_to_favorites(self, user_id, film_id, film_name, film_year, film_poster=None):
        """Добавление фильма в избранное"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO favorites (user_id, film_id, film_name, film_year, film_poster, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, film_id, film_name, film_year, film_poster, now))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления в избранное: {e}")
            return False
    
    def remove_from_favorites(self, user_id, film_id):
        """Удаление фильма из избранного"""
        self.cursor.execute('DELETE FROM favorites WHERE user_id = ? AND film_id = ?', (user_id, film_id))
        self.conn.commit()
    
    def get_favorites(self, user_id):
        """Получение списка избранного"""
        self.cursor.execute('''
            SELECT * FROM favorites 
            WHERE user_id = ? 
            ORDER BY added_at DESC
        ''', (user_id,))
        return self.cursor.fetchall()
    
    def __del__(self):
        """Закрытие соединения при удалении объекта"""
        if self.conn:
            self.conn.close()
            logger.info("🔒 Соединение с БД закрыто")
