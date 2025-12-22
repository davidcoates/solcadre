"""Implementation of the Solcadre calendar system.

This module provides the core calendar functionality, including seasons, transitions,
days, and calendar calculations based on solar events and geographic location.
"""

__all__ = [
    "CANONICAL_LATITUDE",
    "CANONICAL_LONGITUDE",
    "CANONICAL_TIMEZONE",
    "CANONICAL_EPOCH",
    "InvalidLatitude",
    "Season",
    "Transition",
    "BlockType",
    "Weekday",
    "Day",
    "Week",
    "Block",
    "Year",
    "Hemisphere",
    "Calendar"
]

import astral
import astral.sun
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta, tzinfo
from enum import Enum, auto
from typing import Iterable
import itertools
import zoneinfo

from .solar_events import *
from .format import *


CANONICAL_LATITUDE = -33.865143
CANONICAL_LONGITUDE = 151.209900
CANONICAL_TIMEZONE = zoneinfo.ZoneInfo("Australia/Sydney")
CANONICAL_EPOCH = date(2024, 9, 22)


class InvalidLatitude(Exception):
    """Exception raised when a latitude value is invalid for Solcadre.

    This occurs when the latitude is too close to the poles, resulting in days
    where sunrise or sunset cannot be calculated.

    Args:
        latitude: The invalid latitude value.
        message: Additional error message describing why the latitude is invalid.
    """

    def __init__(self, latitude, message):
        super().__init__(f"latitude({latitude}) is invalid: {message}")


class Season(Enum):
    """Enumeration of the four Solcadre seasons."""
    GREENTIDE = 0
    SUNCREST = 2
    EMBERWANE = 4
    FROSTFALL = 6

    def flip(self):
        """Return the opposite season (180 degrees in the cycle).

        Returns:
            Season: The season opposite to this one in the cycle.
        """
        return Season((self.value + 4) % 8)

    def next(self):
        """Return the next transition that follows this season.

        Returns:
            Transition: The transition that comes after this season.
        """
        return Transition(self.value + 1)

    @property
    def number(self):
        """Get the block number (1-indexed).

        Returns:
            int: The block number (1-8).
        """
        return self.value + 1


class Transition(Enum):
    """Enumeration of the four Solcadre transitions."""
    SUMMER_SOLSTICE = 1
    AUTUMNAL_EQUINOX = 3
    WINTER_SOLSTICE = 5
    VERNAL_EQUINOX = 7

    def flip(self):
        """Return the opposite transition (180 degrees in the cycle).

        Returns:
            Transition: The transition opposite to this one in the cycle.
        """
        return Transition((self.value + 4) % 8)

    def next(self):
        """Return the next season that follows this transition.

        Returns:
            Season: The season that comes after this transition.
        """
        return Season((self.value + 1) % 8)

    @property
    def number(self):
        """Get the block number (1-indexed).

        Returns:
            int: The block number (1-8).
        """
        return self.value + 1


type BlockType = Season | Transition
"""Type alias for either a Season or Transition, representing a calendar block."""


def _block_type_from_index(block_index: int) -> BlockType:
    if block_index % 2 == 0:
        return Season(block_index)
    else:
        return Transition(block_index)


class Weekday(Enum):
    """Enumeration of the seven days of the week.

    The weekdays are numbered starting from Sunday (0) through Saturday (6).
    """
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6

    @staticmethod
    def from_datetime(datetime):
        """Create a Weekday from a datetime object.

        Args:
            datetime: A datetime object to extract the weekday from.

        Returns:
            Weekday: The weekday corresponding to the given datetime.
        """
        return Weekday((datetime.weekday() + 1) % 7)

    @property
    def number(self):
        """Get the weekday number (1-indexed).

        Returns:
            int: The weekday number (1-7, where 1 is Sunday).
        """
        return self.value + 1


@dataclass(frozen=True)
class Day:
    """Represents a day in the Solcadre calendar.

    A day is defined by its solar events (sunrise, sunset) and its position
    within the calendar structure (year, block, day of block).

    Attributes:
        sunrise: The datetime of sunrise for this day.
        sunset: The datetime of sunset for this day.
        next_sunrise: The datetime of sunrise for the next day.
        solar_event: Optional SolarEvent that occurs on this day, if any.
        days_since_epoch: The number of days since the epoch, which serves as an identifier of the date.
    """
    sunrise: datetime
    sunset: datetime
    next_sunrise: datetime
    solar_event: SolarEvent | None
    days_since_epoch: int
    _day_index: int
    _week_index: int
    _block_index: int
    _year_index: int

    def __post_init__(self):
        assert self.sunrise.date() == self.sunset.date()

    @property
    def date(self) -> date:
        """Get the date of this day.

        Returns:
            date: The date corresponding to this day's sunrise.
        """
        return self.sunrise.date()

    @property
    def start(self) -> datetime:
        """Get the start datetime of this day.

        Returns:
            datetime: The sunrise datetime marking the start of the day.
        """
        return self.sunrise

    @property
    def end(self) -> datetime:
        """Get the end datetime of this day.

        Returns:
            datetime: The sunrise datetime marking the end of the day.
        """
        return self.next_sunrise

    @property
    def weekday(self) -> Weekday:
        """Get the weekday for this day.

        Returns:
            Weekday: The weekday enum value.
        """
        return Weekday(self._day_index % 7)

    @property
    def week_number(self) -> int:
        """Get the week number (1-indexed) within the block.

        Returns:
            int: The week number within the current block.
        """
        return self._week_index + 1

    @property
    def block_type(self) -> BlockType:
        """Get the block type (season or transition) this day belongs to.

        Returns:
            BlockType: The Season or Transition this day is part of.
        """
        return _block_type_from_index(self._block_index)

    @property
    def year_number(self) -> int:
        """Get the year number (1-indexed) this day belongs to.

        Returns:
            int: The year number.
        """
        return self._year_index + 1

    def __str__(self):
        """Return a string representation of this day.

        Returns:
            str: A string in the format "year/block/week/weekday".
        """
        return f"{self.year_number}/{self.block_type.number}/{self.week_number}/{self.weekday.number}"

    def __eq__(self, other):
        return self.days_since_epoch == other.days_since_epoch

    def __hash__(self):
        return self.days_since_epoch


@dataclass(frozen=True)
class Week:
    """Represents a week in the Solcadre calendar.

    A week consists of seven consecutive days within a block (season or transition).

    Attributes:
        days: List of seven Day objects that make up this week.
        weeks_since_epoch: The number of weeks since the calendar epoch.
    """
    days: list[Day]
    weeks_since_epoch: int

    @property
    def number(self) -> int:
        """Get the week number (1-indexed) within the block.

        Returns:
            int: The week number within the current block.
        """
        return self.days[0].week_number

    @property
    def block_type(self) -> BlockType:
        """Get the block type (season or transition) this week belongs to.

        Returns:
            BlockType: The Season or Transition this week is part of.
        """
        return self.days[0].block_type

    @property
    def year_number(self) -> int:
        """Get the year number (1-indexed) this week belongs to.

        Returns:
            int: The year number.
        """
        return self.days[0].year_number

    @property
    def start(self) -> datetime:
        """Get the start datetime of this week.

        Returns:
            datetime: The sunrise datetime marking the start of the first day of the week.
        """
        return self.days[0].sunrise

    @property
    def end(self) -> datetime:
        """Get the end datetime of this week.

        Returns:
            datetime: The sunrise datetime marking the end of the last day of the week.
        """
        return self.days[-1].next_sunrise

    @property
    def _week_index(self) -> int:
        return self.days[0]._week_index

    @property
    def _block_index(self) -> int:
        return self.days[0]._block_index

    @property
    def _year_index(self) -> int:
        return self.days[0]._year_index

    def __str__(self):
        """Return a string representation of this week.

        Returns:
            str: A string in the format "year/block/week".
        """
        return f"{self.year_number}/{self.block_type.number}/{self.number}"

    def __eq__(self, other):
        return self._year_index == other._year_index and self._block_index == other._block_index and self._week_index == other._week_index

    def __hash__(self):
        return hash((self._year_index, self._block_index, self._week_index))


@dataclass(frozen=True)
class Block:
    """Represents a block (season or transition) in the Solcadre calendar.

    A block is either a Season (12 weeks) or a Transition (1-2 weeks).

    Attributes:
        weeks: List of Week objects that make up this block.
        blocks_since_epoch: The number of blocks since the calendar epoch.
    """
    weeks: list[Week]
    blocks_since_epoch: int

    @property
    def type(self) -> BlockType:
        """Get the block type (season or transition).

        Returns:
            BlockType: The Season or Transition enum value.
        """
        return self.weeks[0].block_type

    @property
    def year_number(self) -> int:
        """Get the year number (1-indexed) this block belongs to.

        Returns:
            int: The year number.
        """
        return self.weeks[0].year_number

    @property
    def start(self) -> datetime:
        """Get the start datetime of this block.

        Returns:
            datetime: The sunrise datetime marking the start of the first day of the block.
        """
        return self.weeks[0].start

    @property
    def end(self) -> datetime:
        """Get the end datetime of this block.

        Returns:
            datetime: The sunrise datetime marking the end of the last day of the block.
        """
        return self.weeks[-1].end

    @property
    def _block_index(self) -> int:
        return self.weeks[0]._block_index

    @property
    def _year_index(self) -> int:
        return self.weeks[0]._year_index

    def __str__(self):
        """Return a string representation of this block.

        Returns:
            str: A string in the format "year/block".
        """
        return f"{self.year_number}/{self.type.number}"

    def __eq__(self, other):
        return self._year_index == other._year_index and self._block_index == other._block_index

    def __hash__(self):
        return hash((self._year_index, self._block_index))


@dataclass(frozen=True)
class Year:
    """Represents a year in the Solcadre calendar.

    A year consists of a sequence of blocks (seasons and transitions),
    starting with GREENTIDE season and ending with the VERNAL_EQUINOX transition.

    Attributes:
        blocks: List of Block objects (seasons and transitions) that make up this year.
        years_since_epoch: The number of years since the calendar epoch.
    """
    blocks: list[Block]
    years_since_epoch: int

    @property
    def number(self) -> int:
        """Get the year number (1-indexed).

        Returns:
            int: The year number.
        """
        return self.blocks[0].year_number

    @property
    def start(self) -> datetime:
        """Get the start datetime of this year.

        Returns:
            datetime: The sunrise datetime marking the start of the first day of the year.
        """
        return self.blocks[0].start

    @property
    def end(self) -> datetime:
        """Get the end datetime of this year.

        Returns:
            datetime: The sunrise datetime marking the end of the last day of the year.
        """
        return self.blocks[-1].end

    @property
    def _year_index(self) -> int:
        return self.blocks[0]._year_index

    def __str__(self):
        """Return a string representation of this year.

        Returns:
            str: A string containing the year number.
        """
        return f"{self.number}"

    def __eq__(self, other):
        return self._year_index == other._year_index

    def __hash__(self):
        return hash(self._year_index)


class Hemisphere(Enum):
    """Enumeration of the two hemispheres.

    Used to determine how seasons are mapped based on geographic location.
    """
    NORTHERN = auto()
    SOUTHERN = auto()


class LazyList:

    def __init__(self, iterable):
        self._iter = iter(iterable)
        self._cache = []

    def get(self, index: int, default = None):
        try:
            while index >= len(self._cache):
                item = next(self._iter)
                self._cache.append(item)
        except StopIteration:
            return default
        else:
            return self._cache[index]

    def iter_items(self, start_index: int | None, stop_index: int | None):
        index = 0 if start_index is None else start_index
        if stop_index is None:
            while True:
                item = self.get(index)
                if item is None:
                    return
                yield item
                index += 1
        else:
            while index < stop_index:
                yield self[index]
                index += 1

    def __getitem__(self, index: int):
        item = self.get(index)
        assert item is not None
        return item


@dataclass
class Calendar:
    """Calendar system that calculates days based on solar events and geographic location.

    The calendar generates a sequence of days based on sunrise/sunset times for
    a given location. Seasons and transitions are automatically adjusted based on
    the hemisphere.

   Attributes:
        latitude: The latitude for solar calculations (defaults to canonical).
        longitude: The longitude for solar calculations (defaults to canonical).
        timezone: The timezone for solar calculations (defaults to canonical).
        observer: Astral observer object for solar calculations.
        hemisphere: The hemisphere determined from latitude.
        epoch: The first day of the calendar.
    """
    latitude: float = CANONICAL_LATITUDE
    longitude: float = CANONICAL_LONGITUDE
    timezone: zoneinfo.ZoneInfo = CANONICAL_TIMEZONE

    def __post_init__(self):
        """Initialize the calendar with observer, hemisphere, and calculated days."""
        self.observer = astral.Observer(self.latitude, self.longitude)
        self.hemisphere = Hemisphere.NORTHERN if self.latitude > 0 else Hemisphere.SOUTHERN
        self._days = LazyList(self._calc_localized_days())
        self._weeks = LazyList(_group_weeks(self.iter_days()))
        self._blocks = LazyList(_group_blocks(self.iter_weeks()))
        self._years = LazyList(_group_years(self.iter_blocks()))
        self.epoch = next(day for day in self.iter_days())

    def find_day(self, time: datetime) -> Day | None:
        """Find the Day object that contains the given datetime.

        Args:
            time: The datetime to search for.

        Returns:
            Day | None: The Day object containing the time, or None if not found.
        """
        for day in self.iter_days():
            if day.start <= time < day.end:
                return day
        return None

    def find_week(self, time: datetime) -> Week | None:
        """Find the Week object that contains the given datetime.

        Args:
            time: The datetime to search for.

        Returns:
            Week | None: The Week object containing the time, or None if not found.
        """
        for week in self.iter_weeks():
            if week.start <= time < week.end:
                return week
        return None

    def find_block(self, time: datetime) -> Block | None:
        """Find the Block object that contains the given datetime.

        Args:
            time: The datetime to search for.

        Returns:
            Block | None: The Block object containing the time, or None if not found.
        """
        for block in self.iter_blocks():
            if block.start <= time < block.end:
                return block
        return None

    def find_year(self, time: datetime) -> Year | None:
        """Find the Year object that contains the given datetime.

        Args:
            time: The datetime to search for.

        Returns:
            Year | None: The Year object containing the time, or None if not found.
        """
        for year in self.iter_years():
            if year.start <= time < year.end:
                return year
        return None

    def iter_days(self, start_day = None, end_day = None) -> Iterable[Day]:
        """Iterate over days in the calendar.

        Args:
            start_day: Optional Day object to start iteration from (inclusive).
                If None, starts from the beginning.
            end_day: Optional Day object to end iteration at (exclusive).
                If None, continues to the end.

        Returns:
            Iterable[Day]: An iterator over Day objects in chronological order.
        """
        start_index = None if start_day is None else start_day.days_since_epoch
        end_index = None if end_day is None else end_day.days_since_epoch
        return self._days.iter_items(start_index, end_index)

    def iter_weeks(self, start_week = None, end_week = None) -> Iterable[Week]:
        """Iterate over weeks in the calendar.

        Args:
            start_week: Optional Week object to start iteration from (inclusive).
                If None, starts from the beginning.
            end_week: Optional Week object to end iteration at (exclusive).
                If None, continues to the end.

        Returns:
            Iterable[Week]: An iterator over Week objects in chronological order.
        """
        start_index = None if start_week is None else start_week.weeks_since_epoch
        end_index = None if end_week is None else end_week.weeks_since_epoch
        return self._weeks.iter_items(start_index, end_index)

    def iter_blocks(self, start_block = None, end_block = None) -> Iterable[Block]:
        """Iterate over blocks (seasons and transitions) in the calendar.

        Args:
            start_block: Optional Block object to start iteration from (inclusive).
                If None, starts from the beginning.
            end_block: Optional Block object to end iteration at (exclusive).
                If None, continues to the end.

        Returns:
            Iterable[Block]: An iterator over Block objects in chronological order.
        """
        start_index = None if start_block is None else start_block.blocks_since_epoch
        end_index = None if end_block is None else end_block.blocks_since_epoch
        return self._blocks.iter_items(start_index, end_index)

    def iter_years(self, start_year = None, end_year = None) -> Iterable[Year]:
        """Iterate over years in the calendar.

        Args:
            start_year: Optional Year object to start iteration from (inclusive).
                If None, starts from the beginning.
            end_year: Optional Year object to end iteration at (exclusive).
                If None, continues to the end.

        Returns:
            Iterable[Year]: An iterator over Year objects in chronological order.
        """
        start_index = None if start_year is None else start_year.years_since_epoch
        end_index = None if end_year is None else end_year.years_since_epoch
        return self._years.iter_items(start_index, end_index)

    def week_of(self, obj: Day) -> Week:
        """Get the Week object that contains the given day.

        Args:
            obj: The Day object to find the week for.

        Returns:
            Week: The Week object containing the given day.
        """
        return self.block_of(obj).weeks[obj._week_index]

    def block_of(self, obj: Day | Week) -> Block:
        """Get the Block object that contains the given day or week.

        Args:
            obj: The Day or Week object to find the block for.

        Returns:
            Block: The Block object (season or transition) containing the given object.
        """
        return self.year_of(obj).blocks[obj._block_index]

    def year_of(self, obj: Day | Week | Block) -> Year:
        """Get the Year object that contains the given day, week, or block.

        Args:
            obj: The Day, Week, or Block object to find the year for.

        Returns:
            Year: The Year object containing the given object.
        """
        year = self._years[obj._year_index]
        assert year is not None
        return year

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

    def _calc_localized_days(self) -> Iterable[Day]:
        canonical_days = _calc_canonical_days()
        offset = 0
        if self.hemisphere == Hemisphere.NORTHERN:
            offset = 2 * (12 + 1) * 7 # skip ahead half a year
            canonical_days = itertools.islice(canonical_days, offset, None)
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
        assert offset >= 0
        year_index = -1
        next_solar_event_index = 0
        for days_since_epoch, canonical_day in enumerate(canonical_days):
            day_index = canonical_day._day_index
            week_index = canonical_day._week_index
            block_index = canonical_day._block_index
            if self.hemisphere == Hemisphere.NORTHERN:
                block_index = _block_type_from_index(block_index).flip().value
            if _block_type_from_index(block_index) == Season.GREENTIDE and week_index == 0 and day_index == 0:
                year_index += 1
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
                solar_event=solar_event,
                days_since_epoch=days_since_epoch,
                _day_index=day_index,
                _week_index=week_index,
                _block_index=block_index,
                _year_index=year_index
            )
            yield day
            gregorian_date = gregorian_date + timedelta(days=1)


def _group_weeks(days: Iterable[Day]) -> Iterable[Week]:
    weeks_since_epoch = 0
    for _, days_in_week in itertools.groupby(days, key=lambda day: (day._year_index, day._block_index, day._week_index)):
        yield Week(list(days_in_week), weeks_since_epoch)
        weeks_since_epoch += 1

def _group_blocks(weeks: Iterable[Week]) -> Iterable[Block]:
    blocks_since_epoch = 0
    for _, weeks_in_block in itertools.groupby(weeks, key=lambda week: (week._year_index, week._block_index)):
        yield Block(list(weeks_in_block), blocks_since_epoch)
        blocks_since_epoch += 1

def _group_years(blocks: Iterable[Block]) -> Iterable[Year]:
    years_since_epoch = 0
    for _, blocks_in_year in itertools.groupby(blocks, key=lambda block: block._year_index):
        yield Year(list(blocks_in_year), years_since_epoch)
        years_since_epoch += 1

def _sunrise_of_canonical_day(date) -> datetime:
    return astral.sun.sunrise(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date, tzinfo=CANONICAL_TIMEZONE)

def _sunset_of_canonical_day(date) -> datetime:
    return astral.sun.sunset(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date, tzinfo=CANONICAL_TIMEZONE)

LAST_DAY_OF_WEEK = 7 - 1
LAST_WEEK_OF_SEASON = 11

def _calc_canonical_days() -> Iterable[Day]:
    assert Weekday.from_datetime(_sunrise_of_canonical_day(CANONICAL_EPOCH)) == Weekday.SUNDAY
    gregorian_date = CANONICAL_EPOCH
    days_since_epoch = 0
    day_index = 0
    week_index = 0
    block_index = 0
    year_index = 0
    day = Day(
        sunrise=_sunrise_of_canonical_day(gregorian_date),
        sunset=_sunset_of_canonical_day(gregorian_date),
        next_sunrise=_sunrise_of_canonical_day(gregorian_date + timedelta(days=1)),
        solar_event=None,
        days_since_epoch=days_since_epoch,
        _day_index=day_index,
        _week_index=week_index,
        _block_index=block_index,
        _year_index=year_index
    )
    yield day
    while True:
        gregorian_date = gregorian_date + timedelta(days=1)
        sunrise = _sunrise_of_canonical_day(gregorian_date)
        sunset = _sunset_of_canonical_day(gregorian_date)
        next_sunrise = _sunrise_of_canonical_day(gregorian_date + timedelta(days=1))
        days_since_epoch += 1
        if day_index == LAST_DAY_OF_WEEK:
            day_index = 0
            if isinstance(day.block_type, Transition):
                solar_events = [ solar_event for solar_event in SOLAR_EVENTS if abs(solar_event.time.date() - gregorian_date) <= timedelta(days=14) ]
                if not solar_events:
                    return
                [ solar_event ] = solar_events
                leap_week_threshold = _sunset_of_canonical_day(gregorian_date + timedelta(days=1))
                if solar_event.time > leap_week_threshold: # insert a leap week
                    week_index += 1
                else:
                    week_index = 0
                    if day.block_type == Transition.VERNAL_EQUINOX:
                        block_index = 0
                        year_index += 1
                    else:
                        block_index += 1
            elif isinstance(day.block_type, Season) and week_index == LAST_WEEK_OF_SEASON:
                week_index = 0
                block_index += 1
            else:
                week_index += 1
        else:
            day_index += 1
        day = Day(
            sunrise=sunrise,
            sunset=sunset,
            next_sunrise=next_sunrise,
            solar_event=None,
            days_since_epoch=days_since_epoch,
            _day_index=day_index,
            _week_index=week_index,
            _block_index=block_index,
            _year_index=year_index
        )
        yield day
