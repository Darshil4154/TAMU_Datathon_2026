# Energy Clock - Test & Run Log

**Run date:** 2026-11-08  **Dataset:** REAL (21 responses, 20 unique participants, TAMU Datathon 2026)

---

## Pipeline results (real data update)

| Metric | Value |
|--------|-------|
| Check-ins in | 21 |
| Check-ins out (all consented, all valid) | 21 |
| Game sessions in | 21 |
| Game sessions excluded (no matching survey consent) | 2 |
| Game sessions out | 19 |
| Unique participants | 20 |
| Paired sessions (survey + game within 45 min) | 11 |
| Hours covered | 11.2 h (spanning 21:52 on Nov 7 to 09:01 on Nov 8) |
| Observed crash hour | 22:00 (n=10) |
| `is_fake` | False |

**Consent policy:** Explicit consent; linked survey consent allowed with confirmed coverage.

**Name aliases resolved:** Two name variant aliases were resolved in private mapping storage.

---

## Model results

| Metric | Value |
|--------|-------|
| Model MAE (LOPO) | 1.022 |
| Baseline MAE | 1.113 |
| Beats baseline? | **Yes!** Leave-One-Participant-Out (LOPO) Cross-Validation confirms the ridge regression outperforms training-fold mean baseline. |
| Status text | "Model beats the baseline." |

---

## Test suite

```
30 passed in 10.30s
```

All 30 unit, integration, and property tests pass cleanly.

---

## Data quality table

| source | reason | count |
|--------|--------|-------|
| checkins | rows_in | 21 |
| checkins | no_consent | 0 |
| games | rows_in | 21 |
| games | no_consent | 2 |
| games | invalid_session_id | 0 |
| games | duplicate_session | 0 |
| checkins | invalid_energy | 0 |
| checkins | invalid_focus | 0 |
| checkins | invalid_slept_h | 0 |
| checkins | invalid_caffeine_today | 0 |
| checkins | missing_time_or_energy | 0 |
| checkins | rows_out | 21 |
| games | invalid_energy | 0 |
| games | invalid_reaction_avg_ms | 0 |
| games | invalid_reaction_best_ms | 0 |
| games | invalid_reaction_slowest_ms | 2 |
| games | invalid_false_starts | 0 |
| games | invalid_time_estimate_s | 1 |
| games | missing_time_or_energy | 0 |
| games | rows_out | 19 |

---

## App health check

| Check | Result |
|-------|--------|
| `streamlit run app.py` | Running on port 8501 |
| HTTP GET http://localhost:8501 | 200 OK |
| `is_fake` guard in UI | Passes (real data loaded, no demo banner) |
| All 7 pages functioning | PASS |
