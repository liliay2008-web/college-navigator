token_bot = '8216098356:AAEdA3S5wrnDDgehiLW2_A9I_uktppab0OM'

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, WebAppInfo
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import asyncio
import logging
import aiosqlite
from datetime import datetime
from typing import List

# === НАСТРОЙКИ ===
BOT_TOKEN = token_bot
WEB_APP_URL = "https://liliay2008-web.github.io/college-navigator/"
ADMIN_IDS = [1208286838]  # ← добавь сюда ID админов через запятую, например: [123456789, 987654321]
DB_NAME = "bot_database.db"

# Включаем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# === БАЗА ДАННЫХ ===
async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at TEXT,
                last_activity TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_at TEXT
            )
        """)
        await db.commit()
        logger.info("База данных инициализирована")

async def add_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Добавление/обновление пользователя в БД"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, registered_at, last_activity)
            VALUES (?, ?, ?, ?, 
                COALESCE((SELECT registered_at FROM users WHERE user_id = ?), ?),
                ?)
        """, (user_id, username, first_name, last_name, user_id, now, now))
        await db.commit()
        logger.info(f"Пользователь {user_id} добавлен/обновлен в БД")

async def get_user_count() -> int:
    """Получить количество пользователей"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def get_all_users() -> List[int]:
    """Получить список всех user_id"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    if user_id in ADMIN_IDS:
        return True
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result is not None

# === КОМАНДЫ ===
@router.message(Command("start"))
async def send_welcome(message: Message):
    """Обработка команды /start"""
    user = message.from_user
    
    # Добавляем пользователя в БД
    await add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Красивое приветственное сообщение
    welcome_text = f"""
🎓 <b>Добро пожаловать в Навигатор по колледжу!</b>

👋 Привет, {user.first_name or 'друг'}!

Это официальный бот-навигатор по колледжу. Здесь ты можешь:
📍 Найти любой кабинет
🗺️ Построить маршрут
⭐ Сохранить избранные локации

<b>Доступные команды:</b>
/start - Главное меню
/help - Справка
/stats - Статистика (только для админов)
/broadcast - Рассылка (только для админов)

👇 Нажми кнопку ниже, чтобы открыть интерактивную карту!
    """
    
    builder = ReplyKeyboardBuilder()
    builder.button(
        text="📍 Открыть навигатор",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    builder.button(text="ℹ️ Помощь")
    builder.adjust(1)
    
    await message.answer(
        welcome_text,
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@router.message(Command("help"))
async def send_help(message: Message):
    """Справка по боту"""
    help_text = """
📚 <b>Справка по боту</b>

<b>Основные функции:</b>
• Поиск кабинетов по номеру
• Построение маршрута от холла до кабинета
• Сохранение избранных кабинетов
• Интерактивная карта всех этажей

<b>Команды:</b>
/start - Главное меню
/help - Эта справка
/stats - Статистика бота (админы)
/broadcast - Рассылка сообщений (админы)

<b>Как использовать:</b>
1. Нажми кнопку "📍 Открыть навигатор"
2. Выбери этаж, на котором находишься
3. Введи номер кабинета или выбери из списка
4. Следуй маршруту на карте!

💡 <i>Совет: добавь избранные кабинеты в закладки для быстрого доступа!</i>
    """
    await message.answer(help_text)

@router.message(Command("stats"))
async def send_stats(message: Message):
    """Статистика бота (только для админов)"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа к этой команде.")
        return
    
    user_count = await get_user_count()
    stats_text = f"""
📊 <b>Статистика бота</b>

👥 Всего пользователей: <b>{user_count}</b>
📅 Дата: {datetime.now().strftime("%d.%m.%Y %H:%M")}

<i>Подробная статистика доступна в базе данных.</i>
    """
    await message.answer(stats_text)

@router.message(Command("broadcast"))
async def broadcast_command(message: Message):
    """Команда для начала рассылки (только для админов)"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа к этой команде.")
        return
    
    await message.answer(
        "📢 <b>Режим рассылки</b>\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Для отмены отправьте /cancel"
    )
    
    # Сохраняем состояние ожидания сообщения для рассылки
    # В реальном боте лучше использовать FSM (Finite State Machine)
    # Здесь упрощенная версия
    await message.answer(
        "⚠️ <i>Примечание: Для полноценной рассылки используйте команду /broadcast_send с текстом сообщения.</i>\n\n"
        "Пример: <code>/broadcast_send Привет всем! Это тестовая рассылка.</code>"
    )

@router.message(Command("broadcast_send"))
async def broadcast_send(message: Message):
    """Отправка рассылки всем пользователям"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа к этой команде.")
        return
    
    # Получаем текст сообщения после команды
    broadcast_text = message.text.replace("/broadcast_send", "").strip()
    
    if not broadcast_text:
        await message.answer(
            "❌ Ошибка: Укажите текст сообщения.\n\n"
            "Пример: <code>/broadcast_send Привет всем! Это тестовая рассылка.</code>"
        )
        return
    
    # Добавляем форматирование
    formatted_text = f"""
📢 <b>Рассылка от администрации</b>

{broadcast_text}

<i>— Навигатор по колледжу</i>
    """
    
    # Получаем список всех пользователей
    users = await get_all_users()
    
    if not users:
        await message.answer("❌ Нет пользователей для рассылки.")
        return
    
    sent_count = 0
    failed_count = 0
    
    await message.answer(f"⏳ Начинаю рассылку для {len(users)} пользователей...")
    
    # Отправляем сообщение всем пользователям
    for user_id in users:
        try:
            await bot.send_message(user_id, formatted_text)
            sent_count += 1
            # Небольшая задержка, чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
            logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
    
    # Отчет администратору
    report_text = f"""
✅ <b>Рассылка завершена!</b>

📤 Отправлено: <b>{sent_count}</b>
❌ Ошибок: <b>{failed_count}</b>
📊 Всего получателей: <b>{len(users)}</b>
    """
    await message.answer(report_text)

# Обработка текстовых сообщений
@router.message()
async def handle_text(message: Message):
    """Обработка текстовых сообщений"""
    text = message.text.lower()
    
    if text in ["ℹ️ помощь", "помощь", "help"]:
        await send_help(message)
    elif text in ["📍 открыть навигатор", "навигатор", "карта"]:
        builder = ReplyKeyboardBuilder()
        builder.button(
            text="📍 Открыть навигатор",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
        await message.answer(
            "📍 Нажмите кнопку ниже, чтобы открыть интерактивную карту колледжа!",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
    else:
        await message.answer(
            "❓ Не понимаю эту команду.\n\n"
            "Используйте /help для справки или /start для главного меню."
        )

# Подключаем роутер
dp.include_router(router)

# Запуск
async def main():
    """Главная функция запуска бота"""
    await init_db()
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
