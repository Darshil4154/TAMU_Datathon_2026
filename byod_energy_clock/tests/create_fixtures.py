"""Reproducibly write clearly labeled synthetic collection records."""
from pathlib import Path
import uuid
import numpy as np
import pandas as pd


def create() -> None:
    """Create fictional repeated participants, never in production data/."""
    root = Path(__file__).parent / "fixtures"
    root.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    checks, games = [], []
    for person in range(12):
        for hour in [18, 21, 24, 27, 30, 33]:
            time = pd.Timestamp("2026-11-07", tz="America/Chicago") + pd.Timedelta(hours=hour, minutes=person)
            energy = int(np.clip(round(4 - 2 * np.exp(-((hour - 27) / 3) ** 2) + rng.normal(0, .65)), 1, 5))
            checks.append({"Timestamp": time.strftime("%m/%d/%Y %H:%M:%S"), "[consent] Consent": "I agree", "[anon_code] Name": f"FAKE Person {person}", "[energy] Energy": energy, "[focus] Focus": energy, "[slept_h] Sleep": 4 + person % 5, "[caffeine_today] Drinks": (person + hour // 3) % 5, "[last_ate] Meal": ["Within 1 hour", "1-3 hours ago", "3-6 hours ago", "6+ hours ago"][(person + hour // 6) % 4], "[break_last_hour] Break": "Yes" if (person + hour // 3) % 2 else "No", "[progress] Progress": "Stuck" if energy < 3 else "Making progress", "[would_help] Help": "Sleep, A short break" if energy < 3 else "Food, Water", "is_fake": True})
            reaction = round(620 - 65 * energy + rng.normal(0, 55), 1)
            estimate = round(10 + rng.normal(0, 1.5), 2)
            games.append({"Timestamp": time.strftime("%m/%d/%Y %H:%M:%S"), "[session_id] Session": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"FAKE-{person}-{hour}")), "[anon_code] Name": f"FAKE Person {person}", "[consent] Consent": "I agree", "[energy] Energy": energy, "[reaction_avg_ms] Average": reaction, "[reaction_best_ms] Best": reaction - 40, "[reaction_slowest_ms] Slowest": reaction + 60, "[false_starts] Starts": int(rng.integers(0, 3)), "[time_estimate_s] Estimate": estimate, "[time_error_s] Error": estimate - 10, "[device] Device": "station" if person % 2 else "roving", "[client_time] Time": (time + pd.Timedelta(minutes=5)).isoformat(), "is_fake": True})
    pd.DataFrame(checks).to_csv(root / "FAKE_checkins.csv", index=False)
    pd.DataFrame(games).to_csv(root / "FAKE_fatigue_lab.csv", index=False)


if __name__ == "__main__":
    create()
