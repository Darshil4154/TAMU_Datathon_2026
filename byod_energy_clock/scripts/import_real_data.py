"""Convert collected Google Form exports to the ingest-ready CSV format.

Reads Excel files from data/ and writes CSVs to data/raw/ with
[bracket_code] column headers that ingest.py expects.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1.  Energy Clock check-in responses
# ---------------------------------------------------------------------------
ec_path = ROOT / "data" / "energy_clock_responses.xlsx"
ec = pd.read_excel(ec_path, dtype=str)

# Map original column names to [bracket_code] names the ingest layer expects.
EC_RENAME = {
    "Timestamp": "Timestamp",
    "[consent] I am 18 or older and agree to share these answers. My name will be kept private.": "[consent] Consent",
    "Your first name ": "[anon_code] Name",
    "Energy right now": "[energy] Energy",
    "Focus right now": "[focus] Focus",
    "Hours you slept last night": "[slept_h] Sleep hours",
    "Caffeinated drinks so far today (coffee, energy drink, soda, tea)": "[caffeine_today] Caffeine drinks",
    "When did you last eat a meal or real snack?": "[last_ate] Last ate",
    "Did you take a break away from your screen in the last hour?": "[break_last_hour] Break",
    "Project status": "[progress] Progress",
    "What would help you most right now?": "[would_help] Would help",
}
ec = ec.rename(columns=EC_RENAME)
# Keep only mapped columns
wanted = [c for c in EC_RENAME.values() if c in ec.columns]
ec = ec[wanted]

# Recode free-text meal answers to canonical choices if needed
meal_map = {
    "within 1 hour": "Within 1 hour",
    "1-3 hours ago": "1-3 hours ago",
    "3-6 hours ago": "3-6 hours ago",
    "6+ hours ago": "6+ hours ago",
}
if "[last_ate] Last ate" in ec.columns:
    ec["[last_ate] Last ate"] = ec["[last_ate] Last ate"].fillna("").str.strip().str.lower().map(
        lambda v: next((cv for k, cv in meal_map.items() if k == v), v)
    ).replace("", None)

# Recode break answers
break_map = {"yes": "Yes", "no": "No"}
if "[break_last_hour] Break" in ec.columns:
    ec["[break_last_hour] Break"] = ec["[break_last_hour] Break"].fillna("").str.strip().str.lower().map(
        lambda v: break_map.get(v, v)
    ).replace("", None)

# Recode progress answers
progress_map = {"stuck": "Stuck", "making progress": "Making progress", "almost done": "Almost done"}
if "[progress] Progress" in ec.columns:
    ec["[progress] Progress"] = ec["[progress] Progress"].fillna("").str.strip().str.lower().map(
        lambda v: progress_map.get(v, v)
    ).replace("", None)

out_path = RAW / "checkins.csv"
ec.to_csv(out_path, index=False)
print(f"Wrote {len(ec)} rows to {out_path}")

# ---------------------------------------------------------------------------
# 2.  Fatigue Lab game responses
# ---------------------------------------------------------------------------
fl_path = ROOT / "data" / "fatigue_lab_responses.xlsx"
fl = pd.read_excel(fl_path, dtype=str)

# Columns already have [bracket_code] names; just ensure Timestamp is present.
# The game schema has no consent field. Ingest will use survey consent coverage.
# Rename bare [code] columns to [code] Label form so ingest reads them.
FL_RENAME = {
    "[session_id]": "[session_id] Session",
    "[anon_code]": "[anon_code] Name",
    "[energy]": "[energy] Energy",
    "[reaction_avg_ms]": "[reaction_avg_ms] Avg ms",
    "[reaction_best_ms]": "[reaction_best_ms] Best ms",
    "[reaction_slowest_ms]": "[reaction_slowest_ms] Slowest ms",
    "[false_starts]": "[false_starts] False starts",
    "[time_estimate_s]": "[time_estimate_s] Time estimate",
    "[time_error_s]": "[time_error_s] Time error",
    "[device]": "[device] Device",
    "[client_time]": "[client_time] Client time",
}
fl = fl.rename(columns=FL_RENAME)

# Normalize device values to lowercase
if "[device] Device" in fl.columns:
    fl["[device] Device"] = fl["[device] Device"].fillna("").str.strip().str.lower().replace("", None)

out_fl = RAW / "fatigue_lab.csv"
fl.to_csv(out_fl, index=False)
print(f"Wrote {len(fl)} rows to {out_fl}")
print()
print("Summary:")
print(f"  Check-ins: {len(ec)} rows; consented: {(ec.get('[consent] Consent', pd.Series()) == 'I agree').sum()}")
print(f"  Fatigue Lab: {len(fl)} rows")
print("Next step: run `make data` (or python -m src.pipeline) from the byod_energy_clock folder.")
