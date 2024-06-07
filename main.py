import logging
import asyncio
from datetime import datetime, timedelta
import pymysql
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, BOT_TOKEN

logging.basicConfig(level=logging.INFO)

if BOT_TOKEN is None:
    raise ValueError("No BOT_TOKEN provided. Please set it in the .env file.")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

connection = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    cursorclass=pymysql.cursors.DictCursor
)


async def notify_user(chat_id, event_name):
    await bot.send_message(chat_id, f"Reminder: {event_name} is starting in 20 minutes!")


async def scheduler():
    while True:
        with connection.cursor() as cursor:
            print('Проверка')
            now = datetime.now().replace(second=0, microsecond=0)
            notify_time1 = (now + timedelta(minutes=19, seconds=30)).replace(microsecond=0)
            notify_time2 = (now + timedelta(minutes=20, seconds=30)).replace(microsecond=0)
            cursor.execute("SELECT * FROM tickets")
            tickets = cursor.fetchall()
            for ticket in tickets:
                cursor.execute("SELECT chat_id FROM users WHERE id = %s", (ticket['user_id'],))
                user = cursor.fetchone()
                cursor.execute("SELECT name, address FROM exhibitions WHERE id = %s", (ticket['exhibition_id'],))
                exhibitions = cursor.fetchone()
                if user and user['chat_id']:
                    asyncio.create_task(notify_user(user['chat_id'], exhibitions['name']))
        connection.commit()
        await asyncio.sleep(30)


@router.message(Command(commands=['start']))
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Please enter your user ID from the website:")


@router.message(lambda message: message.text.isdigit())
async def process_user_id(message: types.Message, state: FSMContext):
    user_id = message.text
    chat_id = message.chat.id
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            cursor.execute("UPDATE users SET chat_id = %s WHERE id = %s", (chat_id, user_id))
            connection.commit()
            await message.answer("You have been successfully authorized!")
        else:
            await message.answer("User ID not found. Please try again.")


@router.message(Command(commands=['tickets']))
async def show_tickets(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE chat_id = %s", (chat_id,))
        user = cursor.fetchone()
        if user:
            cursor.execute("SELECT * FROM tickets WHERE user_id = %s", (user['id'],))
            tickets = cursor.fetchall()
            if tickets:
                response = "Your tickets:\n"
                for ticket in tickets:
                    cursor.execute("SELECT name, address FROM exhibitions WHERE id = %s", (ticket['exhibition_id'],))
                    exhibitions = cursor.fetchone()
                    response += f"{exhibitions['name']} at {ticket['exhibition_datetime']} on address {exhibitions['address']}\n"
                await message.answer(response)
            else:
                await message.answer("You have no tickets.")
        else:
            await message.answer("You are not authorized. Please send your user ID using /start.")


async def main():
    await bot.set_my_commands([
        BotCommand(command="/start", description="Start interaction"),
        BotCommand(command="/tickets", description="Show purchased tickets")
    ])

    dp.startup.register(on_startup)
    await dp.start_polling(bot)


async def on_startup(dispatcher: Dispatcher):
    asyncio.create_task(scheduler())

if __name__ == '__main__':
    asyncio.run(main())
