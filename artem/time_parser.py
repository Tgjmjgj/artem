import datetime
import re

import metadate

def parse_time(time):
    if isinstance(time, str):
        time = metadate.parse_date(time)
    if not isinstance(time, datetime.datetime):
        raise TypeError('The datetime has incorrect syntax')
    return time

def parse_timedelta(timedelta):
    if isinstance(timedelta, str):
        weeks = re.search('(\d+) week').group(1)
        days = re.search('(\d+) day').group(1)
        hours = re.search('(\d+) hour').group(1)
        minutes = re.search('(\d+) minute').group(1)
        seconds = re.search('(\d+) second').group(1)
        timedelta = datetime.timedelta(weeks=weeks, days=days, hours=hours,
                                       minutes=minutes, seconds=seconds)
        if not t:
            raise ValueError('Timedelta can\'t be a zero')
    if not isinstance(timedelta, datetime.timedelta):
        raise TypeError('The timedelta has incorrect syntax')
    return timedelta