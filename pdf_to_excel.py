import pandas as pd
from pdf_parser import parse_schedule_pdf
from limits_engine import calculate_flight_metrics, evaluate_cumulative_limits
import os

def export_schedules_to_excel():
    pdf_files = ["202601.pdf", "202602.pdf", "202603.pdf", "202604.pdf"]
    all_final_events = []
    
    print("⏳ Parsing PDF files and analyzing duty...")
    
    for pdf in pdf_files:
        if os.path.exists(pdf):
            print(f"   -> Processing {pdf}...")
            raw_parsed = parse_schedule_pdf(pdf)
            # Use the existing engine to get rich metrics (FDP, Rest, Warnings)
            processed = calculate_flight_metrics(raw_parsed)
            processed = evaluate_cumulative_limits(processed)
            all_final_events.extend(processed)
    
    if not all_final_events:
        print("❌ No data found to export.")
        return

    # Prepare data for DataFrame
    export_rows = []
    for ev in all_final_events:
        export_rows.append({
            "Date (Local)": ev.get("dep_date_str_local", "-"),
            "Title (FLIGHT)": ev.get("flight_no", "-"),
            "Type": ev.get("event_type", "UNKNOWN"),
            "Sector/Place": ev.get("sector", "-"),
            "STD (Local)": ev.get("std_local_str", "-"),
            "STA (Local)": ev.get("sta_local_str", "-"),
            "Flight Time": ev.get("flight_time_str", "0:00"),
            "FDP": ev.get("fdp_str", "0:00"),
            "Rest After": ev.get("rest_period_str", "-"),
            "Status Emo": ev.get("rest_emoji", ""),
            "Warnings": ", ".join(ev.get("warnings", []))
        })

    df = pd.DataFrame(export_rows)
    
    output_path = "Flight_Schedule_Export.xlsx"
    df.to_excel(output_path, index=False)
    
    print(f"✅ Successfully exported {len(export_rows)} events to {output_path}")

if __name__ == "__main__":
    export_schedules_to_excel()
