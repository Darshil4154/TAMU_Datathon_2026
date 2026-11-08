from pathlib import Path
import shutil
import pandas as pd
from src.ingest import ingest, read_fields, CHECK_FIELDS, timestamp
from src.privacy import normalize_name, IdentityMap
from src.features import add_features, pair_sessions

FIXTURES = Path(__file__).parent / "fixtures"


def raw_files(tmp_path):
    for kind in ["checkins", "fatigue_lab"]:
        shutil.copy(FIXTURES / f"FAKE_{kind}.csv", tmp_path / f"{kind}.csv")
    return tmp_path


def test_headers_consent_and_unknown_fields(tmp_path):
    raw_files(tmp_path)
    path = tmp_path / "checkins.csv"
    frame = pd.read_csv(path)
    frame.loc[0, "[consent] Consent"] = "No"
    frame["[secret] Unknown"] = "must disappear"
    frame[frame.columns[::-1]].to_csv(path, index=False)
    checks, games, quality = ingest(tmp_path)
    assert len(checks) == 71 and len(games) == 72
    assert "secret" not in checks and "is_fake" not in checks
    assert any(q["reason"] == "no_consent" and q["count"] == 1 for q in quality)


def test_dedup_bounds_and_consent(tmp_path):
    raw_files(tmp_path)
    path = tmp_path / "fatigue_lab.csv"
    frame = pd.read_csv(path)
    frame.loc[0, "[reaction_avg_ms] Average"] = 99
    frame.loc[0, "[time_estimate_s] Estimate"] = 100
    pd.concat([frame, frame.iloc[[0]]]).to_csv(path, index=False)
    _, games, _ = ingest(tmp_path)
    assert len(games) == 72
    assert pd.isna(games.iloc[0].reaction_avg_ms)
    assert pd.isna(games.iloc[0].time_error_s)
    frame.drop(columns=["[consent] Consent"]).to_csv(path, index=False)
    assert ingest(tmp_path)[1].empty
    assert len(ingest(tmp_path, survey_covers_games=True)[1]) == 72


def test_private_ids_and_aliases(tmp_path):
    assert normalize_name("  FAKE.  Person! ") == "fake person"
    pd.DataFrame([["fake jon", "fake john"]], columns=["alias", "canonical"]).to_csv(tmp_path / "aliases.csv", index=False)
    identities = IdentityMap(tmp_path)
    result = identities.assign(pd.Series(["FAKE JON", "fake john", "", ""]))
    assert result[0] == result[1] and result[2] != result[3]
    assert IdentityMap(tmp_path).assign(pd.Series(["fake john"]))[0] == result[0]


def test_timezone_and_pairing():
    assert timestamp("11/7/2026 22:15:03") == timestamp("2026-11-07T22:15:03-06:00")
    assert pd.isna(timestamp("11/1/2026 01:30:00"))
    checks = add_features(pd.DataFrame({"participant_id": ["P01"], "time": [timestamp("2026-11-07T11:00:00-06:00")], "energy": [3]}))
    assert checks.hours_since_start.iloc[0] == 0 and checks.clock_hour.iloc[0] == 11
    games = pd.DataFrame({"participant_id": ["P01", "P01", "P02"], "time": [checks.time[0] + pd.Timedelta(minutes=m) for m in [45, 46, 0]]})
    paired = pair_sessions(checks, games)
    assert paired.checkin_energy.notna().tolist() == [True, False, False]


def test_empty_input(tmp_path):
    checks, games, quality = ingest(tmp_path)
    assert checks.empty and games.empty and quality


def test_backup_cannot_override_refusal_and_alias_consent(tmp_path):
    from src.ingest import GAME_FIELDS
    raw_files(tmp_path)
    path = tmp_path / "fatigue_lab.csv"
    original = pd.read_csv(path)
    backup = read_fields(path, GAME_FIELDS).drop(columns=["consent", "Timestamp"])
    backup.to_csv(tmp_path / "fatigue_lab_device_FAKE.csv", index=False)
    original.loc[0, "[consent] Consent"] = "No"
    original.to_csv(path, index=False)
    _, games, _ = ingest(tmp_path, survey_covers_games=True)
    assert len(games) == 71
    assert original.loc[0, "[session_id] Session"] not in set(games.session_id)
    original = original.drop(columns="[consent] Consent")
    original.loc[0, "[anon_code] Name"] = "FAKE Typo"
    original.to_csv(path, index=False)
    private = tmp_path / "private"
    private.mkdir()
    pd.DataFrame([["FAKE Typo", "FAKE Person 0"]], columns=["alias", "canonical"]).to_csv(private / "aliases.csv", index=False)
    _, games, _ = ingest(tmp_path, survey_covers_games=True, canonical=IdentityMap(private).canonical)
    assert len(games) == 72


def test_normalization_strips_underscores():
    assert normalize_name("FAKE_Person") == "fakeperson"
