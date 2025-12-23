# Installation

## Requirements

- Python 3.10 or higher


## Install from Source

To install from source:

```bash
git clone https://github.com/davidcoates/solcadre.git
cd solcadre
pip install -e .
```

## Quick Start

After installation, you can use Solcadre in your Python code:

```python
from solcadre import Calendar
from datetime import datetime
import zoneinfo

# Create a calendar for a specific location
calendar = Calendar(
    latitude=-33.865143,  # Sydney, Australia
    longitude=151.209900,
    timezone=zoneinfo.ZoneInfo("Australia/Sydney")
)

# Find the day for a specific datetime
now = datetime.now().astimezone()
day = calendar.find_day(now)
print(day)  # e.g., "1/1/1/1" (Year/Block/Week/Weekday)
```
