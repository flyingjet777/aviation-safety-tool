"""PDF 대신 동일 열의 CSV에서 스케줄 로드 (PDF 추출 후 저장용)."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import List

from flight_models import FlightLeg


def load_legs_from_csv(path: Path | str) -> List[FlightLeg]:
    """
    CSV 헤더 (필수):
      dep,arr,day_dep,std_local,sta_local,show_up_local,sta_next_day,flight_no,training
    day_dep = YYYY-MM-DD
    sta_next_day = true/false/1/0
    training = true/false (훈련·심사)
    """
    p = Path(path)
    legs: List[FlightLeg] = []
    with p.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            day = date.fromisoformat(row["day_dep"].strip())
            sta_nd = str(row.get("sta_next_day", "false")).lower() in ("1", "true", "yes")
            tr = str(row.get("training", "false")).lower() in ("1", "true", "yes")
            legs.append(
                FlightLeg(
                    dep=row["dep"].strip(),
                    arr=row["arr"].strip(),
                    day_dep=day,
                    std_local=row["std_local"].strip(),
                    sta_local=row["sta_local"].strip(),
                    show_up_local=row["show_up_local"].strip(),
                    sta_next_day=sta_nd,
                    flight_no=row.get("flight_no", "").strip(),
                    training_or_check=tr,
                )
            )
    return legs
