# ✈️ 항공 피로관리 분석 앱 — MASTER PLAN

> **목적**: 개인 비행스케줄 PDF를 분석해 대한민국 비행시간 제한 규정과 비교하고,  
> 피로도 경고 및 캘린더 연동을 제공하는 웹/앱 제작

---

## 📌 전체 구현 현황 (2026-04-19 기준)

| 기능 | 상태 | 파일 |
|------|------|------|
| PDF 파싱 (DATE/FLIGHT/SECTOR/STD/STA) | ✅ 완료 | `pdf_parser.py` |
| 날짜 파싱 버그 수정 (`MM/DD` → 일 추출) | ✅ 오늘 수정 | `pdf_parser.py` |
| A380A-T 이벤트 타입 분류 수정 (STBY) | ⚠️ 요주의 | `pdf_parser.py` |
| 비행 메트릭 계산 (FDP/FT/Rest) | ✅ 완료 | `limits_engine.py` |
| 한국 규정 데이터 모듈 | ✅ 완료 | `kr_flight_limits.py` |
| limits_engine ↔ kr_flight_limits 연동 | ✅ 오늘 완료 | `limits_engine.py` |
| 법정 최소 휴식 위반 경고 | ✅ 오늘 추가 | `limits_engine.py` |
| 7일 / 28일 / 365일 누적 한도 검사 | ✅ 완료 | `limits_engine.py` |
| 휴식 피로도 이모지 (🟢🟠🔴⚪) | ✅ 오늘 연동 | `limits_engine.py` |
| FastAPI 백엔드 서버 | ✅ 완료 | `main.py` |
| 웹 UI — 달력 뷰 (FullCalendar) | ✅ 완료 | `index.html` |
| 웹 UI — 스케줄 타임라인 테이블 | ✅ 완료 | `index.html` |
| 웹 UI — 7일/28일 누적 피로도 차트 | ✅ 완료 | `index.html` |
| 공항 DB / 시간대 변환 (KST) | ✅ 완료 | `airport_db.py`, `timezone_util.py` |
| 아시아나 노선 DB | ✅ 완료 | `asiana_flight_db.py` |
| 연속 구간 듀티 병합 (멀티레그) | ✅ 완료 | `limits_engine.py` |
| Google Calendar 연동 | 🔧 미완성 | `google_calendar_sync.py` |
| PDF → 엑셀 변환 저장 | 🔧 미완성 | `pdf_to_excel.py` |
| 사진 OCR → 실제 BLOCK/FLIGHT TIME 추출 | ⬜ 미착수 | — |
| 예정 vs. 실제 시간 비교 분석 | ⬜ 미착수 | — |
| 개인 비행기록증명 PDF 출력 | ⬜ 미착수 | — |
| 3개월 / 연간 피로도 경향 분석 | ⬜ 미착수 | — |
| 월별 비행/휴식 분포 통계 테이블 | ⬜ 미착수 | — |

---

## 🔧 현재 알려진 버그 / 주의 사항

### ⚠️ A380A-T / A380B-T 분류 오류
- **현상**: `A380A-T`, `A380B-T`를 현재 `TRAINING`으로 분류 중
- **정의(마스터 플랜)**: A380 A-T / B-T = **대기근무(Standby Duty)**
- **수정 필요**: `pdf_parser.py`의 `_classify_event()` 에서 A380 키워드를 STBY로 분리

### ⚠️ POSN TYP (TL/CR) 미활용
- TL(이륙착륙, P1) / CR(순항, P2) 구분 파싱은 되나 피로도 계산에 미반영
- 추후 승무 편성(2P/3P/4P) 자동 감지에 활용 예정

### ⚠️ 승무 편성(CrewFormation) 미입력
- `kr_flight_limits.py`의 `daily_max_limits()` (3P/4P FDP 한도)는 구현됐으나
- 현재 UI에서 사용자가 편성을 선택하는 인터페이스 없음
- 기본값 2P(기장+부기)로만 계산 중

---

## 📐 핵심 용어 정의

| 용어 | 정의 |
|------|------|
| **Show Up** | 비행근무 보고 시간 = FDP 시작 |
| **승무시간 (FT)** | Ramp out → Ramp in |
| **비행근무시간 (FDP)** | Show up → Ramp in |
| **휴식시간 (Rest)** | 국내: 착륙 Ramp in +30분 → 다음 Show up<br>해외: 착륙 Ramp in +2시간 → 다음 STD −2시간(공항이동) |
| **근무시간 (Duty)** | FDP + 30분 (훈련/심사 시 +1시간) |

---

## 📋 스케줄 PDF 컬럼 해석 (아시아나항공)

| 컬럼 | 형식 | 설명 |
|------|------|------|
| DATE | MM/DD(요일) | 달력 날짜 |
| FLIGHT | 숫자/문자 | 편명 또는 근무 종류 |
| SHOW UP | DDHHMM | 비행근무 보고 시간 (KST) |
| SECTOR | XXX/YYY | 출발/도착 공항 코드 |
| STD | DDHHMM | 예상 출발 (현지 시간) |
| STA | DDHHMM | 예상 도착 (현지 시간) |
| RANK | CAP/FO | 기장(CAP) / 부기장(FO) |
| POSN TYP | TL/CR | TL=이륙착륙(P1), CR=순항(P2) |
| POSN | C/A | C=기장임무, A=부기장임무 |

### FLIGHT 컬럼 이벤트 타입 분류

| 값 | 타입 | 비고 |
|----|------|------|
| 숫자 (601, 711…) | FLIGHT | 실제 비행 |
| DAY OFF | OFF | 휴식일 |
| A380A-T / A380B-T | **STBY** | 대기근무 ← 수정 필요 |
| SIMIP | TRAINING | 시뮬레이터 훈련 |
| G/SIP, G/SSTU | TRAINING | 지상교육 |
| STBY | STBY | 대기 |

---

## 🗺️ 구현 로드맵

### Phase 1 — 기반 완성 (현재)
- [x] PDF 파싱 + 날짜 버그 수정
- [x] FDP / FT / Rest 계산
- [x] 7일 / 28일 / 365일 누적 한도 경고
- [x] 법정 최소 휴식 위반 감지
- [x] 달력 + 테이블 + 피로도 차트 웹 UI
- [ ] A380A-T → STBY 분류 수정
- [ ] 승무 편성 선택 UI (2P / 3P / 4P)

### Phase 2 — 캘린더 연동
- [ ] Google Calendar OAuth 연동 완성 (`google_calendar_sync.py`)
- [ ] iOS 캘린더 (.ics 파일 내보내기)
- [ ] 최소 휴식 종료 시각을 캘린더 이벤트로 자동 생성

### Phase 3 — 데이터 고도화
- [ ] PDF → 엑셀 저장 완성 (`pdf_to_excel.py`)
- [ ] 다중 월 PDF 업로드 시 연속 피로도 분석
- [ ] 3개월 / 연간 피로도 경향 그래프
- [ ] 월별 비행/휴식 분포 통계 테이블

### Phase 4 — 실제 비행 데이터 반영
- [ ] 비행기록 사진 OCR → 실제 BLOCK/FLIGHT TIME 추출
- [ ] 예정(스케줄) vs. 실제 시간 비교 분석
- [ ] 실제 데이터 기반 피로도 재분석

### Phase 5 — 개인 비행기록 관리
- [ ] 개인 비행기록증명 포맷 PDF 자동 생성
- [ ] 연간 누적 비행 시간 통계 (비행기록증명 제출용)

---

## 🏗️ 파일 구조

```
aviation-safety-tool/
├── main.py                  # FastAPI 서버 (포트 9000)
├── pdf_parser.py            # PDF 파싱 (날짜 버그 수정 완료)
├── limits_engine.py         # 비행 메트릭 계산 + 누적 한도
├── kr_flight_limits.py      # 대한민국 규정 데이터 (Single Source of Truth)
├── compliance_engine.py     # 규정 준수 체크 엔진
├── airport_db.py            # 공항 DB + KST 변환
├── asiana_flight_db.py      # 아시아나 노선 DB
├── timezone_util.py         # 시간대 유틸리티
├── google_calendar_sync.py  # Google Calendar 연동 (미완성)
├── analytics.py             # 통계 분석
├── pdf_to_excel.py          # PDF → 엑셀 (미완성)
├── csv_schedule_loader.py   # CSV 스케줄 로더
├── flight_models.py         # 데이터 모델
├── schedule_compute.py      # 스케줄 계산
├── index.html               # 메인 웹 UI
├── regulations.html         # 규정 참조 페이지
├── flight limitation_KR.md  # 대한민국 비행시간 제한 규정 원문
└── airport_timezones.json   # 공항별 시간대 데이터
```

---

## 🔑 다음 우선순위 작업

1. **[즉시]** `A380A-T` / `A380B-T` → `STBY`로 분류 수정  
2. **[즉시]** 승무 편성 선택 UI 추가 (2P 기본, 3P/4P 선택)  
3. **[단기]** Google Calendar 연동 완성  
4. **[단기]** PDF → 엑셀 자동 저장  
5. **[중기]** 다중 월 누적 피로도 분석  



## 추가적으로 수행해야할 작업

아시아나항공의 운항스케줄과 비교하여 ICN 을 출발하여 ICN 으로 돌아오는 편명을 매칭한다. 
예를 들어 ICN/LAX 스케줄과 LAX/ICN 스케줄을 저장하여 기억한다. 
하루에 여러 편이 운항하는 편이 있을 수 있다. (예: 202, 204 또는 222, 224 등)
ICN/LAX, LAX/ICN 의 연결되는 FLIGHT 에 대한 정보를 저장한다. (202/203, 204/201 의 경우도 가능)


## 비행과 휴식의 시간에 대한 정의 



STD 와 STA 는 현지시간을 기준으로 사용해.



- 예상 승무시간 : 스케줄 PDF 파일에서 추출한 STD 부터 STA 까지 시간. pdf 에서 출발공항/도착공항의 로컬 타임으로 제공할 거고 그걸 한국표준시간으로 환산해서 시간을 계산하면 돼.
- 예상 비행근무시간 : 스케줄 PDF 파일에서 추출한 Show up 부터 STA 까지 시간. pdf 에서 출발공항/도착공항의 로컬 타임으로 제공할 거고 그걸 한국표준시간으로 환산해서 시간을 계산하면 돼.
- 예상 휴식시간 : 스케줄 PDF 파일에서 추출한 STA 부터 30분을 더한 시간부터 다음 비행 STD -2시간 전까지 시간. pdf 에서 출발공항/도착공항의 로컬 타임으로 제공할 거고 그걸 한국표준시간으로 환산해서 시간을 계산하면 돼.
- 예상 근무시간 : 예상 비행근무시간에서 30분을 더한 시간. 훈련/심사 비행 시에는 1시간을 더한 시간. 




FDP 의 정의에 맞게 시간 계산의 규칙을 정한다. (STD/STA 는 현지시간 기준)
인천공항 출발 : STD 1시간 35분 전부터 STA 시간까지의 총 시간
국내공항 출발 : STD 1시간 전부터 STA 시간까지의 총 시간
해외공항 출발 : STD 2시간 전부터 STA 시간까지의 총 시간

만약 훈련비행이면 


