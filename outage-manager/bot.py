import os
import asyncio
import logging
from enum import Enum
from typing import Any, List, Callable

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F

from parser import get_current_status, get_today_outages

load_dotenv()


def get_args():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--delay", type=int, default=5, help="Delay between status checks in minutes", required=False)
    parser.add_argument("--test", action="store_true", help="Run the bot in test mode", required=False)
    return parser.parse_args()

args = get_args()
if args.test:
    API_TOKEN = os.environ.get("TEST_API_TOKEN")
else:
    API_TOKEN = os.environ.get("API_TOKEN")

if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable is not set")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class EventType(Enum):
    OUTAGE = "OUTAGE"
    RESTORED = "RESTORED"
    STATUS_CHANGED = "STATUS_CHANGED"
    NOTIFY_BEFORE = "NOTIFY_BEFORE"

class Event:
    def __init__(self, event_type: EventType, data: Any | None = None):
        self.event_type = event_type
        self.data = None

notify_before_supported_values = [5, 10, 15, 30] # minutes
default_event_types = [EventType.OUTAGE, EventType.RESTORED, EventType.STATUS_CHANGED]
default_events = [Event(event_type) for event_type in default_event_types]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class Subscriber:
    def __init__(self, id: int, events: List[Event]):
        self.id = id
        self.events = events

    def notify(self, message: str):
        asyncio.create_task(bot.send_message(self.id, message))

    def schedule_notification(self, message: str, delay: int):
        asyncio.create_task(self.__notify_after_delay(message, delay))

    async def __notify_after_delay(self, message: str, delay: int):
        await asyncio.sleep(delay)
        self.notify(message)

class EventManager:
    subscriber_events = dict()

    def subscribe(self, id: int, events: List[Event]):
        self.subscriber_events[id] = events

    def unsubscribe(self, id: int):
        if id in self.subscriber_events:
            del self.subscriber_events[id]

    def notify_subscribers(self, event: Event, message: str):
        for subscriber, events in self.subscriber_events.items():
            if event in events:
                asyncio.create_task(bot.send_message(subscriber, message))

class StateManager:
    def __init__(self, delay: int = 5):
        self.current_outages = []
        self.current_status = None
        self.callbacks = dict()

    def update(self):
        outages = list(get_today_outages())
        if self.current_outages != outages:
            self.current_outages = outages
            if on_outages_change := self.callbacks.get("on_outages_change"):
                message = "Outages have changed\n" + "\n".join([str(outage) for outage in outages])
                on_outages_change(message)
        new_current_status = get_current_status(outages)
        if self.current_status != new_current_status:
            self.current_status = new_current_status
            if on_state_change := self.callbacks.get("on_state_change"):
                message = f"Status has changed to {str(self.current_status)}"
                on_state_change(message)

    def register_callback(self, name: str, callback: Callable):
        self.callbacks[name] = callback

    async def periodic_status_check(self, delay: int):
        while True:
            logging.info("Checking status")
            self.update()
            await asyncio.sleep(delay * 60)


event_manager = EventManager()
state_manager = StateManager()

state_manager.register_callback("on_state_change", lambda message: event_manager.notify_subscribers(Event(EventType.STATUS_CHANGED), message))
state_manager.register_callback("on_outages_change", lambda message: event_manager.notify_subscribers(Event(EventType.STATUS_CHANGED), message))

# Define command handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    event_manager.subscribe(user_id, default_events)
    # subscribers.add(message.from_user.id)
    kb = [
        [types.KeyboardButton(text="Current status")],
        [types.KeyboardButton(text="Today outages")],
        [types.KeyboardButton(text="Schedule")]
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

# TODO: Implement the schedule notification feature
@dp.message(F.text.lower() == "schedule")
async def schedule_notification(message: types.Message):
    try:
        buttons = [[types.KeyboardButton(text=str(value))] for value in notify_before_supported_values]
        kb = types.ReplyKeyboardMarkup(keyboard=buttons)
        await message.reply("Choose the time before the outage to notify you", reply_markup=kb)
        kb = types.ReplyKeyboardRemove()
    except Exception as e:
        await message.reply(f"An error occurred: {e}")
# Main function to start the bot
async def main():
    # Start the status checking task
    await dp.start_polling(bot)
    await state_manager.periodic_status_check(args.delay)

if __name__ == '__main__':
    asyncio.run(main())
