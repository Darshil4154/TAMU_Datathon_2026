"""Pure participant-aware summaries. Suppressed cells never carry estimates."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from .ingest import HELP

SEED = 2026
RESAMPLES = 2000


def cluster_ci(frame: pd.DataFrame, column: str, seed: int = SEED, resamples: int = RESAMPLES) -> tuple[float | None, float | None]:
    """Percentile CI of a row mean, resampling participant clusters."""
    valid = frame.dropna(subset=[column])
    agg = valid.groupby("participant_id")[column].agg(["sum", "count"])
    if len(agg) < 3:
        return None, None
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(agg), (resamples, len(agg)))
    means = agg["sum"].to_numpy()[indices].sum(axis=1) / agg["count"].to_numpy()[indices].sum(axis=1)
    return tuple(float(v) for v in np.quantile(means, [.025, .975]))


def grouped(frame: pd.DataFrame, by: str, value: str, resamples: int = RESAMPLES) -> list[dict]:
    """Means and participant bootstrap CIs, with contributor-level suppression."""
    result = []
    for key, group in frame.groupby(by, observed=True):
        valid = group.dropna(subset=[value])
        n = valid.participant_id.nunique()
        low, high = cluster_ci(valid, value, resamples=resamples)
        result.append({"group": key.item() if hasattr(key, "item") else key, "n": int(n) if n >= 3 else "n < 3", "rows": len(valid) if n >= 3 else None, "mean": float(valid[value].mean()) if n >= 3 else None, "low": low, "high": high})
    return result


def energy_clock(checks: pd.DataFrame, resamples: int = RESAMPLES) -> dict:
    """Center each participant and bootstrap both hourly means and crash location."""
    checks = checks.copy()
    checks["centered"] = checks.energy - checks.groupby("participant_id").energy.transform("mean")
    raw = grouped(checks, "clock_hour", "energy", resamples)
    centered = grouped(checks, "clock_hour", "centered", resamples)
    eligible = [r for r in centered if r["mean"] is not None]
    if not eligible:
        return {"raw": raw, "centered": centered, "crash": None}
    best = min(eligible, key=lambda r: r["mean"])
    hours = [r["group"] for r in eligible]
    people = sorted(checks.participant_id.unique())
    sums = checks.pivot_table(index="participant_id", columns="clock_hour", values="centered", aggfunc="sum").reindex(index=people, columns=hours).fillna(0).to_numpy()
    counts = checks.pivot_table(index="participant_id", columns="clock_hour", values="centered", aggfunc="count").reindex(index=people, columns=hours).fillna(0).to_numpy()
    indices = np.random.default_rng(SEED).integers(0, len(people), (resamples, len(people)))
    total, denom = sums[indices].sum(axis=1), counts[indices].sum(axis=1)
    means = np.divide(total, denom, out=np.full_like(total, np.inf), where=denom > 0)
    winners = np.array(hours)[means.argmin(axis=1)]
    # Circular offsets prevent midnight from producing a misleading 0-to-23 CI.
    offsets = (winners - best["group"] + 12) % 24 - 12
    low, high = np.quantile(offsets, [.025, .975], method="nearest")
    crash = {**best, "hour": best["group"], "hour_ci": [int((best["group"] + low) % 24), int((best["group"] + high) % 24)], "bootstrap_hour_share": {str(h): float(np.mean(winners == h)) for h in hours}}
    return {"raw": raw, "centered": centered, "crash": crash}


def correlation(frame: pd.DataFrame, x: str, y: str, resamples: int = RESAMPLES) -> dict:
    """Spearman rho with cluster bootstrap; constant samples are uninformative."""
    frame = frame.dropna(subset=[x, y])
    n = frame.participant_id.nunique()
    result = {"metric": y, "n": int(n) if n >= 3 else "n < 3", "rows": len(frame) if n >= 3 else None, "rho": None, "low": None, "high": None}
    if n < 3 or frame[x].nunique() < 2 or frame[y].nunique() < 2:
        return result
    result["rho"] = float(spearmanr(frame[x], frame[y]).statistic)
    values = bootstrap_spearman(frame, x, y, resamples)
    if len(values) >= resamples / 2:
        result["low"], result["high"] = map(float, np.quantile(values, [.025, .975]))
    return result


def bootstrap_spearman(frame: pd.DataFrame, x: str, y: str, resamples: int = RESAMPLES) -> list[float]:
    """Exact cluster bootstrap via multiplicity-weighted tie ranks, in batches.

    This equals physically duplicating all rows of each drawn participant, but
    avoids thousands of scipy calls. It does not bootstrap precomputed ranks.
    """
    people, labels = pd.factorize(frame.participant_id, sort=True)
    n = len(labels)
    codes = [np.unique(frame[col].to_numpy(), return_inverse=True)[1] for col in [x, y]]
    draws = np.random.default_rng(SEED).integers(0, n, (resamples, n))
    values = []
    for start in range(0, resamples, 100):
        batch = draws[start:start + 100]
        multiplicity = np.zeros((len(batch), n))
        np.add.at(multiplicity, (np.arange(len(batch))[:, None], batch), 1)
        weights = multiplicity[:, people]
        total = weights.sum(axis=1, keepdims=True)
        centered = []
        for code in codes:
            ties = np.zeros((len(batch), int(code.max()) + 1))
            for i, row in enumerate(weights):
                ties[i] = np.bincount(code, weights=row, minlength=ties.shape[1])
            ranks = (ties.cumsum(axis=1) - (ties - 1) / 2)[:, code]
            centered.append(ranks - (total + 1) / 2)
        a, b = centered
        numerator = (weights * a * b).sum(axis=1)
        denominator = np.sqrt((weights * a * a).sum(axis=1) * (weights * b * b).sum(axis=1))
        rho = np.divide(numerator, denominator, out=np.full(len(batch), np.nan), where=denominator > 0)
        values.extend(float(value) for value in rho if np.isfinite(value))
    return values


def awareness(games: pd.DataFrame, resamples: int = RESAMPLES) -> dict:
    """Game self-rating and paired survey analyses are explicitly separate."""
    games = games.copy()
    games["abs_time_error"] = games.time_error_s.abs()
    valid = games.dropna(subset=["energy", "reaction_avg_ms"]).copy()
    n = valid.participant_id.nunique()
    gap = {"n": int(n) if n >= 3 else "n < 3", "overconfident": None, "underconfident": None, "over_ci": [None, None], "under_ci": [None, None], "histogram": []}
    if n >= 3 and valid.energy.std(ddof=0) > 0 and valid.reaction_avg_ms.std(ddof=0) > 0:
        values = (valid.energy - valid.energy.mean()) / valid.energy.std(ddof=0) + (valid.reaction_avg_ms - valid.reaction_avg_ms.mean()) / valid.reaction_avg_ms.std(ddof=0)
        gap.update(overconfident=float((values > .5).mean()), underconfident=float((values < -.5).mean()))
        valid["gap"] = values
        valid["over"] = (values > .5).astype(float)
        valid["under"] = (values < -.5).astype(float)
        gap["over_ci"] = cluster_ci(valid, "over", resamples=resamples)
        gap["under_ci"] = cluster_ci(valid, "under", resamples=resamples)
        valid["bin"] = pd.cut(values, [-np.inf, -1.5, -.5, .5, 1.5, np.inf], labels=["< -1.5", "-1.5 to -0.5", "-0.5 to 0.5", "0.5 to 1.5", "> 1.5"])
        for label, group in valid.groupby("bin", observed=False):
            contributors = group.participant_id.nunique()
            gap["histogram"].append({"bin": str(label), "count": len(group) if contributors >= 3 else None, "n": int(contributors) if contributors >= 3 else "n < 3"})
    metrics = ["reaction_avg_ms", "false_starts", "abs_time_error"]
    return {"correlations": [correlation(games, "energy", metric, resamples) for metric in metrics], "paired_correlations": [correlation(games, "checkin_energy", metric, resamples) for metric in metrics], "gap": gap, "reaction_by_energy": grouped(games, "energy", "reaction_avg_ms", resamples), "time_by_energy": grouped(games, "energy", "abs_time_error", resamples)}


def helps(checks: pd.DataFrame, resamples: int = RESAMPLES) -> dict:
    """Associations and request shares, excluding missing answers from denominators."""
    checks = checks.copy()
    checks["caffeine_bucket"] = pd.cut(checks.caffeine_today, [-.01, 0, 2, np.inf], labels=["0", "1-2", "3+"])
    checks["sleep_bucket"] = pd.cut(checks.slept_h, [-.01, 5, 7, np.inf], right=False, labels=["<5", "5-7", "7+"])
    associations = {field: grouped(checks, field, "energy", resamples) for field in ["last_ate", "break_last_hour", "caffeine_bucket", "sleep_bucket"]}
    demand = []
    for hour, group in checks[checks.would_help.ne("")].groupby("clock_hour"):
        n = group.participant_id.nunique()
        for option in HELP:
            selected = group.would_help.map(lambda s: option in s.split(", "))
            # Request-specific small cells are suppressed too.
            selected_n = group.loc[selected, "participant_id"].nunique()
            visible = n >= 3 and selected_n >= 3
            demand.append({"hour": int(hour), "option": option, "share": float(selected.mean()) if visible else None, "n": int(n) if visible else "n < 3", "requesters": int(selected_n) if visible else "n < 3"})
    return {"associations": associations, "demand": demand}
