import numpy as np
import pandas as pd
from src.analysis import cluster_ci, grouped, energy_clock, awareness
from src.features import add_features, pair_sessions
from src.ingest import ingest
from src.model import fit_models
from pathlib import Path
from scipy.stats import spearmanr
from src.analysis import bootstrap_spearman, SEED


def sample():
    c, g, _ = ingest(Path(__file__).parent / "fixtures", prefix="FAKE_")
    for frame in [c, g]:
        frame["participant_id"] = frame.anon_code
        frame.drop(columns="anon_code", inplace=True)
    c, g = add_features(c), add_features(g)
    return c, pair_sessions(c, g)


def test_reproducible_cluster_bootstrap_and_suppression():
    checks, _ = sample()
    assert cluster_ci(checks, "energy") == cluster_ci(checks, "energy")
    small = checks[checks.participant_id.isin(checks.participant_id.unique()[:2])]
    assert all(r["mean"] is None and r["n"] == "n < 3" for r in grouped(small, "clock_hour", "energy"))
    assert energy_clock(small)["crash"] is None
    result = energy_clock(checks)
    assert result["crash"]["hour"] in [r["group"] for r in result["centered"]]
    assert len(result["crash"]["hour_ci"]) == 2


def test_cluster_bootstrap_not_row_bootstrap():
    frame = pd.DataFrame({"participant_id": np.repeat(["a", "b", "c"], 100), "value": np.repeat([1., 3., 5.], 100)})
    low, high = cluster_ci(frame, "value")
    assert low == 1 and high == 5


def test_lopo_and_training_baseline():
    checks, _ = sample()
    result = fit_models(checks)
    assert result["mae"] is not None and result["baseline_mae"] is not None
    expected = []
    for person in checks.participant_id.unique():
        heldout = checks.participant_id.eq(person)
        expected.append((checks.loc[heldout, "energy"] - checks.loc[~heldout, "energy"].mean()).abs().mean())
    assert np.isclose(result["baseline_mae"], np.mean(expected))
    assert result["beats_baseline"] == (result["mae"] < result["baseline_mae"])


def test_constant_and_missing_game_measurements():
    _, games = sample()
    games["reaction_avg_ms"] = np.nan
    result = awareness(games, resamples=20)
    assert result["gap"]["overconfident"] is None
    assert result["correlations"][0]["rho"] is None


def test_weighted_bootstrap_matches_explicit_cluster_resampling():
    frame = pd.DataFrame({"participant_id": ["a", "a", "b", "c", "c", "c"], "x": [1, 2, 2, 3, 1, 5], "y": [7, 7, 4, 1, 8, 2]})
    actual = bootstrap_spearman(frame, "x", "y", resamples=30)
    groups = [g[["x", "y"]].to_numpy() for _, g in frame.groupby("participant_id")]
    rng = np.random.default_rng(SEED)
    expected = []
    for _ in range(30):
        sample = np.concatenate([groups[i] for i in rng.integers(0, 3, 3)])
        if len(np.unique(sample[:, 0])) < 2 or len(np.unique(sample[:, 1])) < 2:
            continue
        value = spearmanr(sample[:, 0], sample[:, 1]).statistic
        if np.isfinite(value):
            expected.append(value)
    assert np.allclose(actual, expected)
