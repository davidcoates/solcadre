import argparse
import zoneinfo
import sys
from datetime import datetime, timezone
import itertools

from .core import *
from .solar_events import SOLAR_EVENTS


def print_block(calendar: Calendar, block: Block, highlight : Day):
    header = "| Week | Sun | Mon | Tue | Wed | Thu | Fri | Sat |"
    width = len(header)
    print(f"- {block} -".center(width))
    print("-" * width)
    print(header)
    print("-" * width)
    for week in block.weeks:
        week_str = [f"  {week.number:>2}  "]
        for day in week.days:
            if day == highlight:
                day_str = "TODAY"
            elif day.solar_event is not None:
                day_str = "SOLAR"
            else:
                day_str = "     "
            week_str.append(day_str)
        print('|' + '|'.join(week_str) + '|')
    print("--------------------------------------------------")
    print("")


def print_calendar(calendar: Calendar, day: Day, blocks: int):
    block = calendar.block_of(day)
    for block in itertools.islice(calendar.iter_blocks(block), blocks):
        print_block(calendar, block, day)


def main():

    parser = argparse.ArgumentParser(description="Solcadre System")

    local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
    parser.add_argument("--latitude", type=float, default=CANONICAL_LATITUDE, help="used to derive sunrise/sunset times (default is that of Sydney, Australia)")
    parser.add_argument("--longitude", type=float, default=CANONICAL_LONGITUDE, help="used to derive sunrise/sunset times (default is that of Sydney, Australia)")
    parser.add_argument("--timezone", type=str, default=None, metavar='TIMEZONE', choices=zoneinfo.available_timezones(), help=f"used when displaying times (default is the system local timezone = {local_timezone})")
    parser.add_argument("-t", "--time", type=str, default=None, help="display the date at the described timepoint (in isoformat), not 'now'")
    subparsers = parser.add_subparsers(dest="command")

    parser_calendar = subparsers.add_parser("calendar", help="display a calendar, with '*' denoting a solstice/equinox")
    parser_calendar.add_argument('--blocks', type=int, default=3, help="the number of blocks (seasons or transitions) to display")

    args = parser.parse_args()

    if args.timezone is None:
        args.timezone = local_timezone
    else:
        args.timezone = zoneinfo.ZoneInfo(args.timezone)

    calendar = Calendar(args.latitude, args.longitude, args.timezone)

    gregorian_date = datetime.fromisoformat(args.time) if args.time is not None else datetime.now()
    if gregorian_date.tzinfo is None:
        gregorian_date = gregorian_date.astimezone(args.timezone)

    day = calendar.find_day(gregorian_date)
    if day is None:
        print(f"failed to convert time({args.time}) to date", file=sys.stderr)
        return

    if args.time is None:
        print(f"It is now {day}.")
    else:
        print(f"{gregorian_date} is {day}.")

    print("")
    print(f"The day begins at {day.start} and ends at {day.end}.")
    if args.command == "calendar":
        print("")
        print_calendar(calendar, day, args.blocks)


if __name__ == "__main__":
    main()
