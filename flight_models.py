"""비행 편·스케줄 레코드 (PDF/CSV → 동일 구조)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional


@dataclass
class FlightLeg:
    """한 구간. STD/STA/Show up은 각각 출발·도착 공항 로컬 기준 시각."""

    dep: str  # IATA
    arr: str
    day_dep: date
    std_local: str  # "HH:MM" dep TZ
    sta_local: str  # "HH:MM" arr TZ (도착일은 day_dep 또는 익일 처리용 필드)
    show_up_local: str  # "HH:MM" 보통 출발 기지 로컬 = dep TZ
    sta_next_day: bool = False
    flight_no: str = ""
    training_or_check: bool = False
    # 채워지는 값 (빌더가 설정)
    std_utc: Optional[datetime] = None
    sta_utc: Optional[datetime] = None
    show_up_utc: Optional[datetime] = None


@dataclass
class ComputedLeg:
    """KST/UTC 기준 산출값."""

    leg: FlightLeg
    std_kst: datetime
    sta_kst: datetime
    show_up_kst: datetime
    flight_time_hours: float
    fdp_hours: float
    duty_hours: float


@dataclass
class RestBetween:
    """두 편 사이 휴식."""

    prev_flight_no: str
    next_flight_no: str
    mode: str  # "domestic_kr" | "overseas_layover" | "mixed"
    rest_start_utc: datetime
    rest_end_utc: datetime
    rest_hours: float
    required_legal_rest_hours: float
    legal_rest_ok: bool
    shortfall_hours: float
    rag_emoji: str
    # PDF 예상 휴식 (별도 정의)
    estimated_rest_hours_pdf: Optional[float] = None


@dataclass
class ScheduleContext:
    """편성·기내휴식·공항 이동시간(시간, IATA→시간)."""

    airport_travel_hours: Dict[str, float] = field(default_factory=dict)

    def travel_hours_for(self, dep_iata: str) -> float:
        from timezone_util import is_korea_airport

        if is_korea_airport(dep_iata):
            return 0.0
        return float(self.airport_travel_hours.get(dep_iata.upper(), 2.0))
