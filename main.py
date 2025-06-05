import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import aiosqlite
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "meals.db"

# Инициализация БД
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                calories REAL,
                protein REAL,
                timestamp DATETIME
            )
        """)
        await db.commit()

# Парсинг одного приёма пищи
def parse_meal(text: str):
    lines = text.strip().split("\n")
    result = []
    total_kcal = 0
    total_protein = 0

    for line in lines:
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        name, kcal_per_100, protein_per_100, weight = parts
        try:
            kcal = float(kcal_per_100) * float(weight) / 100
            protein = float(protein_per_100) * float(weight) / 100
        except ValueError:
            continue
        result.append((name, round(kcal, 2), round(protein, 2)))
        total_kcal += kcal
        total_protein += protein

    return result, round(total_kcal, 2), round(total_protein, 2)

# Обработка сообщений от пользователя
@dp.message()
async def handle_message(message: Message):
    parsed, total_kcal, total_protein = parse_meal(message.text)

    if not parsed:
        await message.reply("Формат неверен. Пример:\n`яйца 157 12.7 125`")
        return

    # Сохраняем в БД
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT INTO meals (user_id, message, calories, protein, timestamp) VALUES (?, ?, ?, ?, ?)",
            (message.from_user.id, message.text, total_kcal, total_protein, datetime.now())
        )
        await db.commit()

        # Считаем итог за день
        today = datetime.now().date()
        next_day = today + timedelta(days=1)
        async with db.execute(
            "SELECT SUM(calories), SUM(protein) FROM meals WHERE user_id = ? AND timestamp >= ? AND timestamp < ?",
            (message.from_user.id, today.isoformat(), next_day.isoformat())
        ) as cursor:
            row = await cursor.fetchone()
            daily_kcal = round(row[0], 2) if row[0] else 0
            daily_protein = round(row[1], 2) if row[1] else 0

    # Сборка таблицы
    table = ["Продукт        | Ккал     | Белки", "-------------- | -------- | ------"]
    for name, kcal, protein in parsed:
        table.append(f"{name:<14} | {kcal:<8} | {protein:<6} г")

    table.append(f"\nИтого: {total_kcal} ккал | {total_protein} г белка")
    table.append(f"\n📊 С начала дня: {daily_kcal} ккал | {daily_protein} г белка")

    reply_text = "```🍳\xa0Приём\xa0пищи:\n" + "\n".join(table) + "\n```"
    await message.reply(reply_text)

# Ежедневная отправка итогов
async def daily_summary():
    while True:
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep((target - now).total_seconds())

        async with aiosqlite.connect(DB_FILE) as db:
            # Итоги за прошедшие сутки
            start = (datetime.now() - timedelta(days=1)).date()
            end = start + timedelta(days=1)

            async with db.execute(
                "SELECT user_id, SUM(calories), SUM(protein), COUNT(*) FROM meals "
                "WHERE timestamp >= ? AND timestamp < ? GROUP BY user_id",
                (start.isoformat(), end.isoformat())
            ) as cursor:
                rows = await cursor.fetchall()

                for user_id, kcal, protein, count in rows:
                    text = (
                        f"🍽️ *Итоги за {start.strftime('%d.%m')}:*\n"
                        f"Калорий: {round(kcal, 1)}\n"
                        f"Белков: {round(protein, 1)}\n"
                        f"Приёмов пищи: {count}"
                    )
                    await bot.send_message(chat_id=user_id, text=text)

# Главная функция
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    # Запускаем бота и планировщик параллельно
    await asyncio.gather(
        dp.start_polling(bot),
        daily_summary()
    )

if __name__ == "__main__":
    asyncio.run(main())