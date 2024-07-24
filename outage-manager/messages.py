from enum import Enum

class Messages(Enum):
    ENERGY = "{emoji} Електроенергія є до {until} ({left})"
    OUTAGE = "{emoji} Відключення до {until} ({left})"
    OUTAGE_ENDS_SOON = "{emoji} Відлключення закінчиться о {time} ({duration})"
    OUTAGE_STARTS_SOON = "{emoji} Відключення почнеться о {time} ({duration})"
    OUTAGE_INFO_HEADER = "{emoji} Графік відключень:\n\n"
    OUTAGE_INFO = "{emoji} {start_time} - {end_time} {date} ({duration})"
    OUTAGE_BEGIN = "{emoji} Відключення! {start_time} - {end_time} ({duration})"
    OUTAGE_END = "{emoji} Відключення закінчилось о {end_time} ({duration})"
    STATUS_CHANGED = "{emoji} Статус змінився на\n{status}"
    NEXT_OUTAGE = "Наступне відключення - {next_time} (через {duration})"

