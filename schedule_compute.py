"""STD/STA/Show up → UTC/KST, 승무·FDP·근무·휴식(국내/해외) 계산."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from flight_models import (
    ComputedLeg,
    FlightLeg,
    RestBetween,
    ScheduleContext,
)
from kr_flight_limits import (
    check_min_rest_violation,
    duty_time_hours,
    required_min_rest_hours_after_fdp,
    rest_gap_emoji,
)
from timezone_util import (
    add_hours,
    add_minutes,
    hours_between,
    is_korea_airport,
    load_airport_timezones,
    local_datetime_at_airport,
    to_kst,
    utc_from_local,
)
from zoneinfo import ZoneInfo

_UTC = ZoneInfo("UTC")


def _parse_hm(s: str) -> Tuple[int, int]:
    p = s.strip().split(":")
    return int(p[0]), int(p[1])


def leg_times_utc(leg: FlightLeg, tz_cache: Dict[str, str]) -> Tuple[datetime, datetime, datetime]:
    dep = leg.dep.upper()
    arr = leg.arr.upper()
    d0 = leg.day_dep
    sta_day = d0 + timedelta(days=1) if leg.sta_next_day else d0

    std_utc = utc_from_local(d0, leg.std_local, dep, tz_cache)
    show_utc = utc_from_local(d0, leg.show_up_local, dep, tz_cache)

    h, m = _parse_hm(leg.sta_local)
    from datetime import time as dtime

    sta_local_dt = local_datetime_at_airport(sta_day, dtime(h, m), arr, tz_cache)
    sta_utc = sta_local_dt.astimezone(_UTC)

    if show_utc > std_utc:
        # 보통 show <= std; 역전 시 데이터 오류 가능
        pass
    return std_utc, sta_utc, show_utc


def compute_leg(leg: FlightLeg, tz_cache: Dict[str, str]) -> ComputedLeg:
    std_u, sta_u, su_u = leg_times_utc(leg, tz_cache)
    std_k = to_kst(std_u)
    sta_k = to_kst(sta_u)
    su_k = to_kst(su_u)
    ft = hours_between(std_u, sta_u)
    fdp = hours_between(su_u, sta_u)
    dh = duty_time_hours(fdp, training_or_check=leg.training_or_check)
    leg.std_utc, leg.sta_utc, leg.show_up_utc = std_u, sta_u, su_u
    return ComputedLeg(
        leg=leg,
        std_kst=std_k,
        sta_kst=sta_k,
        show_up_kst=su_k,
        flight_time_hours=ft,
        fdp_hours=fdp,
        duty_hours=dh,
    )


def _rest_domestic_kr(prev_sta_u: datetime, next_show_u: datetime) -> Tuple[datetime, datetime]:
    start = add_minutes(prev_sta_u, 30)
    end = next_show_u
    return start, end


def _rest_overseas(
    prev_sta_u: datetime,
    next_std_u: datetime,
    travel_h: float,
) -> Tuple[datetime, datetime]:
    start = add_hours(prev_sta_u, 2.0)
    end = add_hours(next_std_u, -travel_h)
    return start, end


def classify_rest_mode(prev_arr: str, next_dep: str) -> str:
    pk = is_korea_airport(prev_arr)
    nk = is_korea_airport(next_dep)
    if pk and nk:
        return "domestic_kr"
    if not nk and not pk:
        return "overseas_layover"
    return "mixed"


def compute_rest_between(
    prev: ComputedLeg,
    next_: ComputedLeg,
    ctx: ScheduleContext,
    tz_cache: Dict[str, str],
) -> RestBetween:
    """
    국내: STA+30분 ~ 다음 Show up
    해외 출발 전: STA+2h ~ (다음 STD - 공항이동)
    혼합: 보수적으로 해외 규칙과 국내 규칙 중 더 짧은 휴식이 나오는 쪽은 피하고,
    여기서는 — 다음 출발이 한국이면 국내(30분), 다음 출발이 해외면 해외(2h/STD-travel).
    """
    prev_u = prev.leg.sta_utc
    next_u = next_.leg.show_up_utc
    next_std_u = next_.leg.std_utc
    assert prev_u and next_u and next_std_u

    mode = classify_rest_mode(prev.leg.arr, next_.leg.dep)
    travel = ctx.travel_hours_for(next_.leg.dep)

    if mode == "domestic_kr":
        rs, re = _rest_domestic_kr(prev_u, next_u)
    elif mode == "overseas_layover":
        rs, re = _rest_overseas(prev_u, next_std_u, travel)
    else:
        # mixed: 한국 도착 후 해외 출발 → STA+30m ~ 다음 Show up
        # 해외 도착 후 한국 출발 → STA+2h ~ 다음 Show up (모기지/현지 보고)
        pk = is_korea_airport(prev.leg.arr)
        nk = is_korea_airport(next_.leg.dep)
        if pk and not nk:
            rs, re = _rest_domestic_kr(prev_u, next_u)
        elif not pk and nk:
            rs = add_hours(prev_u, 2.0)
            re = next_u
        else:
            rs, re = _rest_domestic_kr(prev_u, next_u)

    rh = max(0.0, hours_between(rs, re))
    req = required_min_rest_hours_after_fdp(prev.fdp_hours)
    bad, _, short = check_min_rest_violation(prev.fdp_hours, rh)
    rag = rest_gap_emoji(rh)

    # PDF 예상 휴식: STA+30분 ~ (다음 STD - 2h), KST 타임라인
    est_start = add_minutes(prev.sta_kst, 30)
    est_end = add_hours(next_.std_kst, -2.0)
    est_h = max(0.0, hours_between(est_start, est_end))

    return RestBetween(
        prev_flight_no=prev.leg.flight_no,
        next_flight_no=next_.leg.flight_no,
        mode=mode,
        rest_start_utc=rs.astimezone(_UTC),
        rest_end_utc=re.astimezone(_UTC),
        rest_hours=rh,
        required_legal_rest_hours=req,
        legal_rest_ok=not bad,
        shortfall_hours=short if bad else 0.0,
        rag_emoji=rag,
        estimated_rest_hours_pdf=est_h,
    )


def build_schedule(
    legs: List[FlightLeg],
    ctx: Optional[ScheduleContext] = None,
) -> Tuple[List[ComputedLeg], List[RestBetween]]:
    tz_cache = load_airport_timezones()
    ctx = ctx or ScheduleContext()
    computed = [compute_leg(l, tz_cache) for l in legs]
    rests: List[RestBetween] = []
    for a, b in zip(computed, computed[1:]):
        rests.append(compute_rest_between(a, b, ctx, tz_cache))
    return computed, rests


def korea_arrival_min_rest_hint(fdp_hours: float) -> float:
    """한국 도착 후 필요 법정 최소 휴식(FDP 기준 §5①)."""
    return required_min_rest_hours_after_fdp(fdp_hours)


def overseas_min_rest_hint(fdp_hours: float) -> float:
    """해외 기준 법정 최소 휴식은 동일 표(직전 FDP)로 안내."""
    return required_min_rest_hours_after_fdp(fdp_hours)
