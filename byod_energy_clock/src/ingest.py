"""Read only allowlisted fields, validating consent before identity handling."""
from pathlib import Path
from collections.abc import Callable
import re
import pandas as pd

CHECK_FIELDS = "consent anon_code energy focus slept_h caffeine_today last_ate break_last_hour progress would_help".split()
GAME_FIELDS = "session_id anon_code energy reaction_avg_ms reaction_best_ms reaction_slowest_ms false_starts time_estimate_s time_error_s device client_time consent".split()
CHOICES = {
    "last_ate": ["Within 1 hour", "1-3 hours ago", "3-6 hours ago", "6+ hours ago"],
    "break_last_hour": ["Yes", "No"],
    "progress": ["Stuck", "Making progress", "Almost done"],
    "device": ["station", "roving"],
}
HELP = ["Food", "Coffee or tea", "Water", "A short break", "A quiet space", "Mentor help", "Sleep", "Nothing"]


def read_fields(path: Path, fields: list[str], backup: bool = False) -> pd.DataFrame:
    """Parse Google Form bracket codes; plain field codes only for backups."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    columns = {}
    for col in raw.columns:
        label = col.strip()
        match = re.match(r"^\[(\w+)\]", label)
        code = match.group(1) if match else label if backup or label == "Timestamp" else None
        if code in fields + ["Timestamp"]:
            if code in columns.values():
                raise ValueError("Duplicate field codes in source CSV.")
            columns[col] = code
    return raw[list(columns)].rename(columns=columns).apply(lambda s: s.str.strip()).reindex(columns=fields + ["Timestamp"], fill_value="")


def timestamp(value: object) -> pd.Timestamp:
    """Convert local Chicago or offset timestamps; reject ambiguous local times."""
    if not value or pd.isna(value):
        return pd.NaT
    try:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("America/Chicago", ambiguous="NaT", nonexistent="NaT")
        return ts.tz_convert("UTC")
    except (ValueError, TypeError):
        return pd.NaT


def numeric(frame: pd.DataFrame, column: str, low: float, high: float, quality: list[dict], source: str) -> None:
    """Replace invalid or out-of-range measurements with missing values."""
    original = frame[column]
    values = pd.to_numeric(original, errors="coerce")
    invalid = original.ne("") & (values.isna() | ~values.between(low, high))
    quality.append({"source": source, "reason": f"invalid_{column}", "count": int(invalid.sum())})
    frame[column] = values.where(values.between(low, high))


def ingest(raw: Path, survey_covers_games: bool = False, prefix: str = "", canonical: Callable | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Load surveys and deduplicated games; game consent requires explicit evidence.

    The supplied game schema has no consent field. Such sessions are accepted
    only with confirmed survey coverage and an explicitly consented survey.
    A present game consent field always takes precedence, including refusals.
    """
    from .privacy import normalize_name
    normalize = canonical or normalize_name
    quality = []
    check_path = raw / f"{prefix}checkins.csv"
    checks = read_fields(check_path, CHECK_FIELDS) if check_path.exists() else pd.DataFrame(columns=CHECK_FIELDS + ["Timestamp"])
    quality.append({"source": "checkins", "reason": "rows_in", "count": len(checks)})
    consented = checks.consent.eq("I agree")
    quality.append({"source": "checkins", "reason": "no_consent", "count": int((~consented).sum())})
    checks = checks[consented].copy()
    consent_names = set(checks.anon_code.map(normalize)) - {""}
    parts = []
    paths = ([raw / f"{prefix}fatigue_lab.csv"] if (raw / f"{prefix}fatigue_lab.csv").exists() else []) + sorted(raw.glob(f"{prefix}fatigue_lab_device_*.csv"))
    for path in paths:
        part = read_fields(path, GAME_FIELDS, backup=path.name != f"{prefix}fatigue_lab.csv")
        # Preserve whether an explicit consent question existed, even when blank.
        headers = pd.read_csv(path, nrows=0).columns
        explicit = any(re.match(r"^\[consent\]", h.strip()) or h.strip() == "consent" for h in headers)
        part["consent_explicit"] = explicit
        part["consent_ok"] = part.consent.eq("I agree") if explicit else part.anon_code.map(normalize).isin(consent_names) & survey_covers_games
        parts.append(part)
    games = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=GAME_FIELDS + ["Timestamp", "consent_ok", "consent_explicit"])
    denied = set(games.loc[(games.consent_explicit == True) & (games.consent_ok != True), "session_id"])
    games.loc[games.session_id.isin(denied), "consent_ok"] = False
    quality.append({"source": "games", "reason": "rows_in", "count": len(games)})
    quality.append({"source": "games", "reason": "no_consent", "count": int((games.consent_ok != True).sum())})
    games = games[games.consent_ok == True].copy()
    valid_id = games.session_id.str.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", na=False)
    quality.append({"source": "games", "reason": "invalid_session_id", "count": int((~valid_id).sum())})
    games = games[valid_id].copy()
    duplicates = games.session_id.duplicated()
    quality.append({"source": "games", "reason": "duplicate_session", "count": int(duplicates.sum())})
    games = games[~duplicates].copy()
    for source, frame in [("checkins", checks), ("games", games)]:
        frame["time"] = frame.Timestamp.map(timestamp)
        if source == "games":
            frame["time"] = frame.client_time.map(timestamp).combine_first(frame.time)
        for column, bounds in {"energy": (1, 5), "focus": (1, 5), "slept_h": (0, 14), "caffeine_today": (0, 15), "reaction_avg_ms": (100, 2000), "reaction_best_ms": (100, 2000), "reaction_slowest_ms": (100, 2000), "false_starts": (0, 10000), "time_estimate_s": (1, 60)}.items():
            if column in frame:
                numeric(frame, column, *bounds, quality, source)
        for col, choices in CHOICES.items():
            if col in frame:
                frame[col] = frame[col].where(frame[col].isin(choices))
        if source == "checkins":
            frame["would_help"] = frame.would_help.map(lambda x: ", ".join(v for v in HELP if v in [s.strip() for s in x.split(",")]))
        else:
            frame["time_error_s"] = frame.time_estimate_s - 10
        invalid = frame.time.isna() | frame.energy.isna()
        quality.append({"source": source, "reason": "missing_time_or_energy", "count": int(invalid.sum())})
        frame.drop(index=frame.index[invalid], inplace=True)
        frame.drop(columns=[c for c in ["Timestamp", "client_time", "consent", "consent_ok", "consent_explicit"] if c in frame], inplace=True)
        quality.append({"source": source, "reason": "rows_out", "count": len(frame)})
    return checks.reset_index(drop=True), games.reset_index(drop=True), quality
