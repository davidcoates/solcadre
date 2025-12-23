"""Implementation of the Solcadre calendar system.

This module provides the core calendar functionality: generating localized days,
weeks, blocks, and years aligned to solar events, as well as helpers to map
arbitrary datetimes to Solcadre Day, Week, Block, Year, and Time objects.
"""

__all__ = [
    "InvalidLatitude",
    "Calendar"
]

import astral
import astral.sun
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable
import itertools
import zoneinfo

from .types import *
from .solar_events import *


CANONICAL_LATITUDE = -33.865143
CANONICAL_LONGITUDE = 151.209900
CANONICAL_TIMEZONE = zoneinfo.ZoneInfo("Australia/Sydney")
CANONICAL_EPOCH = date(2024, 9, 22)


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
        """Initialize the calendar with observer, hemisphere, and cached iterators."""
        self.observer = astral.Observer(self.latitude, self.longitude)
        self.hemisphere = Hemisphere.NORTHERN if self.latitude > 0 else Hemisphere.SOUTHERN
        self._days = LazyList(self._calc_localized_days())
        self._weeks = LazyList(_group_weeks(self.iter_days()))
        self._blocks = LazyList(_group_blocks(self.iter_weeks()))
        self._years = LazyList(_group_years(self.iter_blocks()))
        self.epoch = next(day for day in self.iter_days())

    def find_time(self, time: datetime) -> Time | None:
        """Find the Time object that corresponds to the given time point.

        Args:
            time: A timezone-aware datetime to locate within the calendar.

        Returns:
            Time | None: A Time object representating the time point, or None if not found.
        """
        day = self.find_day(time)
        if day is None:
            return None
        return Time(day, day.time_of_day(time.astimezone(self.timezone)))

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

    def iter_days(self, start_day : Day | None = None, end_day : Day | None = None) -> Iterable[Day]:
        """Iterate over days in the calendar.

        Args:
            start_day: Optional Day object to start iteration from (inclusive).
                If None, starts from the beginning.
            end_day: Optional Day object to end iteration at (exclusive).
                If None, continues to the end.

        Returns:
            Iterable[Day]: An iterator over Day objects in chronological order.
        """
        start_index = None if start_day is None else start_day.index.day_of_calendar
        end_index = None if end_day is None else end_day.index.day_of_calendar
        return self._days.iter_items(start_index, end_index)

    def iter_weeks(self, start_week : Week | None = None, end_week : Week | None = None) -> Iterable[Week]:
        """Iterate over weeks in the calendar.

        Args:
            start_week: Optional Week object to start iteration from (inclusive).
                If None, starts from the beginning.
            end_week: Optional Week object to end iteration at (exclusive).
                If None, continues to the end.

        Returns:
            Iterable[Week]: An iterator over Week objects in chronological order.
        """
        start_index = None if start_week is None else start_week.index.week_of_calendar
        end_index = None if end_week is None else end_week.index.week_of_calendar
        return self._weeks.iter_items(start_index, end_index)

    def iter_blocks(self, start_block : Block | None = None, end_block : Block | None = None) -> Iterable[Block]:
        """Iterate over blocks (seasons and transitions) in the calendar.

        Args:
            start_block: Optional Block object to start iteration from (inclusive).
                If None, starts from the beginning.
            end_block: Optional Block object to end iteration at (exclusive).
                If None, continues to the end.

        Returns:
            Iterable[Block]: An iterator over Block objects in chronological order.
        """
        start_index = None if start_block is None else start_block.index.block_of_calendar
        end_index = None if end_block is None else end_block.index.block_of_calendar
        return self._blocks.iter_items(start_index, end_index)

    def iter_years(self, start_year : Year | None = None, end_year : Year | None = None) -> Iterable[Year]:
        """Iterate over years in the calendar.

        Args:
            start_year: Optional Year object to start iteration from (inclusive).
                If None, starts from the beginning.
            end_year: Optional Year object to end iteration at (exclusive).
                If None, continues to the end.

        Returns:
            Iterable[Year]: An iterator over Year objects in chronological order.
        """
        start_index = None if start_year is None else start_year.index.year_of_calendar
        end_index = None if end_year is None else end_year.index.year_of_calendar
        return self._years.iter_items(start_index, end_index)

    def week_of(self, obj: Day) -> Week:
        """Get the Week object that contains the given day.

        Args:
            obj: The Day object to find the week for.

        Returns:
            Week: The Week object containing the given day.
        """
        return self.block_of(obj).weeks[obj.index.week_of_block]

    def block_of(self, obj: Day | Week) -> Block:
        """Get the Block object that contains the given day or week.

        Args:
            obj: The Day or Week object to find the block for.

        Returns:
            Block: The Block object (season or transition) containing the given object.
        """
        return self.year_of(obj).blocks[obj.index.block_of_year]

    def year_of(self, obj: Day | Week | Block) -> Year:
        """Get the Year object that contains the given day, week, or block.

        Args:
            obj: The Day, Week, or Block object to find the year for.

        Returns:
            Year: The Year object containing the given object.
        """
        year = self._years[obj.index.year_of_calendar]
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
        year_of_calendar = -1
        next_solar_event_index = 0
        for day_of_calendar, canonical_day in enumerate(canonical_days):
            day_of_week = canonical_day.index.day_of_week
            week_of_block = canonical_day.index.week_of_block
            block_of_year = canonical_day.index.block_of_year
            if self.hemisphere == Hemisphere.NORTHERN:
                block_of_year = block_type_from_index(block_of_year).flip().value
            if block_type_from_index(block_of_year) == Season.GREENTIDE and week_of_block == 0 and day_of_week == 0:
                year_of_calendar += 1
            sunrise = self._sunrise_of_day(gregorian_date)
            next_sunrise = self._sunrise_of_day(gregorian_date + timedelta(days=1))
            while next_solar_event_index < len(SOLAR_EVENTS) and SOLAR_EVENTS[next_solar_event_index].time < sunrise:
                next_solar_event_index += 1
            solar_event = None
            if next_solar_event_index < len(SOLAR_EVENTS) and SOLAR_EVENTS[next_solar_event_index].time < next_sunrise:
                solar_event = SOLAR_EVENTS[next_solar_event_index].localize(self.timezone)
            day = Day(
                sunrise=sunrise,
                sunset=self._sunset_of_day(gregorian_date),
                next_sunrise=next_sunrise,
                solar_event=solar_event,
                index=Day.Index(
                    year_of_calendar,
                    block_of_year,
                    week_of_block,
                    day_of_week,
                    day_of_calendar
                )
            )
            yield day
            gregorian_date = gregorian_date + timedelta(days=1)


def _group_weeks(days: Iterable[Day]) -> Iterable[Week]:
    week_of_calendar = 0
    for _, days_in_week in itertools.groupby(days, key=lambda day: day.index.day_of_calendar):
        days_in_week = list(days_in_week)
        index = days_in_week[0].index
        yield Week(days_in_week, Week.Index(
            index.year_of_calendar,
            index.block_of_year,
            index.week_of_block,
            week_of_calendar
       ))
        week_of_calendar += 1

def _group_blocks(weeks: Iterable[Week]) -> Iterable[Block]:
    block_of_calendar = 0
    for _, weeks_in_block in itertools.groupby(weeks, key=lambda week: week.index.week_of_calendar):
        weeks_in_block = list(weeks_in_block)
        index = weeks_in_block[0].index
        yield Block(weeks_in_block, Block.Index(
            index.year_of_calendar,
            index.block_of_year,
            block_of_calendar
        ))
        block_of_calendar += 1

def _group_years(blocks: Iterable[Block]) -> Iterable[Year]:
    year_of_calendar = 0
    for _, blocks_in_year in itertools.groupby(blocks, key=lambda block: block.index.block_of_calendar):
        blocks_in_year = list(blocks_in_year)
        yield Year(blocks_in_year, Year.Index(year_of_calendar))
        year_of_calendar += 1

def _sunrise_of_canonical_day(date) -> datetime:
    return astral.sun.sunrise(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date, tzinfo=CANONICAL_TIMEZONE)

def _sunset_of_canonical_day(date) -> datetime:
    return astral.sun.sunset(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date, tzinfo=CANONICAL_TIMEZONE)

LAST_DAY_OF_WEEK = 7 - 1
LAST_WEEK_OF_SEASON = 11

def _calc_canonical_days() -> Iterable[Day]:
    assert Weekday.from_datetime(_sunrise_of_canonical_day(CANONICAL_EPOCH)) == Weekday.SUNDAY
    gregorian_date = CANONICAL_EPOCH
    year_of_calendar = 0
    block_of_year = 0
    week_of_block = 0
    day_of_week = 0
    day_of_calendar = 0
    day = Day(
        sunrise=_sunrise_of_canonical_day(gregorian_date),
        sunset=_sunset_of_canonical_day(gregorian_date),
        next_sunrise=_sunrise_of_canonical_day(gregorian_date + timedelta(days=1)),
        solar_event=None,
        index=Day.Index(
            year_of_calendar,
            block_of_year,
            week_of_block,
            day_of_week,
            day_of_calendar
        )
    )
    yield day
    while True:
        gregorian_date = gregorian_date + timedelta(days=1)
        sunrise = _sunrise_of_canonical_day(gregorian_date)
        sunset = _sunset_of_canonical_day(gregorian_date)
        next_sunrise = _sunrise_of_canonical_day(gregorian_date + timedelta(days=1))
        day_of_calendar += 1
        if day_of_week == LAST_DAY_OF_WEEK:
            day_of_week = 0
            if isinstance(day.block_type, Transition):
                solar_events = [ solar_event for solar_event in SOLAR_EVENTS if abs(solar_event.time.date() - gregorian_date) <= timedelta(days=14) ]
                if not solar_events:
                    return
                [ solar_event ] = solar_events
                leap_week_threshold = _sunset_of_canonical_day(gregorian_date + timedelta(days=1))
                if solar_event.time > leap_week_threshold: # insert a leap week
                    week_of_block += 1
                else:
                    week_of_block = 0
                    if day.block_type == Transition.VERNAL_EQUINOX:
                        block_of_year = 0
                        year_of_calendar += 1
                    else:
                        block_of_year += 1
            elif isinstance(day.block_type, Season) and week_of_block == LAST_WEEK_OF_SEASON:
                week_of_block = 0
                block_of_year += 1
            else:
                week_of_block += 1
        else:
            day_of_week += 1
        day = Day(
            sunrise=sunrise,
            sunset=sunset,
            next_sunrise=next_sunrise,
            solar_event=None,
            index=Day.Index(
                year_of_calendar,
                block_of_year,
                week_of_block,
                day_of_week,
                day_of_calendar
            )
        )
        yield day
