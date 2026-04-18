"""
대한민국 조종사 비행/근무 한도 (flight limitation_KR.md 기반 데이터).
실행 전 검증용 — 공식 해석은 항공사 FOM 및 담당 부서 기준을 따릅니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple


class CrewFormation(Enum):
    TWO_P = auto()  # 기장1+부기1
    THREE_P_CAP1 = auto()  # 기장1+부기2
    THREE_P_CAP2 = auto()  # 기장2+부기1
    FOUR_P = auto()  # 기장2+부기2


class RestFacilityGrade(Enum):
    """2명 편성은 휴식시설 무관."""
    NA = auto()
    GRADE_1 = auto()
    GRADE_2 = auto()
    GRADE_3 = auto()
    BELOW_GRADE_3 = auto()


# --- §5① 직전 비행근무시간 → 법정 최소 휴식 (시간) ---
def required_min_rest_hours_after_fdp(prior_fdp_hours: float) -> float:
    """
    직전 비행근무시간(FDP) 구간에 따른 법정 최소 휴식시간.
    표는 19~20시간 미만까지 정의; 20시간 이상은 동일 패턴으로 2시간/시간 가산 extrapolation.
    """
    f = float(prior_fdp_hours)
    if f < 0:
        raise ValueError("prior_fdp_hours must be non-negative")
    if f < 8:
        return 10.0
    if f < 9:
        return 11.0
    if f < 10:
        return 12.0
    if f < 11:
        return 13.0
    if f < 12:
        return 14.0
    if f < 13:
        return 15.0
    if f < 14:
        return 16.0
    if f < 15:
        return 17.0
    if f < 16:
        return 18.0
    if f < 17:
        return 20.0
    if f < 18:
        return 22.0
    if f < 19:
        return 24.0
    if f < 20:
        return 26.0
    # 20h 이상: 19~20h 구간에서 26h → 이후 매 시간 +2h
    return 26.0 + 2.0 * (f - 20.0)


def duty_time_hours(
    fdp_hours: float, *, training_or_check: bool = False
) -> float:
    """근무시간 = FDP + 30분(일반) 또는 +1시간(훈련/심사)."""
    extra = 1.0 if training_or_check else 0.5
    return float(fdp_hours) + extra


@dataclass(frozen=True)
class DailyLimits:
    max_flight_time_hours: float
    max_fdp_hours: float


def daily_max_limits(
    crew: CrewFormation,
    facility: RestFacilityGrade,
    *,
    unacclimated: bool = False,
) -> DailyLimits:
    """
    §3 일일 최대 승무시간 / 최대 비행근무시간.
    시차 미적응 시 최대 FDP는 30분 단축(표의 미적응 열).
    """
    u = unacclimated

    if facility == RestFacilityGrade.BELOW_GRADE_3:
        # §3 각주: 3등급 미달 시 최대 승무 12h; 3P/4P는 FDP 상한 별도.
        if crew == CrewFormation.TWO_P:
            return DailyLimits(8.0, 12.5 if u else 13.0)
        max_ft = 12.0
        if crew in (CrewFormation.THREE_P_CAP1, CrewFormation.THREE_P_CAP2):
            max_fdp = 13.5
        elif crew == CrewFormation.FOUR_P:
            max_fdp = 15.0
        else:
            max_fdp = 13.5
        return DailyLimits(max_ft, max_fdp)

    if crew == CrewFormation.TWO_P:
        return DailyLimits(8.0, 12.5 if u else 13.0)

    fac_map = {
        RestFacilityGrade.NA: None,
        RestFacilityGrade.GRADE_1: 1,
        RestFacilityGrade.GRADE_2: 2,
        RestFacilityGrade.GRADE_3: 3,
    }
    g = fac_map.get(facility)
    if g is None:
        raise ValueError("2명 외 편성은 휴식시설 등급(1~3 또는 미달)이 필요합니다.")

    # (max_ft, fdp_normal, fdp_unacclimated)
    table: dict[
        Tuple[CrewFormation, int], Tuple[float, float, float]
    ] = {
        (CrewFormation.THREE_P_CAP1, 1): (12.0, 16.0, 15.5),
        (CrewFormation.THREE_P_CAP1, 2): (12.0, 15.0, 14.5),
        (CrewFormation.THREE_P_CAP1, 3): (12.0, 14.0, 13.5),
        (CrewFormation.THREE_P_CAP2, 1): (13.0, 16.5, 16.0),
        (CrewFormation.THREE_P_CAP2, 2): (13.0, 15.5, 15.0),
        (CrewFormation.THREE_P_CAP2, 3): (13.0, 14.5, 14.0),
        (CrewFormation.FOUR_P, 1): (16.0, 20.0, 19.5),
        (CrewFormation.FOUR_P, 2): (16.0, 19.0, 18.5),
        (CrewFormation.FOUR_P, 3): (16.0, 18.0, 17.5),
    }
    max_ft, fdp_ok, fdp_u = table[(crew, g)]
    return DailyLimits(max_ft, fdp_u if u else fdp_ok)


@dataclass(frozen=True)
class CumulativeLimits:
    max_duty_7d: float
    max_duty_28d: float
    max_flight_28d_two_p: float
    max_flight_28d_rest_relieved: float
    max_flight_365d: float


def cumulative_limits() -> CumulativeLimits:
    """§4 기간별 누적."""
    return CumulativeLimits(
        max_duty_7d=60.0,
        max_duty_28d=190.0,
        max_flight_28d_two_p=100.0,
        max_flight_28d_rest_relieved=120.0,
        max_flight_365d=1000.0,
    )


def max_flight_28d_for_crew(crew: CrewFormation) -> float:
    c = cumulative_limits()
    if crew == CrewFormation.TWO_P:
        return c.max_flight_28d_two_p
    return c.max_flight_28d_rest_relieved


def rest_gap_emoji(rest_hours: float) -> str:
    """비행 사이 휴식 길이 시각화 (요청하신 RAG 개념)."""
    if rest_hours >= 48:
        return "🟢"
    if rest_hours >= 36:
        return "🟠"
    if rest_hours >= 24:
        return "🔴"
    return "⚪"


def fdp_penalty_unacclimated_max_fdp(base_max_fdp: float) -> float:
    """§2: 미적응 출근 시 허용 최대 FDP에서 30분 차감 — 일일 표에 이미 반영된 값과 동일."""
    return max(0.0, base_max_fdp - 0.5)


def check_min_rest_violation(
    prior_fdp_hours: float, actual_rest_hours: float
) -> Tuple[bool, float, float]:
    """
    Returns: (violated, required_min_rest, shortfall_hours)
    shortfall > 0 이면 부족한 시간.
    """
    req = required_min_rest_hours_after_fdp(prior_fdp_hours)
    short = req - actual_rest_hours
    return short > 0, req, max(0.0, short)
