"""Render every page in fake and empty modes, then exercise sidebar inputs."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "app.py", *sorted((ROOT / "pages").glob("*.py"))]


@pytest.fixture(scope="module")
def fake_artifacts():
    from src.pipeline import run
    path = ROOT / "tests/fixtures/FAKE_output/FAKE_analysis.json"
    inputs = list((ROOT / "src").glob("*.py")) + list((ROOT / "tests/fixtures").glob("FAKE_*.csv"))
    if not path.exists() or max(p.stat().st_mtime_ns for p in inputs) > path.stat().st_mtime_ns:
        before = {p.name: p.read_bytes() for p in (ROOT / "data/processed").glob("*") if p.is_file()}
        run(fake=True)
        after = {p.name: p.read_bytes() for p in (ROOT / "data/processed").glob("*") if p.is_file()}
        assert before == after, "Fake processing must not change production data."
    return path


@pytest.mark.parametrize("page", PAGES, ids=lambda path: path.stem)
def test_every_page_fake(page, fake_artifacts, monkeypatch):
    monkeypatch.setenv("ENERGY_CLOCK_TEST_MODE", "1")
    app = AppTest.from_file(str(page), default_timeout=30).run()
    assert not app.exception
    assert any("FAKE" in item.value for item in app.warning)
    app.sidebar.selectbox[0].set_value("station").run()
    assert not app.exception
    app.sidebar.selectbox[1].set_value("Late night (00-03)").run()
    assert not app.exception


@pytest.mark.parametrize("page", PAGES, ids=lambda path: path.stem)
def test_every_page_empty(page, tmp_path, monkeypatch):
    import src.ui
    monkeypatch.delenv("ENERGY_CLOCK_TEST_MODE", raising=False)
    monkeypatch.setattr(src.ui, "ROOT", tmp_path)
    app = AppTest.from_file(str(page), default_timeout=30).run()
    assert not app.exception
    assert any("No data loaded yet" in item.value for item in app.info)


def test_predictor_inputs(fake_artifacts, monkeypatch):
    monkeypatch.setenv("ENERGY_CLOCK_TEST_MODE", "1")
    app = AppTest.from_file(str(ROOT / "pages/4_Crash_Predictor.py"), default_timeout=30).run()
    app.slider[0].set_value(21).run()
    app.slider[1].set_value(4.5).run()
    assert not app.exception


def test_participant_trajectories(fake_artifacts, monkeypatch):
    monkeypatch.setenv("ENERGY_CLOCK_TEST_MODE", "1")
    app = AppTest.from_file(str(ROOT / "pages/1_Energy_Clock.py"), default_timeout=30).run()
    app.checkbox[0].check().run()
    assert not app.exception
