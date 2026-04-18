"""Google Calendar에 비행·휴식 이벤트 생성 (OAuth2)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# google-api-python-client — 선택 설치
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    build = None  # type: ignore

from flight_models import ComputedLeg, RestBetween

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def _service(credentials_path: Path, token_path: Path):
    if build is None:
        raise RuntimeError(
            "google-api-python-client, google-auth-httplib2, google-auth-oauthlib 가 필요합니다. "
            "pip install -r requirements.txt"
        )
    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def push_flights_to_calendar(
    legs: List[ComputedLeg],
    rests: List[RestBetween],
    *,
    calendar_id: str = "primary",
    credentials_path: Optional[Path] = None,
    token_path: Optional[Path] = None,
    dry_run: bool = True,
) -> List[Dict[str, Any]]:
    """
    dry_run=True 이면 API 호출 없이 생성될 이벤트 본문만 반환.
    실제 연동: Google Cloud Console에서 OAuth 클라이언트(JSON)를 credentials.json 으로 저장.
    """
    cred = credentials_path or Path(os.environ.get("GOOGLE_CREDENTIALS", CREDENTIALS_FILE))
    tok = token_path or Path(os.environ.get("GOOGLE_TOKEN", TOKEN_FILE))
    events: List[Dict[str, Any]] = []
    for x in legs:
        l = x.leg
        body = {
            "summary": f"✈ {l.flight_no or ''} {l.dep}-{l.arr} | FT {x.flight_time_hours:.2f}h FDP {x.fdp_hours:.2f}h",
            "start": {"dateTime": l.std_utc.isoformat().replace("+00:00", "Z")},
            "end": {"dateTime": l.sta_utc.isoformat().replace("+00:00", "Z")},
            "description": (
                f"KST STD {x.std_kst.strftime('%Y-%m-%d %H:%M')} "
                f"STA {x.sta_kst.strftime('%Y-%m-%d %H:%M')}\n"
                f"Duty {x.duty_hours:.2f}h"
            ),
        }
        events.append(body)
    for r in rests:
        body = {
            "summary": f"{r.rag_emoji} 휴식 {r.rest_hours:.1f}h ({r.mode}) 법정 {r.required_legal_rest_hours:.1f}h",
            "start": {"dateTime": r.rest_start_utc.isoformat().replace("+00:00", "Z")},
            "end": {"dateTime": r.rest_end_utc.isoformat().replace("+00:00", "Z")},
            "description": (
                f"예상(PDF) 휴식 {r.estimated_rest_hours_pdf or 0:.1f}h\n"
                f"법정 충족: {'예' if r.legal_rest_ok else '아니오'} 부족 {r.shortfall_hours:.2f}h"
            ),
        }
        events.append(body)

    if dry_run or not cred.exists():
        return events

    service = _service(cred, tok)
    created: List[Dict[str, Any]] = []
    for body in events:
        ev = (
            service.events()
            .insert(calendarId=calendar_id, body=body)
            .execute()
        )
        created.append(ev)
    return created
