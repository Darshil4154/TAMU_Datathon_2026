"""Run collection processing once; the dashboard reads only saved outputs."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .ingest import ingest
from .privacy import IdentityMap
from .features import add_features, pair_sessions
from .analysis import energy_clock, awareness, helps, grouped, RESAMPLES
from .model import fit_models
from .playbook import recommendations, markdown

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = {"All collected hours": None, "Evening (18-23)": "Evening", "Late night (00-03)": "Late night", "Dawn (04-07)": "Dawn", "Morning (08-12)": "Morning", "Afternoon (13-17)": "Afternoon"}


def safe_count(value: int) -> int | str:
    """Mask low participant counts."""
    return value if value >= 3 else "n < 3"


def bundle(checks: pd.DataFrame, games: pd.DataFrame, resamples: int = RESAMPLES) -> dict:
    """Precompute a consistent filtered view including its own models."""
    clock = energy_clock(checks, resamples)
    help_data = helps(checks, resamples)
    model = fit_models(checks)
    people = set(checks.participant_id) | set(games.participant_id)
    paired = games[games.checkin_energy.notna()]
    all_times = pd.concat([checks.time, games.time])
    n = len(people)
    counts = {"participants": safe_count(n), "checkins": len(checks) if checks.participant_id.nunique() >= 3 else "n < 3", "game_sessions": len(games) if games.participant_id.nunique() >= 3 else "n < 3", "paired_sessions": len(paired) if paired.participant_id.nunique() >= 3 else "n < 3", "hours_covered": round((all_times.max() - all_times.min()).total_seconds() / 3600, 1) if n >= 3 else "n < 3"}
    checks = checks.copy()
    checks["elapsed_hour"] = np.floor(checks.hours_since_start)
    checks["stuck"] = checks.progress.map({"Stuck": 1., "Making progress": 0., "Almost done": 0.})
    timeline = []
    for source, frame in [("Check-ins", checks), ("Fatigue Lab", games)]:
        temp = frame.copy()
        temp["hour"] = temp.time.dt.floor("h")
        for hour, group in temp.groupby("hour"):
            count = group.participant_id.nunique()
            timeline.append({"time": hour.isoformat(), "source": source, "count": len(group) if count >= 3 else None, "n": safe_count(count)})
    # Scatter points retain no IDs; show only energy strata with enough contributors.
    scatter = []
    for energy, group in games.dropna(subset=["reaction_avg_ms"]).groupby("energy"):
        count = group.participant_id.nunique()
        if count >= 3:
            scatter.extend({"energy": float(energy), "reaction_avg_ms": float(row.reaction_avg_ms), "n": int(count)} for row in group.itertuples())
    playbook = recommendations(clock, help_data)
    eligible_hours = set(checks.groupby("elapsed_hour").participant_id.nunique().loc[lambda s: s >= 3].index)
    participant_lines = [{"participant_id": r.participant_id, "hours_since_start": float(r.hours_since_start), "energy": float(r.energy)} for r in checks[checks.elapsed_hour.isin(eligible_hours)].itertuples()]
    return {"counts": counts, "clock": clock, "elapsed": grouped(checks, "elapsed_hour", "energy", resamples), "focus": grouped(checks, "clock_hour", "focus", resamples), "stuck": grouped(checks, "clock_hour", "stuck", resamples), "awareness": awareness(games, resamples), "helps": help_data, "model": model, "playbook": playbook, "schedule": markdown(playbook), "timeline": timeline, "scatter": scatter, "participant_lines": participant_lines}


def clean_json(value: object, fake: bool = False, record: bool = False) -> object:
    """JSON must never contain NaN; synthetic records carry explicit labels."""
    if isinstance(value, dict):
        result = {str(k): clean_json(v, fake) for k, v in value.items()}
        if fake and record:
            result["is_fake"] = True
        return result
    if isinstance(value, (list, tuple)):
        return [clean_json(v, fake, record=True) for v in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    return value


def run(fake: bool = False, survey_covers_games: bool = True, resamples: int = RESAMPLES) -> Path:
    """Separate fake artifacts physically; never write fixture data under data/."""
    prefix = "FAKE_" if fake else ""
    raw = ROOT / "tests/fixtures" if fake else ROOT / "data/raw"
    output = ROOT / "tests/fixtures/FAKE_output" if fake else ROOT / "data/processed"
    private = output / "FAKE_private" if fake else ROOT / "data/private"
    output.mkdir(parents=True, exist_ok=True)
    identities = IdentityMap(private, prefix)
    checks, games, quality = ingest(raw, survey_covers_games, prefix, identities.canonical)
    checks = add_features(identities.pseudonymize(checks))
    games = add_features(identities.pseudonymize(games))
    games = pair_sessions(checks, games)
    views = {}
    for device in ["All devices", "station", "roving"]:
        device_games = games if device == "All devices" else games[games.device.eq(device)]
        device_checks = checks if device == "All devices" else checks[checks.participant_id.isin(device_games.participant_id)]
        for window, phase in WINDOWS.items():
            c = device_checks if phase is None else device_checks[device_checks.night_phase.eq(phase)]
            g = device_games if phase is None else device_games[device_games.night_phase.eq(phase)]
            # Re-pair after filtering so hidden check-ins cannot enter displayed statistics.
            g = pair_sessions(c, g)
            views[f"{device}|{window}"] = bundle(c, g, resamples)
            print(f"Analyzed {device}: {window}", flush=True)
    observations = []
    observation_path = raw / f"{prefix}observations.csv"
    if observation_path.exists():
        from .ingest import timestamp
        frame = pd.read_csv(observation_path)
        for _, row in frame.iterrows():
            time = timestamp(row.get("obs_time", ""))
            counts = {key: pd.to_numeric(row.get(key), errors="coerce") for key in ["people_present", "people_sleeping", "people_on_break", "noise_1to5"]}
            if pd.notna(time) and pd.notna(counts["people_present"]) and counts["people_present"] >= 3:
                observations.append({"time": time.isoformat(), **{k: float(v) if pd.notna(v) and v >= 0 else None for k, v in counts.items()}})
        quality.append({"source": "observations", "reason": "eligible_rows", "count": len(observations)})
    for label, frame in [("checkins", checks), ("fatigue_lab", games), ("quality", pd.DataFrame(quality))]:
        frame = frame.copy()
        if fake:
            frame["is_fake"] = True
        frame.to_csv(output / f"{prefix}{label}.csv", index=False)
    result = {"is_fake": fake, "bootstrap_resamples": resamples, "consent_policy": "Explicit consent; linked survey consent allowed only with confirmed coverage." if survey_covers_games else "Explicit consent required. Game rows without consent excluded.", "views": views, "quality": quality, "observations": observations}
    target = output / f"{prefix}analysis.json"
    target.write_text(json.dumps(clean_json(result, fake), indent=2, allow_nan=False), encoding="utf-8")
    model = views["All devices|All collected hours"]["model"]
    card = "# Energy Clock model card\n\n" + ("FAKE FIXTURES ONLY. Not event findings.\n\n" if fake else "Live collection data only.\n\n")
    card += f"Predicts self-reported energy, not health or ability. Complete-case ridge regression; no imputation. Features: elapsed hours, cyclic clock hour, sleep, caffeine, meal recency, break. Leave-one-participant-out CV, equal participant weighting; training-fold mean baseline.\n\nStatus: {model['status']}\n\nMAE: {model['mae']}; baseline MAE: {model['baseline_mae']}; participants: {model['n']}.\n\nThe displayed prediction band uses the 95th percentile of held-out absolute residuals. It is descriptive and has no guaranteed prospective coverage. Small convenience sample, selection bias, repeated participants, device confounding and temporal drift limit generalization. No causal or medical claims.\n"
    (output / f"{prefix}MODEL_CARD.md").write_text(card, encoding="utf-8")
    if not fake:
        (ROOT / "docs/MODEL_CARD.md").write_text(card, encoding="utf-8")
    # Aggregate diagnostics only. Never echo raw rows or names.
    print(pd.DataFrame(quality).to_string(index=False))
    print("Participants:", len(set(checks.participant_id) | set(games.participant_id)), "Paired sessions:", int(games.checkin_energy.notna().sum()))
    print("FAKE artifacts ready." if fake else "Processed artifacts ready.")
    return target


def main() -> None:
    """Command line entry; fake mode cannot select a production output path."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--explicit-game-consent-only", action="store_true", help="Disable linked survey consent. Survey coverage was confirmed by project owner.")
    args = parser.parse_args()
    run(args.fake, not args.explicit_game_consent_only)


if __name__ == "__main__":
    main()
