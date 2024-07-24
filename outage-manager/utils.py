from datetime import datetime, timedelta

def timedelta_to_str(td: timedelta) -> str:
    h, m = divmod(td.seconds, 3600)
    m, _ = divmod(m, 60)
    return f"{h:02}:{m:02}"
