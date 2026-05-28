import pdfplumber
import re
from datetime import datetime
import pandas as pd

# 대기근무(Standby) 키워드: A380A-T / A380B-T 는 STBY (마스터 플랜 정의)
STBY_KEYWORDS = ["STBY"]
import re as _re
_STBY_PATTERN = _re.compile(r'A380[A-Z]-T', _re.IGNORECASE)

# 훈련 이벤트 키워드 (기종 코드 제외 — A380*-T 는 STBY 로 별도 처리)
TRAINING_KEYWORDS = [
    "G/S", "GS ", "SIM", "교육",
    "CHECK", "TRN", "EVAL", "OE", "IOE", "LPC", "PC"
]

def _classify_event(flight_no: str, sector: str) -> str:
    """FLIGHT 번호와 SECTOR 문자열로 이벤트 타입을 분류."""
    fn = flight_no.upper()
    sec = sector.upper()
    combined = fn + sec
    if "/" in sector:
        return "FLIGHT"
    if "OFF" in fn or "OFF" in sec:
        return "OFF"
    # A380A-T / A380B-T = 대기근무(STBY), 일반 STBY 포함
    if any(kw in combined for kw in STBY_KEYWORDS) or _STBY_PATTERN.search(combined):
        return "STBY"
    if any(kw in combined for kw in TRAINING_KEYWORDS):
        return "TRAINING"
    return "UNKNOWN"


def parse_schedule_pdf(file_path: str):
    """
    Parse an Asiana Airlines schedule PDF and extract flight events.
    DATE 컬럼 형식: 'MM/DD(요일)'  →  슬래시 뒤 DD 값을 day로 사용.
    """
    events = []
    current_year = 2026
    current_month = 4
    last_day = 1

    # parse_time은 루프 밖에 정의 (클로저 재정의 방지)
    def parse_time(time_str, default_day):
        """'DDHH:MM' 또는 'HHMM' 문자열을 {'day', 'hour', 'minute'} dict로 변환."""
        if not time_str:
            return None
        ts = time_str.replace(':', '').strip()
        if not ts.isdigit():
            return None
        try:
            if len(ts) >= 5:          # DDHHMM (e.g. "091840")
                day    = int(ts[0:2])
                hour   = int(ts[2:4])
                minute = int(ts[4:6]) if len(ts) >= 6 else 0
            else:                      # HHMM (e.g. "0920")
                day    = default_day
                hour   = int(ts[0:2])
                minute = int(ts[2:4])
            return {"day": day, "hour": hour, "minute": minute}
        except Exception:
            return None

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            month_match = re.search(r'MONTH:\s*(\d{4})(\d{2})', text)
            if month_match:
                current_year  = int(month_match.group(1))
                current_month = int(month_match.group(2))

            tables = page.extract_tables()
            if not tables:
                continue

            table = tables[0]
            if len(table) < 2:
                continue

            for row in table[1:]:
                if len(row) < 6:
                    continue

                date_val  = str(row[0] or "").strip()
                flight_no = str(row[1] or "").strip()
                show_up   = str(row[2] or "").strip()
                sector    = str(row[3] or "").strip()
                std       = str(row[4] or "").strip()
                sta       = str(row[5] or "").strip()

                # ── DATE 컬럼 파싱 ────────────────────────────────────────
                # 형식: 'MM/DD(요일)'  →  슬래시 뒤 DD 그룹을 사용
                # r'(\d+)'는 첫 번째 숫자(=월)를 잡아 항상 1이 되는 버그가 있었음
                date_day_match = re.search(r'\d{1,2}/(\d{1,2})', date_val)
                if date_day_match:
                    last_day = int(date_day_match.group(1))

                # 이 행의 날짜 스냅샷 (STD 파싱 전에 저장)
                row_day = last_day

                # ── 이벤트 타입 분류 ──────────────────────────────────────
                event_type = _classify_event(flight_no, sector)

                # 식별자가 없는 빈 행은 건너뜀
                if event_type == "UNKNOWN" and not flight_no:
                    continue

                # ── 시간 파싱 ─────────────────────────────────────────────
                std_parsed     = parse_time(std, last_day)
                if std_parsed:
                    last_day = std_parsed['day']

                sta_parsed     = parse_time(sta, last_day)
                if sta_parsed and not std_parsed:
                    last_day = sta_parsed['day']

                show_up_parsed = parse_time(show_up, last_day)

                # STD/STA 없는 이벤트(OFF/SIM 등): row_day 기반 종일 범위로 설정
                if not std_parsed:
                    std_parsed = {"day": row_day, "hour": 0,  "minute": 0}
                if not sta_parsed:
                    sta_parsed = {"day": row_day, "hour": 23, "minute": 59}

                if flight_no or sector:
                    events.append({
                        "year":         current_year,
                        "month":        current_month,
                        "date_day":     row_day,          # 올바른 달력 날짜
                        "flight_no":    flight_no or sector,
                        "event_type":   event_type,
                        "sector":       sector,
                        "show_up_raw":  show_up_parsed,
                        "std_raw":      std_parsed,
                        "sta_raw":      sta_parsed,
                    })

    return events


# Simple test if run directly
if __name__ == "__main__":
    flights = parse_schedule_pdf("202601.pdf")
    for f in flights[:5]:
        print(f)
