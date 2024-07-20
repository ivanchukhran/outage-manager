#!/usr/bin/env python3
from enum import Enum

class EmojiStatus(Enum):
    ENERGY = u"💡"
    OUTAGE = u"🕯️"
    WAITING = u"⏳"
    SCHEDULE = u"⏰"

    def __str__(self):
        return self.value
