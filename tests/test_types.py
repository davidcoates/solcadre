from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import pytest

from solcadre.types import (
    Season,
    Transition,
    block_type_from_index,
    Weekday,
    Meridiem,
    Day,
)

SYDNEY = ZoneInfo("Australia/Sydney")


def test_season_next_number():
    assert Season.ONE.next() == Transition.ONE
    assert Season.TWO.number == 2


def test_transition_next_number():
    assert Transition.ONE.next() == Season.TWO
    assert Transition.FOUR.next() == Season.ONE
    assert Transition.TWO.number == 2


def test_block_type_from_index():
    assert block_type_from_index(0) == Season.ONE
    assert block_type_from_index(1) == Transition.ONE
    assert block_type_from_index(2) == Season.TWO
    assert block_type_from_index(3) == Transition.TWO


def test_weekday_from_datetime():
    dt = datetime(2024, 9, 22)
    assert Weekday.from_datetime(dt) == Weekday.SUNDAY


def test_day_time_of_day_and_str():
    solar_midnight = datetime(2024, 1, 1, 0, 0, tzinfo=SYDNEY)
    solar_noon = datetime(2024, 1, 1, 12, 0, tzinfo=SYDNEY)
    next_solar_midnight = datetime(2024, 1, 2, 0, 0, tzinfo=SYDNEY)
    day = Day(
        solar_midnight=solar_midnight,
        solar_noon=solar_noon,
        next_solar_midnight=next_solar_midnight,
        sunrise=datetime(2024, 1, 1, 6, 0, tzinfo=SYDNEY),
        sunset=datetime(2024, 1, 1, 20, 0, tzinfo=SYDNEY),
        solar_event=None,
        index=Day.Index(
            year_of_calendar=0,
            block_of_year=0,
            week_of_block=0,
            day_of_week=0,
            day_of_calendar=0,
        ),
    )
    with pytest.raises(AssertionError):
        day.meridiem(solar_midnight - timedelta(microseconds=1))
    with pytest.raises(AssertionError):
        day.meridiem(next_solar_midnight)

    assert day.meridiem(solar_midnight) == Meridiem.ANTE
    assert day.meridiem(solar_noon - timedelta(microseconds=1)) == Meridiem.ANTE
    assert day.meridiem(solar_noon) == Meridiem.POST
    assert day.meridiem(next_solar_midnight - timedelta(microseconds=1)) == Meridiem.POST

    assert day.date == date(2024, 1, 1)
    assert day.start == solar_midnight
    assert day.end == next_solar_midnight
    assert day.time_of_day(solar_midnight).time == time(0, 0)
    assert str(day) == "01-1S-01/1"
