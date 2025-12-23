"""Core data types for the Solcadre calendar system.

This module defines the fundamental enums and dataclasses that make up the
calendar: seasons, transitions, weekdays, solar phases, time-of-day helpers,
and the structural Day/Week/Block/Year objects.
"""

__all__ = [
    "Season",
    "Transition",
    "BlockType",
    "block_type_from_index",
    "Weekday",
    "SolarPhase",
    "TimeOfDay",
    "Day",
    "Week",
    "Block",
    "Year",
    "Time",
    "Hemisphere"
]

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum, auto

from .solar_events import SolarEvent


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


def block_type_from_index(block_index: int) -> BlockType:
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


class SolarPhase(Enum):
    """Whether a given moment in a Solcadre day is during daylight or night."""
    DAY = auto()
    NIGHT = auto()

    @property
    def abbreviation(self) -> str:
        """Single-letter abbreviation for the phase."""
        match self:
            case SolarPhase.DAY:   return 'D'
            case SolarPhase.NIGHT: return 'N'
            case _: assert False


@dataclass(frozen=True)
class TimeOfDay:
    """Clock time within a day plus whether it is day or night."""
    time: time
    solar_phase: SolarPhase

    def __str__(self):
        return f"{self.time} {self.solar_phase.abbreviation}"


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
        return block_type_from_index(self._block_index)

    @property
    def year_number(self) -> int:
        """Get the year number (1-indexed) this day belongs to.

        Returns:
            int: The year number.
        """
        return self._year_index + 1

    def solar_phase(self, datetime: datetime) -> SolarPhase:
        assert self.start <= datetime < self.end
        return SolarPhase.DAY if datetime <= self.sunset else SolarPhase.NIGHT

    def time_of_day(self, datetime: datetime) -> TimeOfDay:
        assert self.start <= datetime < self.end
        return TimeOfDay(datetime.time(), self.solar_phase(datetime))

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


@dataclass(frozen=True)
class Time:
    """A specific time point in the calendar."""
    day: Day
    time_of_day: TimeOfDay

    def __str__(self):
        return f"{self.day} {self.time_of_day}"


class Hemisphere(Enum):
    """Enumeration of the two hemispheres.

    Used to determine how seasons are mapped based on geographic location.
    """
    NORTHERN = auto()
    SOUTHERN = auto()
