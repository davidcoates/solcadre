"""Core data types for the Solcadre calendar system.

This module defines the fundamental enums and dataclasses that make up the
calendar: seasons, transitions, weekdays, time-of-day helpers, and the
structural Day/Week/Block/Year objects.
"""

__all__ = [
    "Block",
    "BlockType",
    "Day",
    "Meridiem",
    "Season",
    "Time",
    "TimeOfDay",
    "Transition",
    "Week",
    "Weekday",
    "Year",
    "block_type_from_index",
]

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum, auto

from .solar_events import SolarEvent


class Season(Enum):
    """Enumeration of the four Solcadre seasons."""
    ONE = 0
    TWO = 1
    THREE = 2
    FOUR = 3

    def next(self):
        """Return the transition that follows this season.

        Returns:
            Transition: The transition that comes after this season.
        """
        return Transition(self.value)

    @property
    def number(self):
        """Get the season number (1-indexed).

        Returns:
            int: The season number (1-4).
        """
        return self.value + 1

    def __str__(self):
        return f"{self.number}S"


class Transition(Enum):
    """Enumeration of the four Solcadre transitions."""
    ONE = 0
    TWO = 1
    THREE = 2
    FOUR = 3

    def next(self):
        """Return the season that follows this transition.

        Returns:
            Season: The season that comes after this transition.
        """
        return Season((self.value + 1) % 4)

    @property
    def number(self):
        """Get the transition number (1-indexed).

        Returns:
            int: The transition number (1-4).
        """
        return self.value + 1

    def __str__(self):
        return f"{self.number}T"


type BlockType = Season | Transition
"""Type alias for either a Season or Transition, representing a calendar block."""


def block_type_from_index(block_index: int) -> BlockType:
    """Decode a zero-based block-of-year index (0-7) into its Season or Transition.

    Args:
        block_index: Zero-based index of the block within the year (0-7).

    Returns:
        BlockType: The Season or Transition occupying that position in the year.
    """
    if block_index % 2 == 0:
        return Season(block_index // 2)
    else:
        return Transition(block_index // 2)


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


class Meridiem(Enum):
    """Whether a given moment falls before or after a day's solar noon.

    The literal, etymological meaning of ante/post meridiem: before or
    after the sun's transit, rather than before or after the clock reads
    12:00.
    """
    ANTE = auto()
    POST = auto()

    @property
    def abbreviation(self) -> str:
        """Single-letter abbreviation for the meridiem."""
        match self:
            case Meridiem.ANTE: return 'A'
            case Meridiem.POST: return 'P'
            case _: assert False

    def __str__(self):
        return self.abbreviation


@dataclass(frozen=True)
class TimeOfDay:
    """Civil time within a day plus its meridiem."""
    time: time
    meridiem: Meridiem

    def __str__(self):
        return f"{self.time} {self.meridiem}"


@dataclass(frozen=True)
class Day:
    """Represents a day in the Solcadre calendar.

    A day is defined by solar midnight to the next solar midnight, and its
    position within the calendar structure (year, block, day of block).

    Attributes:
        solar_midnight: The datetime of solar midnight marking the start of this day.
        solar_noon: The datetime of solar noon for this day.
        next_solar_midnight: The datetime of solar midnight marking the end of this day.
        sunrise: The datetime of sunrise for this day, or None if the sun does not
            rise on this day (polar day/night).
        sunset: The datetime of sunset for this day, or None if the sun does not
            set on this day (polar day/night).
        solar_event: Optional SolarEvent that occurs on this day, if any.
        index: Day.Index locating this day within the calendar.
    """
    solar_midnight: datetime
    solar_noon: datetime
    next_solar_midnight: datetime
    sunrise: datetime | None
    sunset: datetime | None
    solar_event: SolarEvent | None

    @dataclass(frozen=True)
    class Index:
        """Indices locating this day within the Solcadre calendar.

        Attributes:
            year_of_calendar: Zero-based year index since the epoch.
            block_of_year: Zero-based block index within the year.
            week_of_block: Zero-based week index within the block.
            day_of_week: Zero-based weekday index (0 = Sunday).
            day_of_calendar: Zero-based day index since the epoch.
        """
        year_of_calendar: int
        block_of_year: int
        week_of_block: int
        day_of_week: int
        day_of_calendar: int

    index: Index

    def __post_init__(self):
        assert self.solar_midnight < self.solar_noon < self.next_solar_midnight

    @property
    def date(self) -> date:
        """Get the civil date of this day.

        Returns:
            date: The civil date of solar noon.
        """
        return self.solar_noon.date()

    @property
    def start(self) -> datetime:
        """Get the start datetime of this day.

        Returns:
            datetime: The solar midnight datetime marking the start of the day.
        """
        return self.solar_midnight

    @property
    def end(self) -> datetime:
        """Get the end datetime of this day.

        Returns:
            datetime: The solar midnight datetime marking the end of the day.
        """
        return self.next_solar_midnight

    @property
    def weekday(self) -> Weekday:
        """Get the weekday for this day.

        Returns:
            Weekday: The weekday enum value.
        """
        return Weekday(self.index.day_of_week)

    @property
    def week_number(self) -> int:
        """Get the week number (1-indexed) within the block.

        Returns:
            int: The week number within the current block.
        """
        return self.index.week_of_block + 1

    @property
    def block_type(self) -> BlockType:
        """Get the block type (season or transition) this day belongs to.

        Returns:
            BlockType: The Season or Transition this day is part of.
        """
        return block_type_from_index(self.index.block_of_year)

    @property
    def year_number(self) -> int:
        """Get the year number (1-indexed) this day belongs to.

        Returns:
            int: The year number.
        """
        return self.index.year_of_calendar + 1

    @property
    def days_since_epoch(self) -> int:
        return self.index.day_of_calendar

    def meridiem(self, datetime: datetime) -> Meridiem:
        assert self.start <= datetime < self.end
        return Meridiem.ANTE if datetime < self.solar_noon else Meridiem.POST

    def time_of_day(self, datetime: datetime) -> TimeOfDay:
        assert self.start <= datetime < self.end
        return TimeOfDay(datetime.time(), self.meridiem(datetime))

    def __str__(self):
        return f"{self.year_number:02}-{self.block_type}-{self.week_number:02}/{self.weekday.number:01}"

    def __eq__(self, other):
        return self.index.day_of_calendar == other.index.day_of_calendar

    def __hash__(self):
        return hash(self.index.day_of_calendar)


@dataclass(frozen=True)
class Week:
    """Represents a week in the Solcadre calendar.

    A week consists of seven consecutive days within a block (season or transition).

    Attributes:
        days: List of seven Day objects that make up this week.
        index: Week.Index locating this week within the calendar.
    """
    days: list[Day]

    @dataclass(frozen=True)
    class Index:
        """Indices locating this week within the Solcadre calendar.

        Attributes:
            year_of_calendar: Zero-based year index since the epoch.
            block_of_year: Zero-based block index within the year.
            week_of_block: Zero-based week index within the block.
            week_of_calendar: Zero-based week index since the epoch.
        """
        year_of_calendar: int
        block_of_year: int
        week_of_block: int
        week_of_calendar: int

    index: Index

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
            datetime: The solar midnight datetime marking the start of the first day of the week.
        """
        return self.days[0].start

    @property
    def end(self) -> datetime:
        """Get the end datetime of this week.

        Returns:
            datetime: The solar midnight datetime marking the end of the last day of the week.
        """
        return self.days[-1].end

    def __str__(self):
        return f"{self.year_number:02}-{self.block_type}-{self.number:02}"

    def __eq__(self, other):
        return self.index.week_of_calendar == other.index.week_of_calendar

    def __hash__(self):
        return hash(self.index.week_of_calendar)


@dataclass(frozen=True)
class Block:
    """Represents a block (season or transition) in the Solcadre calendar.

    A block is either a Season (12 weeks) or a Transition (1-2 weeks).

    Attributes:
        weeks: List of Week objects that make up this block.
        index: Block.Index locating this block within the calendar.
    """
    weeks: list[Week]

    @dataclass(frozen=True)
    class Index:
        """Indices locating this block within the Solcadre calendar.

        Attributes:
            year_of_calendar: Zero-based year index since the epoch.
            block_of_year: Zero-based block index within the year.
            block_of_calendar: Zero-based block index since the epoch.
        """
        year_of_calendar: int
        block_of_year: int
        block_of_calendar: int

    index: Index

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
            datetime: The solar midnight datetime marking the start of the first day of the block.
        """
        return self.weeks[0].start

    @property
    def end(self) -> datetime:
        """Get the end datetime of this block.

        Returns:
            datetime: The solar midnight datetime marking the end of the last day of the block.
        """
        return self.weeks[-1].end

    def __str__(self):
        return f"{self.year_number:02}-{self.type}"

    def __eq__(self, other):
        return self.index.block_of_calendar == other.index.block_of_calendar

    def __hash__(self):
        return hash(self.index.block_of_calendar)


@dataclass(frozen=True)
class Year:
    """Represents a year in the Solcadre calendar.

    A year consists of a sequence of blocks (seasons and transitions),
    starting with Season.ONE and ending with Transition.FOUR.

    Attributes:
        blocks: List of Block objects (seasons and transitions) that make up this year.
        index: Year.Index locating this year within the calendar.
    """
    blocks: list[Block]

    @dataclass(frozen=True)
    class Index:
        """Indices locating this year within the Solcadre calendar.

        Attributes:
            year_of_calendar: Zero-based year index since the epoch.
        """
        year_of_calendar: int

    index: Index

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
            datetime: The solar midnight datetime marking the start of the first day of the year.
        """
        return self.blocks[0].start

    @property
    def end(self) -> datetime:
        """Get the end datetime of this year.

        Returns:
            datetime: The solar midnight datetime marking the end of the last day of the year.
        """
        return self.blocks[-1].end

    def __str__(self):
        return f"{self.number:02}"

    def __eq__(self, other):
        return self.index.year_of_calendar == other.index.year_of_calendar

    def __hash__(self):
        return hash(self.index.year_of_calendar)


@dataclass(frozen=True)
class Time:
    """A specific time point in the calendar."""
    day: Day
    time_of_day: TimeOfDay

    def __str__(self):
        return f"{self.day} {self.time_of_day}"
