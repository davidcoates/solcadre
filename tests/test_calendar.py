from datetime import timedelta
import itertools

from solcadre.calendar import Calendar
from solcadre.types import Weekday


def test_calendar_epoch_weekday():
    cal = Calendar()
    assert cal.epoch.weekday == Weekday.SUNDAY


def test_find_day_returns_epoch():
    cal = Calendar()
    moment = cal.epoch.start + timedelta(hours=1)
    found = cal.find_day(moment)
    assert found == cal.epoch


def test_iter_days_respects_start_and_end():
    cal = Calendar()
    days = list(itertools.islice(cal.iter_days(), 3))

    assert [day.index.day_of_calendar for day in days] == [0, 1, 2]
    assert list(cal.iter_days(start_day=days[1], end_day=days[2])) == [days[1]]


def test_day_after_epoch_is_monday_and_links_sunrise():
    cal = Calendar()
    days = list(itertools.islice(cal.iter_days(), 2))

    assert days[1].weekday == Weekday.MONDAY
    assert days[1].sunrise == days[0].next_sunrise
