"""로컬 시각 + 공항(IATA) → UTC/KST."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")


def load_airport_timezones(path: Path | None = None) -> Dict[str, str]:
    base = path or Path(__file__).resolve().parent / "airport_timezones.json"
    with open(base, encoding="utf-8") as f:
        return json.load(f)


def iana_for_airport(iata: str, cache: Dict[str, str] | None = None) -> str:
    iata = iata.strip().upper()
    m = cache or load_airport_timezones()
    if iata not in m:
        raise KeyError(f"Unknown airport IATA: {iata}. Add it to airport_timezones.json")
    return m[iata]


def is_korea_airport(iata: str) -> bool:
    return iana_for_airport(iata) == "Asia/Seoul"


def local_datetime_at_airport(
    day: date,
    t: time,
    airport_iata: str,
    cache: Dict[str, str] | None = None,
) -> datetime:
    z = ZoneInfo(iana_for_airport(airport_iata, cache))
    return datetime.combine(day, t, tzinfo=z)


def to_kst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(_KST)


def utc_from_local(day: date, hm: str, airport_iata: str, cache: Dict[str, str] | None = None) -> datetime:
    """hm = 'HH:MM' 24h at airport local date `day`."""
    h, m = hm.split(":")
    t = time(int(h), int(m))
    local = local_datetime_at_airport(day, t, airport_iata, cache)
    return local.astimezone(ZoneInfo("UTC"))


def hours_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 3600.0


def add_minutes(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=minutes)


def add_hours(dt: datetime, hours: float) -> datetime:
    return dt + timedelta(hours=hours)
