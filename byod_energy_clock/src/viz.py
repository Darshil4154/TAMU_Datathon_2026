"""Plotly views built from privacy-filtered, precomputed estimates."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

SCALE = [[0, "#e65a67"], [.5, "#e8c96b"], [1, "#63d69b"]]


def finish(fig: go.Figure, title: str = "") -> go.Figure:
    """Shared readable, responsive chart styling."""
    fig.update_layout(template="plotly_dark", title=title, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=25, r=25, t=55, b=35), font=dict(family="Arial", size=13), legend=dict(orientation="h", y=-.2))
    return fig


def clock(rows: list[dict], crash: dict | None) -> go.Figure:
    """24-hour radial clock; suppressed and unobserved hours remain gray."""
    lookup = {int(row["group"]): row for row in rows}
    values, colors, details = [], [], []
    for hour in range(24):
        row = lookup.get(hour)
        value = row["mean"] if row else None
        values.append(value if value is not None else .15)
        colors.append(px.colors.sample_colorscale(SCALE, [(value - 1) / 4])[0] if value is not None else "#435066")
        details.append(f"{hour:02d}:00 | energy {value:.2f} | n={row['n']}" if value is not None else f"{hour:02d}:00 | " + ("n < 3" if row else "No observations"))
    fig = go.Figure(go.Barpolar(r=values, theta=np.arange(24) * 15, width=[13] * 24, marker_color=colors, customdata=details, hovertemplate="%{customdata}<extra></extra>", name="Energy"))
    if crash:
        fig.add_trace(go.Scatterpolar(r=[5.3], theta=[crash["hour"] * 15], mode="markers", marker=dict(symbol="diamond", size=12, color="white"), name="Lowest centered energy", hovertemplate=f"Crash hour {crash['hour']:02d}:00<extra></extra>"))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5.5], tickvals=[1, 3, 5]), angularaxis=dict(rotation=90, direction="clockwise", tickvals=np.arange(24) * 15, ticktext=[f"{h:02d}" for h in range(24)])))
    return finish(fig, "A day in energy")


def interval_chart(rows: list[dict], title: str, x_label: str, y_label: str, line: bool = False) -> go.Figure:
    """Visible confidence intervals and n attached to every plotted group."""
    frame = pd.DataFrame(rows)
    fig = go.Figure()
    if frame.empty:
        return finish(fig, title)
    frame = frame[frame["mean"].notna()].copy()
    if frame.empty:
        return finish(fig, title)
    custom = frame[["n", "rows"]].to_numpy()
    if line:
        fig.add_trace(go.Scatter(x=frame.group, y=frame.high, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=frame.group, y=frame.low, fill="tonexty", fillcolor="rgba(99,214,155,.16)", mode="lines", line=dict(width=0), name="95% participant bootstrap CI", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=frame.group, y=frame["mean"], mode="lines+markers", line_color="#63d69b", customdata=custom, name="Mean", hovertemplate="%{x}: %{y:.2f}<br>n=%{customdata[0]} participants; %{customdata[1]} rows<extra></extra>"))
    else:
        fig.add_trace(go.Bar(x=frame.group.astype(str), y=frame["mean"], marker_color="#63d69b", customdata=custom, error_y=dict(type="data", array=frame.high - frame["mean"], arrayminus=frame["mean"] - frame.low), hovertemplate="%{x}: %{y:.2f}<br>n=%{customdata[0]} participants; %{customdata[1]} rows<extra></extra>"))
    fig.update_layout(xaxis_title=x_label, yaxis_title=y_label)
    return finish(fig, title)


def takeaway(rows: list[dict], measure: str) -> str:
    """A factual caption derived only from visible estimates."""
    valid = [r for r in rows if r.get("mean") is not None]
    if not valid:
        return f"Not enough participants to summarize {measure}; groups with n < 3 are suppressed."
    low = min(valid, key=lambda r: r["mean"])
    return f"Lowest observed {measure}: {low['group']} ({low['mean']:.2f}; n={low['n']} participants). This suggests a pattern within this collection window."
