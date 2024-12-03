import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import os
from datetime import datetime
import aiosqlite
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv('config.env')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Константы
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SUPPORT_GROUP_ID = int(os.getenv('SUPPORT_GROUP_ID'))
DB_PATH = "support_bot.db"

# Проверка наличия необходимых переменных окружения
if not TOKEN:
    raise ValueError("Не указан TELEGRAM_BOT_TOKEN в файле config.env")
if not SUPPORT_GROUP_ID:
    raise ValueError("Не указан SUPPORT_GROUP_ID в файле config.env")

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица для связи пользователей и топиков
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_topics (
                user_id INTEGER PRIMARY KEY,
                topic_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для хранения сообщений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                is_from_support BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_topics(user_id)
            )
        ''')
        await db.commit()

async def get_user_topic(user_id: int) -> int:
    """Получить ID топика пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT topic_id FROM user_topics WHERE user_id = ?',
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def save_user_topic(user_id: int, topic_id: int):
    """Сохранить связь пользователь-топик"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR REPLACE INTO user_topics (user_id, topic_id) VALUES (?, ?)',
            (user_id, topic_id)
        )
        await db.commit()

async def save_message(user_id: int, topic_id: int, message_text: str, is_from_support: bool):
    """Сохранить сообщение в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''INSERT INTO messages (user_id, topic_id, message_text, is_from_support)
               VALUES (?, ?, ?, ?)''',
            (user_id, topic_id, message_text, is_from_support)
        )
        await db.commit()

async def get_chat_history(user_id: int) -> list:
    """Получить историю переписки пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            '''SELECT message_text, is_from_support, created_at 
               FROM messages 
               WHERE user_id = ?
               ORDER BY created_at ASC''',
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот поддержки. Напишите ваш вопрос, и я перенаправлю его нашим специалистам."
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих сообщений от пользователей"""
    if update.message.chat.type == "private":
        user = update.message.from_user
        message_text = update.message.text
        
        try:
            # Проверяем, есть ли уже топик у пользователя
            existing_topic_id = await get_user_topic(user.id)
            
            if existing_topic_id is None:
                # Создаем новую тему в супергруппе
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                topic_title = f"Поддержка: {user.username or user.first_name} - {current_time}"
                
                # Создаем новую тему
                forum_topic = await context.bot.create_forum_topic(
                    chat_id=SUPPORT_GROUP_ID,
                    name=topic_title
                )
                
                # Сохраняем ID темы для пользователя
                await save_user_topic(user.id, forum_topic.message_thread_id)
                topic_id = forum_topic.message_thread_id
            else:
                topic_id = existing_topic_id
            
            # Сохраняем сообщение пользователя
            await save_message(user.id, topic_id, message_text, False)
            
            # Отправляем сообщение в тему
            await context.bot.send_message(
                chat_id=SUPPORT_GROUP_ID,
                message_thread_id=topic_id,
                text=f"👤 *Пользователь:* {user.mention_html()}\n"
                     f"🆔 *User ID:* `{user.id}`\n"
                     f"📝 *Сообщение:*\n{message_text}",
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем подтверждение пользователю
            await update.message.reply_text(
                "Ваше сообщение отправлено команде поддержки. Мы ответим вам как можно скорее."
            )
            
        except Exception as e:
            logging.error(f"Error handling message: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка. Пожалуйста, попробуйте позже."
            )

async def handle_support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответов от команды поддержки"""
    if update.message.chat.id == SUPPORT_GROUP_ID and update.message.is_topic_message:
        try:
            # Находим пользователя по теме
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    'SELECT user_id FROM user_topics WHERE topic_id = ?',
                    (update.message.message_thread_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        user_id = result[0]
                        message_text = update.message.text
                        
                        # Сохраняем ответ поддержки
                        await save_message(
                            user_id, 
                            update.message.message_thread_id,
                            message_text,
                            True
                        )
                        
                        # Пересылаем ответ пользователю
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message_text
                        )
                    else:
                        await update.message.reply_text(
                            "Не удалось найти пользователя для этого топика."
                        )
        except Exception as e:
            logging.error(f"Error sending reply to user: {e}")
            await update.message.reply_text(
                "Не удалось отправить ответ пользователю."
            )

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ID текущего чата"""
    await update.message.reply_text(f"ID этого чата: {update.effective_chat.id}")

async def post_init(application: Application):
    """Действия после инициализации бота"""
    await init_db()

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
        handle_user_message
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.SUPERGROUP,
        handle_support_reply
    ))

    # Инициализация базы данных при запуске
    application.post_init = post_init

    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
