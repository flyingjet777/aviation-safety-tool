import pdfplumber
import re
from datetime import datetime
import pandas as pd

def parse_schedule_pdf(file_path: str):
    """
    Parse an Asiana Airlines schedule PDF and extract flight events.
    """
    events = []
    current_year = 2026
    current_month = 4
    last_day = 1 # Keep track of the current day in the list

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            month_match = re.search(r'MONTH:\s*(\d{4})(\d{2})', text)
            if month_match:
                current_year = int(month_match.group(1))
                current_month = int(month_match.group(2))
            
            tables = page.extract_tables()
            if not tables: continue
            
            table = tables[0]
            if len(table) < 2: continue
            
            for row in table[1:]:
                if len(row) < 6: continue
                
                date_val = str(row[0] or "").strip()
                flight_no = str(row[1] or "").strip()
                show_up = str(row[2] or "").strip()
                sector = str(row[3] or "").strip()
                std = str(row[4] or "").strip()
                sta = str(row[5] or "").strip()

                # ✅ KEY FIX: Update last_day from DATE column FIRST (highest priority)
                day_match = re.search(r'(\d+)', date_val)
                if day_match:
                    last_day = int(day_match.group(1))
                
                # Snapshot the current day for this row BEFORE parsing STD/STA
                row_day = last_day

                # Determine Event Type
                event_type = "UNKNOWN"
                if "/" in sector:
                    event_type = "FLIGHT"
                elif "OFF" in flight_no or "OFF" in sector:
                    event_type = "OFF"
                elif "STBY" in flight_no or "STBY" in sector:
                    event_type = "STBY"
                elif any(x in flight_no.upper() or x in sector.upper() for x in ["G/S", "GS ", "SIM", "교육"]):
                    event_type = "TRAINING"

                if event_type == "UNKNOWN" and not flight_no: continue

                # Helper to convert "DDHH:MM" or "HH:MM"
                def parse_time(time_str, default_day):
                    if not time_str: return None
                    ts = time_str.replace(':', '').strip()
                    if not ts.isdigit(): return None
                    try:
                        if len(ts) >= 5: # DDHHMM or similar (e.g. "091800")
                            day = int(ts[0:2])
                            hour = int(ts[2:4])
                            minute = int(ts[4:6]) if len(ts) >= 6 else 0
                        else: # HHMM (e.g. "0920")
                            day = default_day
                            hour = int(ts[0:2])
                            minute = int(ts[2:4])
                        return {"day": day, "hour": hour, "minute": minute}
                    except: return None

                std_parsed = parse_time(std, last_day)
                if std_parsed:
                    last_day = std_parsed['day']
                
                sta_parsed = parse_time(sta, last_day)
                if sta_parsed and not std_parsed:
                    last_day = sta_parsed['day']

                show_up_parsed = parse_time(show_up, last_day)

                # ✅ KEY FIX: For events with NO STD/STA, use row_day (from DATE col)
                # This prevents DAY OFF / SIM from all clustering on day=1
                if not std_parsed:
                    std_parsed = {"day": row_day, "hour": 0, "minute": 0}
                if not sta_parsed:
                    sta_parsed = {"day": row_day, "hour": 23, "minute": 59}

                # Always append if there's at least some identifier (flight_no or sector)
                if flight_no or sector:
                    # Concise type deduction
                    e_type = "FLIGHT" if "/" in sector else ("OFF" if "OFF" in flight_no.upper() else ("STBY" if "STBY" in flight_no.upper() else ("TRAINING" if any(x in (flight_no + sector).upper() for x in ["G/S", "GS ", "SIM", "교육"]) else "UNKNOWN")))
                    
                    events.append({
                        "year": current_year,
                        "month": current_month,
                        "date_day": row_day,  # ✅ Always the correct calendar day
                        "flight_no": flight_no or sector,
                        "event_type": e_type,
                        "sector": sector,
                        "show_up_raw": show_up_parsed,
                        "std_raw": std_parsed,
                        "sta_raw": sta_parsed
                    })

    return events

# Simple test if run directly
if __name__ == "__main__":
    flights = parse_schedule_pdf("202601.pdf")
    for f in flights[:3]:
        print(f)
