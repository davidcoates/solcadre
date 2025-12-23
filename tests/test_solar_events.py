import zoneinfo

from solcadre.solar_events import SOLAR_EVENTS


def test_solar_event_localize():
    event = SOLAR_EVENTS[0]
    tz = zoneinfo.ZoneInfo("Australia/Sydney")
    localized = event.localize(tz)

    assert localized.type == event.type
    assert localized.time == event.time.astimezone(tz)
    assert localized.time.tzinfo == tz
