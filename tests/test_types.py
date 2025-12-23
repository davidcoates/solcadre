from datetime import datetime, time, timedelta
import pytest

from solcadre.types import (
    Season,
    Transition,
    block_type_from_index,
    Weekday,
    SolarPhase,
    Day,
)


def test_season_flip_next_number():
    assert Season.GREENTIDE.flip() == Season.EMBERWANE
    assert Season.GREENTIDE.next() == Transition.SUMMER_SOLSTICE


def test_transition_flip_next_number():
    assert Transition.SUMMER_SOLSTICE.flip() == Transition.WINTER_SOLSTICE
    assert Transition.SUMMER_SOLSTICE.next() == Season.SUNCREST


def test_block_type_from_index():
    assert block_type_from_index(0) == Season.GREENTIDE
    assert block_type_from_index(1) == Transition.SUMMER_SOLSTICE


def test_weekday_from_datetime():
    dt = datetime(2024, 9, 22)
    assert Weekday.from_datetime(dt) == Weekday.SUNDAY


def test_day_time_of_day_and_str():
    sunrise = datetime(2024, 1, 1, 6, 0)
    sunset = datetime(2024, 1, 1, 18, 0)
    next_sunrise = datetime(2024, 1, 2, 6, 0)
    day = Day(
        sunrise=sunrise,
        sunset=sunset,
        next_sunrise=next_sunrise,
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
        day.solar_phase(sunrise - timedelta(microseconds=1))
    assert day.solar_phase(sunrise) == SolarPhase.DAY
    assert day.solar_phase(sunrise + timedelta(microseconds=1)) == SolarPhase.DAY
    assert day.solar_phase(sunset) == SolarPhase.DAY
    assert day.solar_phase(sunset + timedelta(microseconds=1)) == SolarPhase.NIGHT
    assert day.solar_phase(next_sunrise - timedelta(microseconds=1)) == SolarPhase.NIGHT
    with pytest.raises(AssertionError):
        day.solar_phase(next_sunrise)
    assert day.time_of_day(sunrise).time == time(6, 0)
    assert str(day) == "01-01-01/1"
