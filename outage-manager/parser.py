#!/usr/bin/env python3
#
import re
import asyncio
from datetime import datetime, time

import httpx

from lxml import etree
from dataclasses import dataclass

URL = "https://energy-ua.info/grafik/%D0%9F%D0%BE%D0%BB%D1%82%D0%B0%D0%B2%D0%B0/%D0%93%D0%B5%D1%82%D1%8C%D0%BC%D0%B0%D0%BD%D0%B0+%D0%A1%D0%B0%D0%B3%D0%B0%D0%B9%D0%B4%D0%B0%D1%87%D0%BD%D0%BE%D0%B3%D0%BE/8"

color_to_status = {
    'red': 'electricity is unavailable',
    'green': 'electricity is available',
    'yellow': 'electricity could be unavailable'
}

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.5",
}



def time_to_str(time: time) -> str:
    return time.strftime("%H:%M")

@dataclass
class Outage:
    status: str
    start_time: time
    end_time: time
    duration: str

    def __str__(self):
        return f"{color_to_status.get(self.status)} from {time_to_str(self.start_time)} to {time_to_str(self.end_time)} ({self.duration})"


from enum import Enum

class OutageStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

def get_page_content(url: str = URL) -> str:
    with httpx.Client(headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
    return response.text

def get_today_outages():
    html_content = get_page_content(URL)
    schedule_container = etree.HTML(html_content).xpath("//div[@class='grafik_string']")[0]
    schedule_container_list = schedule_container.xpath("//div[@class='grafik_string_list_item']")
    pattern = r'.*\"clock_info_(.*)\".*\<b\>(\d+:\d+)<\/b>.*\<b\>(\d+:\d+)<\/b>.*<b>(.+?)<\/b>.*'
    for item_ in schedule_container_list:
        match_ = re.findall(pattern, etree.tostring(item_, encoding='unicode'))
        if not match_: continue
        status, start_time, end_time, duration = match_.pop()
        start_time = datetime.strptime(start_time, "%H:%M").time()
        end_time = datetime.strptime(end_time, "%H:%M").time()
        yield Outage(status, start_time, end_time, duration)


@dataclass
class EnergyState:
    status: OutageStatus
    next_state_change: time
    to_next_state_change: time

    def __str__(self):
        has_energy_string = "Has energy" if self.status == OutageStatus.INACTIVE else "No energy"
        until_string = f"until {self.next_state_change.strftime('%H:%M')}"
        time_left_string = f"{self.to_next_state_change.strftime('%H:%M')} left"
        return f"{has_energy_string} {until_string} ({time_left_string})"

def get_current_status(outages: list[Outage]):
    now = datetime.now()
    current_time = now.time()
    for outage in outages:
        if outage.start_time <= current_time <= outage.end_time:
            status = OutageStatus.ACTIVE
            netx_state_change = outage.end_time
            to_next_state_change = datetime.combine(now.date(), outage.end_time) - now
            break
        elif current_time < outage.start_time:
            status = OutageStatus.INACTIVE
            netx_state_change = outage.start_time
            to_next_state_change = datetime.combine(now.date(), outage.start_time) - now
            break
    h, m = divmod(to_next_state_change.seconds, 3600)
    m, _ = divmod(m, 60)
    return EnergyState(status, netx_state_change, datetime.strptime(f"{h}:{m}", "%H:%M").time())

async def main():
    for outage in get_today_outages():
        print(outage)
    print(get_current_status(list(get_today_outages())))
       
if __name__ == "__main__":
    asyncio.run(main())
