"""Recommendations are computed from visible evidence, never preset conclusions."""


def recommendations(clock: dict, helps: dict) -> list[dict]:
    """Rank request peaks by share; every entry retains its evidence."""
    rows = []
    actions = {"Food": "Arrange food arrival", "Coffee or tea": "Offer optional coffee or tea and water", "Sleep": "Make a quiet rest space available", "A short break": "Invite a short break"}
    for option, action in actions.items():
        eligible = [r for r in helps["demand"] if r["option"] == option and r["share"] is not None]
        if not eligible:
            continue
        peak = max(eligible, key=lambda r: r["share"])
        arrival = f"{(peak['hour'] - 1) % 24:02d}:30"
        rows.append({"title": action, "time": arrival, "evidence": f"{option} requests peak at {peak['hour']:02d}:00: {peak['share']:.0%} of answered check-ins, n={peak['n']} participants ({peak['requesters']} requesters).", "reason": "Schedule 30 minutes before the observed request peak; this is a planning heuristic, not a tested intervention.", "effect_size": peak["share"], "source": "Demand by hour"})
    rows.sort(key=lambda row: row["effect_size"], reverse=True)
    crash = clock["crash"]
    if crash:
        rows.append({"title": "Offer a rest check-in", "time": f"{crash['hour']:02d}:00", "evidence": f"Lowest centered energy: {crash['mean']:+.2f} points relative to personal mean, n={crash['n']} participants; 95% mean CI [{crash['low']:.2f}, {crash['high']:.2f}].", "reason": "This suggests a low-energy window; it does not establish that a break changes performance.", "effect_size": crash["mean"], "source": "Energy Clock"})
    return rows


def markdown(rows: list[dict]) -> str:
    """Create the printable schedule using only computed recommendations."""
    text = "# Energy Clock organizer schedule\n\nChicago local time. Associations, not causes.\n\n"
    if not rows:
        return text + "Insufficient data for recommendations.\n"
    for row in sorted(rows, key=lambda r: r["time"]):
        text += f"## {row['time']} - {row['title']}\n\n{row['evidence']}\n\n{row['reason']}\n\n"
    return text
