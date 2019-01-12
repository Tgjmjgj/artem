import datetime
import re

import metadate

def parse_time(time):
    if isinstance(time, str):
        time = metadate.parse_date(time).start_date
    if not isinstance(time, datetime.datetime):
        raise TypeError('The datetime has incorrect syntax')
    return time

def parse_timedelta(timedelta):
    if isinstance(timedelta, str):
        re_weeks = re.search('(\d+) week', timedelta)
        weeks = int(re_weeks.group(1)) if re_weeks else 0
        re_days = re.search('(\d+) day', timedelta)
        days = int(re_days.group(1)) if re_days else 0
        re_hours = re.search('(\d+) hour', timedelta)
        hours = int(re_hours.group(1)) if re_hours else 0
        re_minutes = re.search('(\d+) minute', timedelta)
        minutes = int(re_minutes.group(1)) if re_minutes else 0
        re_seconds = re.search('(\d+) second', timedelta)
        seconds = int(re_seconds.group(1)) if re_seconds else 0
        timedelta = datetime.timedelta(weeks=weeks, days=days, hours=hours,
                                       minutes=minutes, seconds=seconds)
        if not timedelta:
            raise ValueError('Timedelta can\'t be a zero')
    if not isinstance(timedelta, datetime.timedelta):
        raise TypeError('The timedelta has incorrect syntax')
    return timedelta