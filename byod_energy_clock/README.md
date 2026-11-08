# Datathon Energy Clock

**When does a hackathon crash?** Your hackathon has a body clock. We measured it.

This Build Your Own Dataset project combines live hourly check-ins with a Fatigue Lab reaction-time and time-sense game. It helps organizers locate low-energy periods, compare feelings with performance, and plan around participant requests. The app has no event findings without the collected data.

## Status

Development uses explicitly labeled FAKE fixtures only. They are not event evidence. Real exports and the existing collector are supplied by the project owner. No official challenge brief was present when implementation began. Actual findings and final rubric verification depend on those inputs.

## Run

Use Python 3.11. From this directory:

On this workstation, a project-local Python 3.11 environment is already available. Use `./run.ps1 -Task demo` for the fake preview, `./run.ps1 -Task app` for real-data mode, `./run.ps1 -Task data` to process real exports, and `./run.ps1 -Task check` to run all checks. No global Python changes are needed. For a fresh checkout:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.pipeline
python -m pytest -q
python -m src.check
python -m streamlit run app.py
```

On systems with GNU Make, the equivalent commands are `make data`, `make test`, `make check`, and `make app`. Windows does not need Make; the Python commands above are equivalent. Run commands from this project folder, not the repository root.

## Fake-data preview

```powershell
python tests/create_fixtures.py
python -m src.pipeline --fake
$env:ENERGY_CLOCK_TEST_MODE = '1'
python -m streamlit run app.py
```

Stop Streamlit and run `Remove-Item Env:ENERGY_CLOCK_TEST_MODE` before viewing real results. The app never falls back to fake data automatically. Fake outputs live only under `tests/fixtures/FAKE_output`, never under `data/`. All pages display a prominent FAKE warning in test mode.

## Add the real collection

- Put the existing game at `collector/index.html`; the pipeline does not modify it.
- Export forms as `data/raw/checkins.csv` and `data/raw/fatigue_lab.csv`.
- Optional device exports: `data/raw/fatigue_lab_device_*.csv`.
- Optional room observations: `data/raw/observations.csv`.
- Optional manual identity corrections: `data/private/aliases.csv`, columns `alias,canonical`.
- Run `python -m src.pipeline`, then `python -m pytest -q` and `python -m src.check`.

The owner confirmed survey consent covers the game. A game without a consent column must link to an explicitly consented survey participant. A present but blank/refused game consent is excluded. `--explicit-game-consent-only` disables the linked-survey route. Supply the actual consent wording for collection documentation.

Raw exports and the ID map are ignored by Git. Only allowlisted, pseudonymized fields enter processed files. Do not add private files with `git add -f`. No names are printed by the pipeline. Counts below three contributing participants are suppressed in group statistics. Downloads contain pseudonymized participant-level data and still warrant careful handling.

## Pages and evidence

Home summarizes coverage and the crash estimate. Energy Clock shows a radial clock, elapsed energy, centered energy, focus and progress. Say vs Perform separates game ratings from nearest-check-in comparisons. What Helps contains descriptive associations, adjusted models and demand. Crash Predictor reports participant-held-out validation and falls back to hourly means when it cannot improve on the baseline. Organizer Playbook ties each timing suggestion to observed evidence. Dataset and Methods provides collection timing, quality counts, methods and downloads.

Both sidebar filters select precomputed analyses. Device filtering selects that device's games and check-ins belonging to its participants. Time windows are named Chicago day phases. Models and summaries are recomputed by the pipeline for each view, not on page load.

## Streamlit Community Cloud

Choose Python 3.11, repository entrypoint `byod_energy_clock/app.py`, and this folder's pinned requirements. Publish only reviewed processed artifacts. Never upload raw/private files or enable `ENERGY_CLOCK_TEST_MODE` for a real-data demo. No deployment has been performed.

## Judging narrative

| Criterion | Evidence in this project |
| --- | --- |
| Data collection | Two participant instruments, collection timeline, raw-to-processed quality counts |
| Functionality and integration | Cross-source identity linking, nearest-session pairing, seven working views |
| Usefulness and impact | Request-based organizer schedule and uncertainty-aware crash window |
| Creativity | Radial Energy Clock and measured-vs-felt awareness gap |
| Communication | Number provenance, participant counts, methods, model card and explicit limitations |

This mapping uses the criteria in the supplied project specification, pending the official brief. Real findings and screenshots should be added after real-data validation, not invented from test fixtures.
