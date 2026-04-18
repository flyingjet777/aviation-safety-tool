"""7·28·90·365일 경향, 월별 표, 단순 피로 경고."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple

from flight_models import ComputedLeg, RestBetween
from compliance_engine import rollup_by_duty_day
from timezone_util import to_kst
from zoneinfo import ZoneInfo

_UTC = ZoneInfo("UTC")


@dataclass
class RollingStats:
    label: str
    days: int
    total_flight_hours: float
    total_fdp_hours: float
    total_duty_hours: float
    total_rest_hours: float


def _sum_legs_in_range(
    legs: List[ComputedLeg],
    start: date,
    end: date,
) -> Tuple[float, float, float]:
    ft = fdp = du = 0.0
    for x in legs:
        d = x.show_up_kst.date()
        if start <= d <= end:
            ft += x.flight_time_hours
            fdp += x.fdp_hours
            du += x.duty_hours
    return ft, fdp, du


def _rest_hours_in_window(rests: List[RestBetween], start: date, end: date) -> float:
    s = 0.0
    for r in rests:
        u = r.rest_start_utc
        if u.tzinfo is None:
            u = u.replace(tzinfo=_UTC)
        d0 = to_kst(u).date()
        if start <= d0 <= end:
            s += r.rest_hours
    return s


def rolling_stats(
    legs: List[ComputedLeg],
    rests: List[RestBetween],
    windows: Tuple[int, ...] = (7, 28, 90, 365),
) -> List[RollingStats]:
    if not legs:
        return []
    last = max(x.show_up_kst.date() for x in legs)
    first = min(x.show_up_kst.date() for x in legs)
    out: List[RollingStats] = []
    for w in windows:
        start = max(first, last - timedelta(days=w - 1))
        ft, fdp, du = _sum_legs_in_range(legs, start, last)
        rh = _rest_hours_in_window(rests, start, last)
        out.append(
            RollingStats(
                label=f"최근 {w}일",
                days=w,
                total_flight_hours=round(ft, 2),
                total_fdp_hours=round(fdp, 2),
                total_duty_hours=round(du, 2),
                total_rest_hours=round(rh, 2),
            )
        )
    return out


def monthly_table(legs: List[ComputedLeg]) -> Dict[str, Tuple[float, float]]:
    """월별(YYYY-MM) (비행근무 FDP 합, 근무 Duty 합). 휴식은 일자 배분 없이 별도 입력 전까지 '-'."""
    mfdp: Dict[str, float] = defaultdict(float)
    mdu: Dict[str, float] = defaultdict(float)
    for x in legs:
        d = x.show_up_kst.date()
        key = f"{d.year:04d}-{d.month:02d}"
        mfdp[key] += x.fdp_hours
        mdu[key] += x.duty_hours
    keys = sorted(mfdp.keys())
    return {k: (round(mfdp[k], 2), round(mdu[k], 2)) for k in keys}


def monthly_rest_hours(rests: List[RestBetween]) -> Dict[str, float]:
    """휴식 시작일(KST) 기준 월별 휴식 시간 합."""
    out: Dict[str, float] = defaultdict(float)
    for r in rests:
        u = r.rest_start_utc
        if u.tzinfo is None:
            u = u.replace(tzinfo=_UTC)
        d = to_kst(u).date()
        key = f"{d.year:04d}-{d.month:02d}"
        out[key] += r.rest_hours
    return {k: round(v, 2) for k, v in sorted(out.items())}


def fatigue_warnings(legs: List[ComputedLeg], rests_total_hours: float) -> List[str]:
    """휴리스틱 경고(참고용)."""
    warn: List[str] = []
    if not legs:
        return warn
    roll = rollup_by_duty_day(legs)
    for d, (_, fdp, _) in roll.items():
        if fdp > 12.0:
            warn.append(f"{d}: 일 FDP {fdp:.1f}h — 장시간 FDP 구간, 피로 누적 유의")
    avg_ft = sum(x.flight_time_hours for x in legs) / len(legs)
    if avg_ft > 8.0:
        warn.append(f"구간 평균 승무 {avg_ft:.1f}h/편 — 상한에 근접할 수 있음")
    if rests_total_hours < len(legs) * 10.0:
        warn.append("편·휴식 비율이 낮음 — 스케줄·휴식 정의 재확인 권장")
    return warn


def format_monthly_markdown_table(
    monthly: Dict[str, Tuple[float, float]],
    monthly_rest: Dict[str, float] | None = None,
) -> str:
    lines = [
        "| 월 | 비행근무(FDP) 합(h) | 근무(Duty) 합(h) | 휴식 합(h) |",
        "|---|---:|---:|---:|",
    ]
    keys = sorted(set(monthly.keys()) | set(monthly_rest or []))
    for k in keys:
        fdp, du = monthly.get(k, (0.0, 0.0))
        mr = (monthly_rest or {}).get(k, 0.0)
        lines.append(f"| {k} | {fdp} | {du} | {mr} |")
    return "\n".join(lines)
