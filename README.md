# Solcadre

**Solcadre** is a week-based, solar-structured calendar system designed around how people actually organise their time.

Human routines, work, and social life are overwhelmingly structured around the **week**. Solcadre takes the week as its fundamental unit, and builds the rest of the calendar around it.

The year is divided into **four fixed 12-week seasons**, with **explicit transition weeks** between seasons.

**See it in action:** https://solcadre.net

---

## Core ideas

- **The week is the building block**
  All longer periods are composed of a whole number of weeks, so weekly structure never breaks or drifts.

- **Seasons are fixed-length**  
  Each season is exactly 12 weeks long, making seasons comparable and well-suited to training programs, projects, or focused periods of work.

- **Transitions are intentional**  
  One or two transition weeks sit between seasons, aligned closely with the solstices and equinoxes, and are intended for rest, review, or change.

- **Solar alignment without daily complexity**  
  The calendar follows the solar year at the seasonal level, while keeping week-level structure clean and regular.

---

## Why Solcadre?

Most people already plan their lives in weeks: work cycles, training schedules, routines, and rest days are all weekly patterns.

Solcadre makes that implicit structure explicit. By keeping weeks intact and grouping them into fixed-length seasons, it provides a stable framework for planning without constant adjustment or drift.

---

## Implementation

This repository contains a library implementing the Solcadre calendar system.

Calendars are localised by timezone, latitude, and longitude. Days are defined from sunrise to the following sunrise, allowing day boundaries to follow the local solar cycle rather than the civil clock.
