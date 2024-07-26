import os
import json
import asyncio
import logging
from enum import Enum
from typing import List, Callable, Set, Tuple, Dict
from collections import deque
from collections.abc import Sequence
from datetime import datetime, time, timedelta


from pydantic import BaseModel
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F

from parser import get_current_status, get_outages, Outage
from emoji import EmojiStatus

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
DELAY = int(os.getenv("DELAY", 5))

if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable is not set")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

class EventType(Enum):
    OUTAGE = "OUTAGE"
    RESTORED = "RESTORED"
    STATUS_CHANGED = "STATUS_CHANGED"
    NOTIFY_BEFORE = "NOTIFY_BEFORE"

notify_before_supported_values = [5, 10, 15, 30] # minutes
default_event_types = [EventType.OUTAGE, EventType.RESTORED, EventType.STATUS_CHANGED]

default_events = [(event_type, None) for event_type in default_event_types]
schedule_events = [(EventType.NOTIFY_BEFORE, notify_before) for notify_before in notify_before_supported_values]

all_events = default_events + schedule_events

Event = Tuple[EventType, int | None]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class EventManager:
    def __init__(self, save_path: str = "events.json"):
        # TODO: Implement the load from json method
        self.subscribers: Set[int] = set()
        self.event_subscribers: Dict[Event, Set[int]] = dict().fromkeys(all_events, set())

        self.save_path = save_path
        self.load()

        self.scheduled_queue = deque()

    def subscribe(self, id: int, events: Sequence[Event]) -> None:
        self.subscribers.add(id)
        for event in events:
            self.event_subscribers[event].add(id)
        self.save()
           
    def unsubscribe(self, id: int, events: Sequence[Event] | None = None) -> None:
        if events:
            for event in events:
                self.event_subscribers[event].discard(id)
            self.save()
            return
        self.subscribers.remove(id)
        for event in all_events:
            self.event_subscribers[event].discard(id)
        self.save()

    async def notify(self, id: int, message: str):
        await bot.send_message(id, message)

    async def notify_by_event(self, event: Event, message: str) -> None:
        for sub_id in self.event_subscribers[event]:
            await bot.send_message(sub_id, message)

    async def notify_all(self, message: str) -> None:
        for sub_id in self.subscribers:
            await bot.send_message(sub_id, message)

    def reschedule(self, outages: List[Outage]):
        self.scheduled_queue.clear()
        logging.info(f"Rescheduling notifications for outages: {outages})")
        current_time= time(datetime.now().hour, datetime.now().minute)
        current_timedelta = timedelta(hours=current_time.hour, minutes=current_time.minute)
        estimated_wait_time_list: List[Tuple[Event, int, str]] = [] # (notify_before, seconds, message)
        reversed_notify_before_supported_values = notify_before_supported_values[::-1]
        for outage in outages:
            outage_start_timedelta = timedelta(hours=outage.start_time.hour, minutes=outage.start_time.minute)
            outage_end_timedelta = timedelta(hours=outage.end_time.hour, minutes=outage.end_time.minute)
            # Schedule notifications for the status change
            if current_timedelta < outage_start_timedelta:
                for notify_option in reversed_notify_before_supported_values:
                    logging.debug(f"Outage: {outage.start_time} - {outage.end_time} {notify_option}, current: {current_timedelta}, start: {outage_start_timedelta}")
                    notify_before_timedelta = timedelta(minutes=notify_option)
                    diff = outage_start_timedelta - current_timedelta - notify_before_timedelta
                    if diff >= timedelta(0):
                        message = f"{str(EmojiStatus.SCHEDULE)} Outage will start in {notify_option} minutes"
                        estimated_wait_time_list.append(((EventType.NOTIFY_BEFORE, notify_option), diff.seconds, message))
                        current_timedelta = current_timedelta + diff
                message = f"{str(EmojiStatus.OUTAGE)} The outage has started at {outage.start_time.strftime('%H:%M')} and will end at {outage.end_time} ({outage.duration})"
                diff = outage_start_timedelta - current_timedelta
                estimated_wait_time_list.append(((EventType.STATUS_CHANGED, None), diff.seconds, message))
                current_timedelta = current_timedelta + diff
            # Schedule notifications for the outage end
            if current_timedelta < outage_end_timedelta:
                for notify_option in reversed_notify_before_supported_values:
                    logging.debug(f"Event: {notify_option}, current: {current_timedelta}, end: {outage_end_timedelta}")
                    notify_before_timedelta = timedelta(minutes=notify_option)
                    diff = outage_end_timedelta - current_timedelta - notify_before_timedelta
                    if diff >= timedelta(0):
                        message = f"{str(EmojiStatus.SCHEDULE)} Outage will end in {notify_option} minutes"
                        estimated_wait_time_list.append(((EventType.NOTIFY_BEFORE, notify_option), diff.seconds, message))
                        current_timedelta = current_timedelta + diff
                next_outage = outages[outages.index(outage) + 1] if outages.index(outage) + 1 < len(outages) else None
                message = f"{str(EmojiStatus.ENERGY)} The outage has ended at {outage.end_time.strftime('%H:%M')}."
                if next_outage:
                    message += f" The next outage will start at {next_outage.start_time.strftime('%H:%M')}"
                diff = outage_end_timedelta - current_timedelta
                estimated_wait_time_list.append(((EventType.STATUS_CHANGED, None), diff.seconds, message))
                current_timedelta = current_timedelta + diff
        logging.debug(f"Estimated wait time list: {estimated_wait_time_list}")
        for event, seconds, message in estimated_wait_time_list:
            self.scheduled_queue.append((event, seconds, message))

    async def process_scheduled_notifications(self):
        while True:
            logging.debug(f"Scheduled queue: {self.scheduled_queue}")
            if self.scheduled_queue:
                event, seconds, message = self.scheduled_queue.popleft()
                logging.info(f"Waiting for {seconds} seconds to notify about {event}")
                await asyncio.sleep(seconds)
                await self.notify_by_event(event, message)
            await asyncio.sleep(5)

    def load(self):
        try:
            with open(self.save_path, "r") as file:
                json_data = json.load(file)
                self.subscribers = set(json_data["subscribers"])
                self.event_subscribers = dict().fromkeys(all_events, set())
                for event in json_data["event_subscribers"]:
                    event_type = EventType(event["event_type"])
                    data = event["data"]
                    subscribers = set(event["subscribers"])
                    self.event_subscribers[(event_type, data)] = subscribers
        except Exception as e:
            logging.error(f"An error occurred while loading data: {e}")
            logging.info("Creating a new checkpoint file")
            self.save()

    def save(self):
        json_data = {
            "subscribers": list(self.subscribers),
            "event_subscribers": []
        }
        for event in self.event_subscribers:
            event_type, data = event
            json_data["event_subscribers"].append({
                "event_type": event_type.value,
                "data": data,
                "subscribers": list(self.event_subscribers[event])
                })
        with open(self.save_path, "w") as file:
            json.dump(json_data, file)

    def __contains__(self, id: int) -> bool:
        return id in self.subscribers

event_manager = EventManager()

class StateManager:
    def __init__(self):
        self.current_outages: List[Outage] = []

    async def update(self):
        outages = await get_outages()
        logging.info(f"Outages: {outages}")
        if self.current_outages != outages:
            logging.info(f"Outages have changed: {outages}")
            self.current_outages = outages
            message = "Outages have changed\n" + "\n".join([str(EmojiStatus.OUTAGE) + " " + str(outage) for outage in outages])
            await event_manager.notify_by_event((EventType.STATUS_CHANGED, None), message)
            message = f"Status has changed to \n{str(self.current_status())}"
            await event_manager.notify_by_event((EventType.STATUS_CHANGED, None), message)
            event_manager.reschedule(outages)

    def current_status(self):
        status = get_current_status(self.current_outages)
        logging.info(f"Current status: {str(status)}")
        return str(status)

    async def periodic_status_check(self, delay: int):
        while True:
            logging.info("Checking status")
            await self.update()
            await asyncio.sleep(delay * 60)

state_manager = StateManager()

navigation_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="Current status")],
        [types.KeyboardButton(text="Today outages")],
        [types.KeyboardButton(text="Schedule")],
        [types.KeyboardButton(text="Unsubscribe")]
    ]
)

schedule_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text=str(value))] for value in notify_before_supported_values
    ]
)
schedule_keyboard.keyboard += [[types.KeyboardButton(text="Cancel")]]

def check_user_or_raise(user: types.User | None):
    if user is None:
        raise ValueError("User is not found")
    return user

def subscriable(func):
    async def wrapper(message: types.Message):
        user = check_user_or_raise(message.from_user)
        user_id = int(user.id)
        event_manager.subscribe(id=user_id, events=default_events)
        await func(message)
    return wrapper


# Define command handlers
@dp.message(Command("start"))
@subscriable
async def cmd_start(message: types.Message):
    await message.reply("Hello! Choose an option:", reply_markup=navigation_keyboard)

@dp.message(F.text.lower() == "current status")
@subscriable
async def current_outage_status(message: types.Message):
    try:
        status = state_manager.current_status()
        await message.reply(str(status))
    except Exception as e:
        await message.reply(f"An error occurred: {e}")


@dp.message(F.text.lower() == "today outages")
@subscriable
async def today_outages(message: types.Message):
    try:
        outages_str = "\n".join([str(EmojiStatus.OUTAGE) + " " + str(outage) for outage in state_manager.current_outages])
        await message.reply(outages_str)
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

# TODO: Implement the schedule notification feature
@dp.message(F.text.lower() == "schedule")
async def show_scheduling_options(message: types.Message):
    try:
        await message.reply("Choose the time before the outage to notify you", reply_markup=schedule_keyboard)
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

@dp.message(lambda message: message.text.isdigit() and int(message.text) in notify_before_supported_values)
@subscriable
async def choose_schedule_options(message: types.Message):
    try:
        message_text = message.text
        assert message_text is not None and message_text.isdigit()
        notify_option = int(message_text)
        logging.info(f"Notifying {notify_option} minutes before the outage")
        if notify_option not in notify_before_supported_values:
            await message.reply("Unsupported value. Please choose a value from the list")
            return
        event = (EventType.NOTIFY_BEFORE, notify_option)
        user = check_user_or_raise(message.from_user)
        logging.info(f"Subscribing user {user.id} to event {event}")
        event_manager.subscribe(user.id, [event])
        await message.reply(f"Notifications will be sent {notify_option} minutes before each status change", reply_markup=navigation_keyboard)
    except Exception as e:
        await message.reply(f"An error occurred: {e}", reply_markup=navigation_keyboard)

@dp.message(F.text.lower() == "cancel")
@subscriable
async def cancel_schedule(message: types.Message):
    try:
        user = check_user_or_raise(message.from_user)
        await message.reply("Notification setup have been canceled", reply_markup=navigation_keyboard)
    except Exception as e:
        await message.reply(f"An error occurred: {e}", reply_markup=navigation_keyboard)

@dp.message(F.text.lower() == "unsubscribe")
async def show_unsubscribe_options(message: types.Message):
    user = check_user_or_raise(message.from_user)
    user_id = int(user.id)
    subscribed_options = [
        event_key for event_key in event_manager.event_subscribers.keys()
        if user_id in event_manager.event_subscribers[event_key] and event_key[0] == EventType.NOTIFY_BEFORE
        ]
    unsubscribe_options = []
    for option in subscribed_options:
        event_type, data = option
        str = f"{event_type.value}: {data}" if data else f"{event_type.value}"
        unsubscribe_options.append([types.KeyboardButton(text=str)])
    unsubscribe_options.append([types.KeyboardButton(text="All")])
    unsubscribe_options.append([types.KeyboardButton(text="Cancel")])
    keyboard = types.ReplyKeyboardMarkup(keyboard=unsubscribe_options)
    message_text = "Choose an option to unsubscribe"
    await message.reply(message_text, reply_markup=keyboard)

@dp.message(lambda message: message.text.lower() == "all" or message.text in [f"{event_type.value}: {data}" for event_type, data in all_events])
async def unsubscribe(message: types.Message):
    try:
        user = check_user_or_raise(message.from_user)
        user_id = int(user.id)
        option = message.text
        assert option is not None
        if option == "all":
            event_manager.unsubscribe(user_id)
            await message.reply("You have been unsubscribed from all notifications", reply_markup=navigation_keyboard)
            return
        event_type, data = option.split(":")
        event = (EventType(event_type), int(data)) if data else (EventType(event_type), None)
        event_manager.unsubscribe(user_id, [event])
        await message.reply(f"You have been unsubscribed from {event}", reply_markup=navigation_keyboard)
    except Exception as e:
        await message.reply(f"An error occurred: {e}", reply_markup=navigation_keyboard)


# async def main():
if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    tasks = asyncio.gather(
        dp.start_polling(bot, handle_signals=False),
        state_manager.periodic_status_check(DELAY),
        event_manager.process_scheduled_notifications(),
        return_exceptions=True
    )

    try:
        loop.run_until_complete(tasks)
    except KeyboardInterrupt as e:
        tasks.cancel()
        loop.run_forever()
        tasks.exception()
    finally:
        loop.close()
