from datetime import timedelta
import itertools
import zoneinfo

from solcadre.calendar import Calendar
from solcadre.types import Weekday


def test_calendar_epoch_weekday():
    cal = Calendar()
    assert cal.epoch.weekday == Weekday.SUNDAY
    assert Weekday.from_datetime(cal.epoch.solar_noon) == Weekday.SUNDAY


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


def test_day_after_epoch_is_monday_and_links_solar_midnight():
    cal = Calendar()
    days = list(itertools.islice(cal.iter_days(), 2))

    assert days[1].weekday == Weekday.MONDAY
    assert days[1].solar_midnight == days[0].next_solar_midnight


def test_polar_latitude_calendar_does_not_raise():
    cal = Calendar(latitude=80.0, longitude=0.0, timezone=zoneinfo.ZoneInfo("UTC"))
    days = list(itertools.islice(cal.iter_days(), 380))

    assert len(days) == 380
    assert all(day.solar_midnight < day.solar_noon < day.next_solar_midnight for day in days)
    assert any(day.sunrise is None for day in days)
    assert any(day.sunset is None for day in days)
