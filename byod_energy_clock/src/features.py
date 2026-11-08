"""Time features and nearest, within-participant matching."""
import numpy as np
import pandas as pd

START = pd.Timestamp("2026-11-07 11:00", tz="America/Chicago")


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Use elapsed UTC hours and Chicago wall-clock hours across DST."""
    out = frame.copy()
    out["time"] = pd.to_datetime(out.time, utc=True)
    out["hours_since_start"] = (out.time - START).dt.total_seconds() / 3600
    out["clock_hour"] = out.time.dt.tz_convert("America/Chicago").dt.hour
    out["night_phase"] = out.clock_hour.map(lambda h: "Evening" if h >= 18 else "Late night" if h < 4 else "Dawn" if h < 8 else "Morning" if h <= 12 else "Afternoon")
    out["sin_hour"] = np.sin(2 * np.pi * out.clock_hour / 24)
    out["cos_hour"] = np.cos(2 * np.pi * out.clock_hour / 24)
    return out


def pair_sessions(checks: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Pair games to the nearest check-in within 45 minutes, earlier on ties."""
    paired = games.copy()
    paired["checkin_energy"] = np.nan
    paired["pair_minutes"] = np.nan
    paired["checkin_time"] = pd.NaT
    paired["checkin_time"] = pd.to_datetime(paired.checkin_time, utc=True)
    for index, game in paired.iterrows():
        candidates = checks[checks.participant_id.eq(game.participant_id)].sort_values("time")
        if candidates.empty:
            continue
        distances = (candidates.time - game.time).abs().dt.total_seconds() / 60
        nearest = distances.idxmin()
        if distances.loc[nearest] <= 45:
            paired.loc[index, ["checkin_energy", "pair_minutes", "checkin_time"]] = [candidates.loc[nearest, "energy"], distances.loc[nearest], candidates.loc[nearest, "time"]]
    return paired
