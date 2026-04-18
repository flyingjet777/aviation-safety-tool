from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from typing import List
import os
from datetime import datetime, date, timedelta
from pathlib import Path

from pdf_parser import parse_schedule_pdf
from limits_engine import calculate_flight_metrics, evaluate_cumulative_limits

app = FastAPI(title="Flight Duty Analyzer API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 정적 파일 서빙 경로 ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent


def serialize_flight(flight: dict) -> dict:
    """
    datetime / timedelta 등 JSON 직렬화 불가 타입을 변환.
    datetime → ISO-8601 문자열, timedelta → total_seconds float
    """
    result = {}
    for key, value in flight.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat() if value else None
        elif isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, timedelta):
            result[key] = value.total_seconds()
        elif isinstance(value, list):
            result[key] = [str(item) for item in value]
        elif isinstance(value, (int, float, str, bool)) or value is None:
            result[key] = value
        else:
            result[key] = str(value)
    return result


# ── API 엔드포인트 ──────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Backend is running successfully."}


@app.post("/api/analyze")
async def analyze_schedules(files: List[UploadFile] = File(...)):
    all_flights = []

    for file in files:
        safe_name = os.path.basename(file.filename or "upload.pdf")
        temp_path = os.path.join("/tmp", safe_name)
        try:
            with open(temp_path, "wb") as f:
                f.write(await file.read())
            flights = parse_schedule_pdf(temp_path)
            all_flights.extend(flights)
        except Exception as e:
            print(f"[ERROR] parsing {file.filename}: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    if not all_flights:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "error": "PDF에서 유효한 비행 스케줄을 찾지 못했습니다."},
        )

    try:
        processed = calculate_flight_metrics(all_flights)
    except Exception as e:
        print(f"[ERROR] calculate_flight_metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": f"비행 메트릭 계산 오류: {str(e)}"},
        )

    import pytz
    KST = pytz.timezone("Asia/Seoul")
    fallback_dt = datetime.max.replace(tzinfo=KST)
    processed.sort(key=lambda x: x["std"] if x.get("std") else fallback_dt)

    try:
        processed = evaluate_cumulative_limits(processed)
    except Exception as e:
        print(f"[ERROR] evaluate_cumulative_limits: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": f"누적 한도 평가 오류: {str(e)}"},
        )

    serialized = [serialize_flight(f) for f in processed]
    return JSONResponse(content={"status": "success", "flights": serialized})


# ── 정적 HTML 파일 서빙 (API 라우트 등록 후에 마운트해야 함) ────────────────

# regulations.html 명시적 라우트
@app.get("/regulations.html")
def serve_regulations():
    return FileResponse(BASE_DIR / "regulations.html")

# 루트 → index.html
@app.get("/")
@app.get("/index.html")
def serve_index():
    return FileResponse(BASE_DIR / "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    print(f"🚀 Flight Duty Analyzer 서버 시작 → http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
