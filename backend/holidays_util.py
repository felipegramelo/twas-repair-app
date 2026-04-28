"""
Brazilian holidays utility.

Returns a set of holiday date strings (DD/MM/YYYY) for a given year,
combining national fixed-date holidays, Easter-based movable holidays,
and regional holidays stored in MongoDB collection `holidays`.
"""
from datetime import date, timedelta
from typing import Set


def _easter_date(year: int) -> date:
    """Anonymous Gregorian algorithm for computing Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def national_holidays(year: int) -> Set[str]:
    """Return Brazilian national holidays for given year as DD/MM/YYYY strings."""
    holidays: Set[str] = set()

    # Fixed national holidays
    fixed = [
        (1, 1),    # Confraternização Universal
        (4, 21),   # Tiradentes
        (5, 1),    # Dia do Trabalho
        (9, 7),    # Independência
        (10, 12),  # Nossa Sra Aparecida
        (11, 2),   # Finados
        (11, 15),  # Proclamação da República
        (12, 25),  # Natal
    ]
    for m, d in fixed:
        holidays.add(f"{d:02d}/{m:02d}/{year}")

    # Movable (Easter-based)
    easter = _easter_date(year)
    carnaval = easter - timedelta(days=47)              # Terça de Carnaval
    sexta_santa = easter - timedelta(days=2)            # Sexta-feira Santa
    corpus_christi = easter + timedelta(days=60)        # Corpus Christi

    for d in (carnaval, sexta_santa, corpus_christi):
        holidays.add(f"{d.day:02d}/{d.month:02d}/{d.year}")

    return holidays


async def all_holidays_for_year(db, year: int) -> Set[str]:
    """National + regional holidays (regional pulled from `holidays` collection)."""
    holidays = national_holidays(year)
    cursor = db.holidays.find({})
    async for h in cursor:
        d = h.get("date", "")
        if d:
            # Only include if matches the year
            try:
                if d.split("/")[2] == str(year):
                    holidays.add(d)
            except (IndexError, ValueError):
                pass
    return holidays


async def all_holidays_in_range(db, dates_ddmmyyyy) -> Set[str]:
    """Holidays covering all years that appear in the given list of DD/MM/YYYY dates."""
    years = set()
    for d in dates_ddmmyyyy:
        try:
            years.add(int(d.split("/")[2]))
        except (IndexError, ValueError):
            continue
    holidays: Set[str] = set()
    for y in years:
        holidays.update(await all_holidays_for_year(db, y))
    return holidays
