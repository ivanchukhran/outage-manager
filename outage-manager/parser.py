#!/usr/bin/env python3
#
import re
import asyncio
from datetime import datetime, time, timedelta

import httpx
from playwright.async_api import async_playwright


from lxml import etree
from dataclasses import dataclass

from emoji import EmojiStatus
from utils import timedelta_to_str
from messages import Messages

URL = "https://energy-ua.info/grafik/%D0%9F%D0%BE%D0%BB%D1%82%D0%B0%D0%B2%D0%B0/%D0%93%D0%B5%D1%82%D1%8C%D0%BC%D0%B0%D0%BD%D0%B0+%D0%A1%D0%B0%D0%B3%D0%B0%D0%B9%D0%B4%D0%B0%D1%87%D0%BD%D0%BE%D0%B3%D0%BE/8"

color_to_message = {
    'red': Messages.OUTAGE_INFO,
    'green': Messages.ENERGY,
    'yellow': 'Можуть бути перебої'
}

def time_to_str(time: time) -> str:
    return time.strftime("%H:%M")

@dataclass
class Outage:
    status: str
    start_time: datetime
    end_time: datetime
    duration: str

    def to_str_with_date(self) -> str:
        message = color_to_message.get(self.status, Messages.OUTAGE_INFO)
        return message.value.format(
            emoji=EmojiStatus.OUTAGE if self.status == 'red' else EmojiStatus.ENERGY,
            start_time=self.start_time.strftime('%H:%M'),
            end_time=self.end_time.strftime('%H:%M'),
            date = self.start_time.date().strftime('%d.%m.%Y'),
            duration=self.duration
        )

    def to_str(self) -> str:
        message = color_to_message.get(self.status, Messages.OUTAGE_INFO)
        return message.value.format(
            emoji=EmojiStatus.OUTAGE if self.status == 'red' else EmojiStatus.ENERGY,
            start_time=self.start_time.strftime('%H:%M'),
            end_time=self.end_time.strftime('%H:%M'),
            duration=self.duration,
            date = ''
        )

    def __str__(self):
        message = color_to_message.get(self.status, Messages.OUTAGE_INFO)
        return message.value.format(
            emoji=EmojiStatus.OUTAGE if self.status == 'red' else EmojiStatus.ENERGY,
            start_time=self.start_time.strftime('%H:%M'),
            end_time=self.end_time.strftime('%H:%M'),
            date = self.start_time.date().strftime('%d.%m.%Y'),
            duration=self.duration)
        # return f"{color_to_status.get(self.status)} from {time_to_str(self.start_time.time())} to {time_to_str(self.end_time.time())} ({self.duration})"


from enum import Enum

class OutageStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
}

async def get_content_with_httpx(url: str = URL) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.text

   
async def get_content_with_playwright(url: str = URL) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        html = await page.content()
        await browser.close()
        return html


async def get_page_content(url: str = URL, fn=get_content_with_playwright) -> str:
    response = await fn(url)
    return response

async def get_outages():
    result = []
    html_content = await get_page_content(URL)
    today_schedule_container, tomorrow_schedule_container = etree.HTML(html_content).xpath("//div[@class='grafik_string']")
    current_datetime = datetime.now().date()
    tomorrow_datetime = current_datetime + timedelta(days=1)
    for schedule_item in today_schedule_container.xpath("*/div[@class='grafik_string_list_item']"):
        status, start_time, end_time, duration = re.findall(r'.*\"clock_info_(.*)\".*\<b\>(\d+:\d+)<\/b>.*\<b>(\d+:\d+)<\/b>.*<b>(.+?)<\/b>.*', etree.tostring(schedule_item, encoding='unicode')).pop()
        start_time = datetime.strptime(start_time, "%H:%M").time()
        end_time = datetime.strptime(end_time, "%H:%M").time()
        result.append(
            Outage(status=status,
                   start_time=datetime.combine(current_datetime, start_time),
                   end_time=datetime.combine(current_datetime, end_time),
                   duration=duration)
            )
    for schedule_item in tomorrow_schedule_container.xpath("*/div[@class='grafik_string_list_item']"):
        status, start_time, end_time, duration = re.findall(r'.*\"clock_info_(.*)\".*\<b\>(\d+:\d+)<\/b>.*\<b>(\d+:\d+)<\/b>.*<b>(.+?)<\/b>.*', etree.tostring(schedule_item, encoding='unicode')).pop()
        start_time = datetime.strptime(start_time, "%H:%M").time()
        end_time = datetime.strptime(end_time, "%H:%M").time()
        result.append(
            Outage(status=status,
                   start_time=datetime.combine(tomorrow_datetime, start_time),
                   end_time=datetime.combine(tomorrow_datetime, end_time),
                   duration=duration)
            )
    return result

@dataclass
class EnergyState:
    status: OutageStatus
    next_state_change: datetime | None
    to_next_state_change: timedelta | None

    def __str__(self) -> str:
        message = Messages.OUTAGE if self.status == OutageStatus.ACTIVE else Messages.ENERGY
        string = message.value.format(
            emoji=EmojiStatus.OUTAGE if self.status == OutageStatus.ACTIVE else EmojiStatus.ENERGY,
            until = self.next_state_change.strftime('%H:%M %d.%m.%Y') if self.next_state_change is not None else '',
            left = timedelta_to_str(self.to_next_state_change) if self.to_next_state_change is not None else ''
            )
        return string



def get_current_status(outages: list[Outage]):
    now = datetime.now()
    # current_time = now.time()
    status = OutageStatus.INACTIVE
    next_state_change = None
    to_next_state_change = None
    for i, outage in enumerate(outages):
        if outage.start_time <= now <= outage.end_time:
            status = OutageStatus.ACTIVE
            next_state_change = outage.end_time
            to_next_state_change = outage.end_time - now
            break
        elif outage.start_time > now:
            status = OutageStatus.INACTIVE
            next_state_change = outage.start_time
            to_next_state_change = outage.start_time - now
            break
    if to_next_state_change is not None:
        h, m = divmod(to_next_state_change.seconds, 3600)
        m, _ = divmod(m, 60)
        to_next_state_change = timedelta(hours=h, minutes=m)
    return EnergyState(status, next_state_change, to_next_state_change)

async def main():
    outages = await get_outages()
    for outage in outages:
        print(outage)
    print(get_current_status(outages))
       
if __name__ == "__main__":
    asyncio.run(main())
