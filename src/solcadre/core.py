__all__ = [
    "CANONICAL_LATITUDE",
    "CANONICAL_LONGITUDE",
    "CANONICAL_TIMEZONE",
    "CANONICAL_EPOCH",
    "InvalidLatitude",
    "Season",
    "Holiday",
    "Block",
    "Weekday",
    "Day",
    "Hemisphere",
    "Calendar"
]

import astral
import astral.sun
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta, tzinfo
from enum import Enum, auto
from typing import Iterable
import zoneinfo

from .solar_events import *
from .format import *


CANONICAL_LATITUDE = -33.865143
CANONICAL_LONGITUDE = 151.209900
CANONICAL_TIMEZONE = zoneinfo.ZoneInfo("Australia/Sydney")
CANONICAL_EPOCH = date(2024, 9, 22)


class InvalidLatitude(Exception):

    def __init__(self, latitude, message):
        super().__init__(f"latitude({latitude}) is invalid: {message}")


class Season(Enum):
    GREENTIDE = 0
    SUNCREST = 1
    EMBERWANE = 2
    FROSTFALL = 3

    def flip(self):
        return Season((self.value + 2) % 4)

    def next(self):
        return Holiday(self.value)

    def __str__(self):
        return self.name.title()


class Holiday(Enum):
    SUMMER_SOLSTICE = 0
    AUTUMNAL_EQUINOX = 1
    WINTER_SOLSTICE = 2
    VERNAL_EQUINOX = 3

    def flip(self):
        return Holiday((self.value + 2) % 4)

    def next(self):
        return Season((self.value + 1) % 4)

    def __str__(self):
        return self.name.title().replace('_', ' ')


type Block = Season | Holiday


class Weekday(Enum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6

    @staticmethod
    def from_datetime(datetime):
        return Weekday((datetime.weekday() + 1) % 7)

    def __str__(self):
        return self.name.title()


LAST_DAY_OF_HOLIDAY = 7 - 1
LAST_DAY_OF_LEAP_HOLIDAY = (7 * 2) - 1
LAST_DAY_OF_SEASON = (7 * 12) - 1


@dataclass(frozen=True)
class Day:
    sunrise: datetime
    sunset: datetime
    next_sunrise: datetime
    year: int
    block: Block
    day_of_block: int
    days_since_epoch: int
    solar_event: SolarEvent | None

    def __post_init__(self):
        assert self.sunrise.date() == self.sunset.date()

    @property
    def date(self) -> date:
        return self.sunrise.date()

    @property
    def start(self) -> datetime:
        return self.sunrise

    @property
    def end(self) -> datetime:
        return self.next_sunrise

    @property
    def week(self) -> int:
        return (self.day_of_block // 7)

    @property
    def weekday(self) -> Weekday:
        return Weekday(self.day_of_block % 7)

    @property
    def day_of_week(self) -> int:
        return self.day_of_block % 7

    def human_string(self):
        if isinstance(self.block, Season):
            return f"{self.weekday}, Week {self.week + 1} of {self.block}, Year {self.year + 1}"
        elif isinstance(self.block, Holiday):
            return f"{self.weekday}, Week {self.week + 1} of the {self.block} Holiday, Year {self.year + 1}"
        else:
            assert False

    def __str__(self):
        return self.human_string()


class Hemisphere(Enum):
    NORTHERN = auto()
    SOUTHERN = auto()


@dataclass
class Calendar:
    latitude: float = CANONICAL_LATITUDE
    longitude: float = CANONICAL_LONGITUDE
    timezone: zoneinfo.ZoneInfo = CANONICAL_TIMEZONE

    def __post_init__(self):
        self.observer = astral.Observer(self.latitude, self.longitude)
        self.hemisphere = Hemisphere.NORTHERN if self.latitude > 0 else Hemisphere.SOUTHERN
        self.days = self._calc_localized_days()
        self.epoch = self.days[0]

    def find_day(self, time: datetime) -> Day | None:
        for day in self.days:
            if day.start <= time < day.end:
                return day
        return None

    def _sunrise_of_day(self, date) -> datetime:
        try:
            return astral.sun.sunrise(self.observer, date, tzinfo=self.timezone)
        except ValueError:
            raise InvalidLatitude(self.latitude, f"no sunrise on date({date})")

    def _sunset_of_day(self, date) -> datetime:
        try:
            return astral.sun.sunset(self.observer, date, tzinfo=self.timezone)
        except ValueError:
            raise InvalidLatitude(self.latitude, f"no sunset on date({date})")

    def _calc_localized_days(self):
        days = []
        offset = 0
        if self.hemisphere == Hemisphere.NORTHERN:
            offset = next(i for (i, day) in enumerate(CANONICAL_DAYS) if day.block == Season.EMBERWANE)
        match Weekday.from_datetime(self._sunrise_of_day(CANONICAL_EPOCH + timedelta(days=offset))):
            case Weekday.MONDAY:
                gregorian_offset = offset - 1
            case Weekday.SUNDAY:
                gregorian_offset = offset
            case Weekday.SATURDAY:
                gregorian_offset = offset + 1
            case _:
                assert False
        gregorian_date = CANONICAL_EPOCH + timedelta(days=gregorian_offset)
        assert Weekday.from_datetime(self._sunrise_of_day(gregorian_date)) == Weekday.SUNDAY
        assert Weekday.from_datetime(CANONICAL_DAYS[offset].start) == Weekday.SUNDAY
        assert offset >= 0
        year = -1
        next_solar_event_index = 0
        for i, canonical_day in enumerate(CANONICAL_DAYS[offset:]):
            block = canonical_day.block
            day_of_block = canonical_day.day_of_block
            if self.hemisphere == Hemisphere.NORTHERN:
                block = block.flip()
            if block == Season.GREENTIDE and day_of_block == 0:
                year += 1
            sunrise = self._sunrise_of_day(gregorian_date)
            next_sunrise = self._sunrise_of_day(gregorian_date + timedelta(days=1))
            while next_solar_event_index < len(SOLAR_EVENTS) and SOLAR_EVENTS[next_solar_event_index].time < sunrise:
                next_solar_event_index += 1
            solar_event = None
            if next_solar_event_index < len(SOLAR_EVENTS) and SOLAR_EVENTS[next_solar_event_index].time < next_sunrise:
                solar_event = SOLAR_EVENTS[next_solar_event_index]
            day = Day(
                sunrise=sunrise,
                sunset=self._sunset_of_day(gregorian_date),
                next_sunrise=next_sunrise,
                year=year,
                block=block,
                day_of_block=day_of_block,
                days_since_epoch=i,
                solar_event=solar_event
            )
            days.append(day)
            gregorian_date = gregorian_date + timedelta(days=1)
        return days


def _sunrise_of_canonical_day(date) -> datetime:
    return astral.sun.sunrise(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date, tzinfo=CANONICAL_TIMEZONE)

def _sunset_of_canonical_day(date) -> datetime:
    return astral.sun.sunset(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date, tzinfo=CANONICAL_TIMEZONE)

def _calc_canonical_days() -> Iterable[Day]:
    assert Weekday.from_datetime(_sunrise_of_canonical_day(CANONICAL_EPOCH)) == Weekday.SUNDAY
    gregorian_date = CANONICAL_EPOCH
    day = Day(
        sunrise=_sunrise_of_canonical_day(gregorian_date),
        sunset=_sunset_of_canonical_day(gregorian_date),
        next_sunrise=_sunrise_of_canonical_day(gregorian_date + timedelta(days=1)),
        year=0,
        block=Season.GREENTIDE,
        day_of_block=0,
        days_since_epoch=0,
        solar_event=None
    )
    yield day
    while True:
        gregorian_date = gregorian_date + timedelta(days=1)
        sunrise = _sunrise_of_canonical_day(gregorian_date)
        sunset = _sunset_of_canonical_day(gregorian_date)
        next_sunrise = _sunrise_of_canonical_day(gregorian_date + timedelta(days=1))
        if isinstance(day.block, Holiday) and (day.day_of_block == LAST_DAY_OF_HOLIDAY or day.day_of_block == LAST_DAY_OF_LEAP_HOLIDAY):
            assert day.weekday == Weekday.SATURDAY
            solar_events = [ solar_event for solar_event in SOLAR_EVENTS if abs(solar_event.time.date() - gregorian_date) <= timedelta(days=14) ]
            if not solar_events:
                return
            [ solar_event ] = solar_events
            leap_week_threshold = _sunset_of_canonical_day(gregorian_date + timedelta(days=1))
            if solar_event.time > leap_week_threshold: # insert a leap week
                year = day.year
                block = day.block
                day_of_block = day.day_of_block + 1
            else:
                year = day.year + 1 if day.block == Holiday.VERNAL_EQUINOX else day.year
                block = day.block.next()
                day_of_block = 0
        elif isinstance(day.block, Season) and day.day_of_block == LAST_DAY_OF_SEASON:
            year = day.year
            block = day.block.next()
            day_of_block = 0
        else:
             year = day.year
             block = day.block
             day_of_block = day.day_of_block + 1
        day = Day(
            sunrise=sunrise,
            sunset=sunset,
            next_sunrise=next_sunrise,
            year=year,
            block=block,
            day_of_block=day_of_block,
            days_since_epoch=day.days_since_epoch + 1,
            solar_event=None
        )
        yield day


CANONICAL_DAYS = list(_calc_canonical_days())
