"""일일 한도·기간 누적 초과분 계산 (kr_flight_limits 연동)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple

from flight_models import ComputedLeg
from kr_flight_limits import (
    CrewFormation,
    RestFacilityGrade,
    cumulative_limits,
    daily_max_limits,
    max_flight_28d_for_crew,
)


@dataclass
class DailyViolation:
    day_kst: date
    flight_time_hours: float
    fdp_hours: float
    max_ft: float
    max_fdp: float
    over_ft: float
    over_fdp: float


@dataclass
class WindowViolation:
    label: str
    window_days: int
    end_date: date
    duty_hours: float
    flight_hours: float
    max_duty: float | None
    max_flight: float | None
    over_duty: float
    over_flight: float


def _duty_day_kst(leg: ComputedLeg) -> date:
    return leg.show_up_kst.date()


def rollup_by_duty_day(legs: List[ComputedLeg]) -> Dict[date, Tuple[float, float, float]]:
    """날짜(KST, Show up 기준)별 합계: (승무, FDP, 근무)."""
    ft: Dict[date, float] = defaultdict(float)
    fdp: Dict[date, float] = defaultdict(float)
    duty: Dict[date, float] = defaultdict(float)
    for x in legs:
        d = _duty_day_kst(x)
        ft[d] += x.flight_time_hours
        fdp[d] += x.fdp_hours
        duty[d] += x.duty_hours
    days = sorted(set(ft) | set(fdp) | set(duty))
    out: Dict[date, Tuple[float, float, float]] = {}
    for d in days:
        out[d] = (ft.get(d, 0.0), fdp.get(d, 0.0), duty.get(d, 0.0))
    return out


def check_daily_limits(
    legs: List[ComputedLeg],
    crew: CrewFormation,
    facility: RestFacilityGrade,
    *,
    unacclimated: bool = False,
) -> List[DailyViolation]:
    lim = daily_max_limits(crew, facility, unacclimated=unacclimated)
    viol: List[DailyViolation] = []
    for d, (ft, fdp, _) in rollup_by_duty_day(legs).items():
        over_ft = max(0.0, ft - lim.max_flight_time_hours)
        over_fdp = max(0.0, fdp - lim.max_fdp_hours)
        if over_ft > 0 or over_fdp > 0:
            viol.append(
                DailyViolation(
                    day_kst=d,
                    flight_time_hours=ft,
                    fdp_hours=fdp,
                    max_ft=lim.max_flight_time_hours,
                    max_fdp=lim.max_fdp_hours,
                    over_ft=over_ft,
                    over_fdp=over_fdp,
                )
            )
    return sorted(viol, key=lambda v: v.day_kst)


def _sum_range(
    roll: Dict[date, Tuple[float, float, float]],
    start: date,
    end: date,
) -> Tuple[float, float]:
    """(근무 합, 승무 합) — 해당 기간 KST 일자 기준."""
    duty_sum = 0.0
    ft_sum = 0.0
    d = start
    while d <= end:
        if d in roll:
            f, _, du = roll[d]
            ft_sum += f
            duty_sum += du
        d += timedelta(days=1)
    return duty_sum, ft_sum


def check_rolling_windows(
    legs: List[ComputedLeg],
    crew: CrewFormation,
) -> List[WindowViolation]:
    """연속 7일·28일·365일(근무/승무) 누적. 근무·승무는 Show up 일자 기준 합산 근사."""
    roll = rollup_by_duty_day(legs)
    if not roll:
        return []
    c = cumulative_limits()
    mf28 = max_flight_28d_for_crew(crew)
    days_sorted = sorted(roll.keys())
    end = days_sorted[-1]
    start_min = days_sorted[0]
    out: List[WindowViolation] = []

    def window_check(label: str, w: int, max_d: float | None, max_f: float | None) -> None:
        e = end
        while e >= start_min:
            s = e - timedelta(days=w - 1)
            duty_h, ft_h = _sum_range(roll, s, e)
            od = max(0.0, duty_h - max_d) if max_d is not None else 0.0
            of = max(0.0, ft_h - max_f) if max_f is not None else 0.0
            if od > 0 or of > 0:
                out.append(
                    WindowViolation(
                        label=label,
                        window_days=w,
                        end_date=e,
                        duty_hours=duty_h,
                        flight_hours=ft_h,
                        max_duty=max_d,
                        max_flight=max_f,
                        over_duty=od,
                        over_flight=of,
                    )
                )
            e -= timedelta(days=1)

    window_check("7일 근무", 7, c.max_duty_7d, None)
    window_check("28일 근무", 28, c.max_duty_28d, None)
    window_check("28일 승무", 28, None, mf28)
    window_check("365일 승무", 365, None, c.max_flight_365d)
    return out
