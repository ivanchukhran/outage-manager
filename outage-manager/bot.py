import os
import asyncio
import logging

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F

from parser import get_current_status, get_today_outages

load_dotenv()

API_TOKEN = os.environ.get("API_TOKEN")

if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable is not set")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

subscribers = set()
current_status = None

async def notify_users(message: str):
    for user_id in subscribers:
        try:
            await bot.send_message(user_id, message)
        except Exception as e:
            await bot.send_message(user_id, f"An error occurred: {e}")

async def check_status(delay: int = 5):
    """
    Check the status of the outages every `delay` minutes and notify the users if the status changes.

    """
    global current_status
    while True:
        outages = list(get_today_outages())
        status = get_current_status(outages)
        if status != current_status:
            current_status = status
            message = f"Status changed: {status}"
            await notify_users(message)
        await asyncio.sleep(delay * 60)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Define command handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    subscribers.add(message.from_user.id)
    kb = [
        [types.KeyboardButton(text="Current status")],
        [types.KeyboardButton(text="Today outages")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb)
    await message.reply("Hello! Choose an option:", reply_markup=keyboard)

@dp.message(F.text.lower() == "current status")
async def current_outage_status(message: types.Message):
    try:
        outages = list(get_today_outages())
        status = get_current_status(outages)
        await message.reply(str(status))
    except Exception as e:
        await message.reply(f"An error occurred: {e}")


@dp.message(F.text.lower() == "today outages")
async def today_outages(message: types.Message):
    try:
        outages = list(get_today_outages())
        outages_str = "\n".join([str(outage) for outage in outages])
        await message.reply(outages_str)
    except Exception as e:
        await message.reply(f"An error occurred: {e}")


def get_args():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--delay", type=int, default=5, help="Delay between status checks in minutes", required=False)
    return parser.parse_args()

# Main function to start the bot
async def main():
    # Start the status checking task
    args = get_args()
    asyncio.create_task(check_status(delay=args.delay))
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
