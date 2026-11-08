"""Seven Streamlit pages consuming saved analysis artifacts only."""
from pathlib import Path
import json
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from . import viz
from .features import add_features
from .model import predict

ROOT = Path(__file__).resolve().parents[1]
BADGES = {"Self-reported": "Participant answers, not objective measurements.", "Measured": "Fatigue Lab task measurements; hardware and practice can affect results.", "Derived": "Computed from collected responses using documented formulas.", "Model": "Statistical estimate or prediction; uncertainty and validation apply."}


def badge(kind: str) -> None:
    """Accessible tooltip documenting number provenance."""
    st.markdown(f'<span title="{BADGES[kind]}" style="font-size:12px;color:#a4c9bb;border:1px solid #405c53;border-radius:12px;padding:3px 9px">{kind}</span>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def read_result(path: str, modified: int) -> dict:
    """Cache by mtime so a fresh pipeline run is reflected immediately."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load() -> tuple[dict, dict, Path, str]:
    """Select fixed precomputed windows, avoiding ad hoc model fitting in the UI."""
    fake = os.environ.get("ENERGY_CLOCK_TEST_MODE") == "1"
    folder = ROOT / "tests/fixtures/FAKE_output" if fake else ROOT / "data/processed"
    prefix = "FAKE_" if fake else ""
    path = folder / f"{prefix}analysis.json"
    if fake:
        st.warning("FAKE FIXTURES ONLY - synthetic testing data, not datathon findings.")
    if not path.exists():
        st.info("No data loaded yet - run `make data`")
        st.stop()
    result = read_result(str(path), path.stat().st_mtime_ns)
    if bool(result["is_fake"]) != fake:
        st.error("Data mode mismatch. Rebuild the selected dataset.")
        st.stop()
    st.sidebar.markdown("### Explore the collection")
    device = st.sidebar.selectbox("Device", ["All devices", "station", "roving"])
    windows = [key.split("|", 1)[1] for key in result["views"] if key.startswith("All devices|")]
    window = st.sidebar.selectbox("Time window (Chicago)", windows)
    st.sidebar.caption("Device filters include check-ins from participants who used that device. A participant may have used both devices. Time windows filter both sources before analysis.")
    st.sidebar.caption("Each chart reports contributing participants as n. Groups with n < 3 are suppressed.")
    view = result["views"][f"{device}|{window}"]
    if view["counts"]["participants"] == "n < 3":
        has_rows = any(r["reason"] == "rows_out" and r["count"] > 0 for r in result["quality"])
        st.info("n < 3 - not enough participants in this view." if has_rows else "No data loaded yet - run `make data`")
        st.stop()
    return result, view, folder, prefix


def chart(fig: go.Figure, caption: str, kind: str = "Derived") -> None:
    """Render provenance together with every chart and takeaway."""
    badge(kind)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(caption)


def metrics(counts: dict) -> None:
    """Collection coverage cards."""
    cols = st.columns(4)
    for col, (key, label) in zip(cols, [("participants", "Participants"), ("checkins", "Check-ins"), ("game_sessions", "Game sessions"), ("hours_covered", "Hours covered")]):
        with col:
            badge("Derived")
            st.metric(label, counts[key])


def home(view: dict) -> None:
    """Coverage, crash summary and honest evidence statement."""
    st.markdown("### Your hackathon has a body clock. We measured it.")
    st.write("Every check-in tells us how hackers feel. Every Fatigue Lab session measures how they perform. Explore when energy dips, where perception diverges, and what organizers can learn.")
    metrics(view["counts"])
    crash = view["clock"]["crash"]
    badge("Derived")
    if crash:
        st.metric("Observed crash hour (Chicago)", f"{crash['hour']:02d}:00", f"95% bootstrap hour interval {crash['hour_ci'][0]:02d}:00 to {crash['hour_ci'][1]:02d}:00", delta_color="off")
        st.write(f"Energy was lowest relative to participants' own averages around {crash['hour']:02d}:00 (n={crash['n']}). The collection contains {view['counts']['checkins']} check-ins and {view['counts']['game_sessions']} game sessions, with {view['counts']['paired_sessions']} paired sessions. These observations suggest patterns in this sample, not causal effects or a universal hackathon schedule.")
    else:
        st.info("No eligible crash-hour estimate: n < 3 per hour.")
    chart(viz.clock(view["clock"]["raw"], crash), viz.takeaway(view["clock"]["raw"], "raw energy"))


def energy_page(view: dict) -> None:
    """Signature radial clock and time-series evidence."""
    left, right = st.columns([1, 1])
    with left:
        chart(viz.clock(view["clock"]["raw"], view["clock"]["crash"]), viz.takeaway(view["clock"]["raw"], "energy"))
    with right:
        chart(viz.interval_chart(view["elapsed"], "Energy through the event", "Hours since hacking began", "Mean energy (1-5)", True), viz.takeaway(view["elapsed"], "energy"))
    chart(viz.interval_chart(view["clock"]["centered"], "Energy relative to personal baseline", "Chicago clock hour", "Centered energy", True), viz.takeaway(view["clock"]["centered"], "centered energy"))
    if st.checkbox("Show pseudonymous participant trajectories"):
        lines = pd.DataFrame(view.get("participant_lines", []))
        if not lines.empty:
            lines = lines.sort_values(["participant_id", "hours_since_start"])
            chart(viz.finish(px.line(lines, x="hours_since_start", y="energy", color="participant_id", markers=True), "Individual check-in trajectories"), f"Pseudonymous self-reports, n={lines.participant_id.nunique()} participants; only hours with at least three participants are included.", "Self-reported")
    st.caption("The diamond marks the minimum centered mean, which can differ from the minimum raw mean. Bootstrap resamples participants; hour uncertainty uses circular offsets around the observed minimum.")
    for key, title, label in [("focus", "Focus across the night", "Mean focus (1-5)"), ("stuck", "Where progress stalls", "Share reporting Stuck")]:
        chart(viz.interval_chart(view[key], title, "Chicago clock hour", label, True), viz.takeaway(view[key], label))


def awareness_page(view: dict) -> None:
    """Measured performance compared with game ratings and linked survey ratings."""
    data = view["awareness"]
    st.write("Game self-ratings and linked survey ratings are analyzed separately. Higher reaction time means slower performance.")
    badge("Derived")
    st.metric("Sessions paired to a check-in within 45 minutes", view["counts"]["paired_sessions"])
    scatter = pd.DataFrame(view["scatter"])
    if not scatter.empty:
        badge("Self-reported")
        scatter["jittered_energy"] = scatter.energy + np.random.default_rng(2026).uniform(-.10, .10, len(scatter))
        fig = px.scatter(scatter, x="jittered_energy", y="reaction_avg_ms", hover_data=["energy", "n"], color="energy", color_continuous_scale=viz.SCALE, range_color=[1, 5], labels={"jittered_energy": "Game energy (jittered for readability)", "reaction_avg_ms": "Reaction time (ms)"})
        trend = [r for r in data["reaction_by_energy"] if r["mean"] is not None]
        fig.add_trace(go.Scatter(x=[r["group"] for r in trend], y=[r["mean"] for r in trend], mode="lines", line_color="white", name="Mean trend"))
        chart(viz.finish(fig, "Feeling vs reaction"), viz.takeaway(data["reaction_by_energy"], "reaction time (ms)"), "Measured")
    for title, correlations in [("Game self-rating correlations", data["correlations"]), ("Nearest survey check-in correlations", data["paired_correlations"])]:
        st.markdown(f"### {title}")
        badge("Derived")
        st.dataframe(pd.DataFrame(correlations).drop(columns=["is_fake"], errors="ignore"), hide_index=True, use_container_width=True)
    chart(viz.interval_chart(data["time_by_energy"], "Time-sense error", "Game energy", "Mean absolute error (seconds)"), viz.takeaway(data["time_by_energy"], "absolute time error"))
    gap = data["gap"]
    badge("Derived")
    if gap["overconfident"] is not None:
        st.info(f"{gap['overconfident']:.0%} of sessions felt better than they performed (gap > 0.5); {gap['underconfident']:.0%} felt worse (gap < -0.5). n={gap['n']} participants.")
        if gap.get("over_ci", [None])[0] is not None:
            st.caption(f"95% participant bootstrap CIs with standardization held fixed: overconfident {gap['over_ci'][0]:.0%} to {gap['over_ci'][1]:.0%}; underconfident {gap['under_ci'][0]:.0%} to {gap['under_ci'][1]:.0%}.")
        hist = pd.DataFrame(gap["histogram"])
        chart(viz.finish(px.bar(hist, x="bin", y="count", hover_data=["n"]), "Self-awareness gap"), f"Positive values mean feeling exceeds relative reaction performance; n={gap['n']}. Bins with n < 3 are hidden.")
    else:
        st.info("Awareness gap unavailable: insufficient participants or no variation.")
    st.caption("Gap = z(game energy) + z(reaction time), computed over sessions with both measurements. This is a relative score, not a diagnosis.")


def demand_chart(view: dict) -> None:
    """Demand percentages with denominator and suppression visible on hover."""
    data = pd.DataFrame(view["helps"]["demand"])
    if data.empty:
        st.info("No eligible demand responses in this view.")
        return
    values = data.pivot(index="option", columns="hour", values="share")
    counts = data.pivot(index="option", columns="hour", values="n").reindex(index=values.index, columns=values.columns)
    fig = go.Figure(go.Heatmap(z=values.to_numpy(dtype=float), x=values.columns, y=values.index, customdata=counts.to_numpy(), zmin=0, zmax=1, colorscale="Greens", hovertemplate="%{y}, %{x}:00<br>Share %{z:.0%}; n=%{customdata}<extra></extra>"))
    valid = data[data.share.notna()]
    caption = "No request cells have enough participants; n < 3."
    if not valid.empty:
        peak = valid.loc[valid.share.idxmax()]
        caption = f"Largest observed request share: {peak['option']} at {int(peak.hour):02d}:00 ({peak.share:.0%}; n={peak['n']}). Blank cells are suppressed."
    chart(viz.finish(fig, "What people asked for"), caption)


def helps_page(view: dict) -> None:
    """Descriptive associations, model coefficients and demand."""
    st.info("Associations, not causes. Sleep, caffeine, meals and breaks were not randomly assigned.")
    for field, rows in view["helps"]["associations"].items():
        title = field.replace("_", " ").title()
        chart(viz.interval_chart(rows, f"Energy by {title}", title, "Mean energy (1-5)"), viz.takeaway(rows, "energy"))
    model = view["model"]
    st.write(model["association_status"])
    coefficients = pd.DataFrame(model["coefficients"])
    if not coefficients.empty:
        fig = go.Figure(go.Scatter(x=coefficients.estimate, y=coefficients.term, mode="markers", error_x=dict(type="data", array=coefficients.high - coefficients.estimate, arrayminus=coefficients.estimate - coefficients.low), marker_color="#63d69b"))
        fig.add_vline(x=0, line_dash="dot")
        chart(viz.finish(fig, "Adjusted associations with energy"), f"Coefficient intervals express model uncertainty; n={model['n']} complete-case participants. Meal reference: Within 1 hour; break reference: No.", "Model")
    demand_chart(view)


def predictor_page(view: dict, folder: Path, prefix: str) -> None:
    """Saved ridge model or honest observed-hour fallback."""
    model = view["model"]
    badge("Model")
    st.write(model["status"])
    st.caption(f"LOPO evaluation: n={model['n']} participants; {model['rows']} complete-case check-ins.")
    a, b = st.columns(2)
    a.metric("Participant-weighted model MAE", f"{model['mae']:.3f}" if model["mae"] is not None else "Unavailable")
    b.metric("Training-fold mean baseline MAE", f"{model['baseline_mae']:.3f}" if model["baseline_mae"] is not None else "Unavailable")
    badge("Self-reported")
    day = st.selectbox("Event day", ["2026-11-07", "2026-11-08"])
    hour = st.slider("Chicago clock hour", 0, 23, 3)
    sleep = st.slider("Hours slept", 0., 14., 6., .5)
    caffeine = st.slider("Caffeinated drinks", 0, 15, 1)
    meal = st.selectbox("Last meal", ["Within 1 hour", "1-3 hours ago", "3-6 hours ago", "6+ hours ago"])
    took_break = st.selectbox("Break in the last hour", ["Yes", "No"])
    time = pd.Timestamp(f"{day} {hour:02d}:00", tz="America/Chicago")
    row = add_features(pd.DataFrame({"time": [time], "slept_h": [sleep], "caffeine_today": [caffeine], "last_ate": [meal], "break_last_hour": [took_break]}))
    saved = model["predictor"]
    in_range = saved and saved["elapsed_range"][0] <= row.hours_since_start.iloc[0] <= saved["elapsed_range"][1]
    forecast = predict(model, row) if in_range else None
    if forecast:
        badge("Model")
        point, low, high = forecast
        st.metric("Predicted energy", f"{point:.2f} / 5")
        st.caption(f"Empirical held-out error band: {low:.2f} to {high:.2f}. Based on the 95th percentile of held-out absolute errors, not a guaranteed prediction interval. n={model['n']}.")
    else:
        badge("Derived")
        observed = next((r for r in view["clock"]["raw"] if r["group"] == hour and r["mean"] is not None), None)
        if observed:
            st.metric("Observed hourly mean (fallback)", f"{observed['mean']:.2f} / 5")
            st.caption(f"95% participant bootstrap CI {observed['low']:.2f} to {observed['high']:.2f}; n={observed['n']}. Other inputs do not change this observed mean.")
        else:
            st.info("No eligible observed mean for this hour. Predictions outside the observed event window are not shown.")
    card = folder / f"{prefix}MODEL_CARD.md"
    if card.exists():
        st.download_button("Download model card", card.read_text(encoding="utf-8"), file_name=f"{prefix}MODEL_CARD.md")


def playbook_page(view: dict) -> None:
    """Evidence-backed recommendations and printable schedule."""
    st.write("A planning aid for the next event. Timing rules use the selected collection window; they do not establish that an intervention works.")
    for row in view["playbook"]:
        badge("Derived")
        st.markdown(f"### {row['time']} - {row['title']}")
        st.write(row["evidence"])
        st.caption(row["reason"] + " Evidence chart: " + row["source"] + ".")
    if not view["playbook"]:
        st.info("Not enough eligible data for recommendations.")
    st.download_button("Download one-page organizer schedule", view["schedule"], file_name="organizer_schedule.md")
    demand_chart(view)
    chart(viz.interval_chart(view["clock"]["centered"], "Evidence for the rest window", "Chicago clock hour", "Centered energy", True), viz.takeaway(view["clock"]["centered"], "centered energy"))


def methods_page(result: dict, view: dict, folder: Path, prefix: str) -> None:
    """Collection provenance, quality and pseudonymized downloads."""
    st.write("Participants are invited to complete a short check-in about once an hour and a Fatigue Lab reaction/time-sense task. Names are used privately for linking, then replaced with stable random-assignment participant IDs. Blank names receive unlinked one-off IDs.")
    st.write("Consent: the exported survey agreement is 'I agree'. The project owner confirmed that survey consent covers both instruments. The exact consent text and collector implementation have not yet been supplied; see collector/FORMS.md.")
    st.caption(result["consent_policy"])
    metrics(view["counts"])
    timeline = pd.DataFrame(view["timeline"])
    if not timeline.empty:
        chart(viz.finish(px.bar(timeline, x="time", y="count", color="source", barmode="group", hover_data=["n"]), "Collection timeline"), f"Submissions are grouped into UTC hours, with n in hover. Coverage: {view['counts']['hours_covered']} hours. Suppressed hours do not imply no collection.")
    badge("Derived")
    st.markdown("### Data quality (whole collection)")
    st.dataframe(pd.DataFrame(result["quality"]).drop(columns=["is_fake"], errors="ignore"), hide_index=True, use_container_width=True)
    st.caption("Quality counts describe records and validation events, not participant health or behavior; invalid-field counts may overlap.")
    if result["observations"]:
        badge("Measured")
        st.markdown("### Room observations (whole collection)")
        st.dataframe(pd.DataFrame(result["observations"]).drop(columns=["is_fake"], errors="ignore"), hide_index=True)
    for name in ["DATA_DICTIONARY", "METHODS", "LIMITATIONS"]:
        path = ROOT / "docs" / f"{name}.md"
        if path.exists():
            with st.expander(name.replace("_", " ").title()):
                st.markdown(path.read_text(encoding="utf-8"))
    st.markdown("### Download pseudonymized collection")
    st.caption("Downloads contain the whole collection, not only the current filter. Pseudonymization is not a guarantee against re-identification.")
    for name in ["checkins", "fatigue_lab"]:
        path = folder / f"{prefix}{name}.csv"
        if path.exists():
            st.download_button(f"Download {name.replace('_', ' ')}", path.read_bytes(), file_name=path.name, mime="text/csv")


def render(page: str) -> None:
    """Common page setup and explicit routing, including empty-data state."""
    st.set_page_config(page_title=f"{page} | Energy Clock", page_icon="◷", layout="wide")
    st.markdown("<style>.block-container{max-width:1200px;padding-top:2rem}h1{letter-spacing:-.04em}div[data-testid=stMetric]{background:#162235;padding:16px;border-radius:12px}</style>", unsafe_allow_html=True)
    st.caption("DATATHON ENERGY CLOCK / BUILD YOUR OWN DATASET")
    st.title("When does a hackathon crash?" if page == "Home" else page)
    result, view, folder, prefix = load()
    if page == "Home":
        home(view)
    elif page == "The Energy Clock":
        energy_page(view)
    elif page == "Say vs Perform":
        awareness_page(view)
    elif page == "What Helps":
        helps_page(view)
    elif page == "Crash Predictor":
        predictor_page(view, folder, prefix)
    elif page == "Organizer Playbook":
        playbook_page(view)
    elif page == "Dataset and Methods":
        methods_page(result, view, folder, prefix)
