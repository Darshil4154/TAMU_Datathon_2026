#!/usr/bin/env python3
"""
agent_board.py - turn one pinned GitHub issue into a message board for your team's coding agents.

How it works:
  - Polls the issue's comments every N seconds.
  - When a new comment tags YOUR GitHub username (@you), it hands the message to your
    coding agent (Codex, Claude Code or Antigravity CLI) running in your local clone of the repo.
  - The agent edits files. The script then commits and pushes the changes and posts the
    agent's reply back to the issue. The reply can tag teammates (@their-username),
    which wakes up THEIR watcher.
  - Replies carry a hidden marker so your watcher never answers its own posts.

Each teammate runs one copy of this on their own computer, in their own clone, with their own username.
Teammates can use different agents (one on Codex, one on Claude Code, etc.).

Requirements:
  - Git and the GitHub CLI, logged in:  gh auth login  then  gh auth setup-git
  - One agent CLI, logged in once:      codex / claude / agy

Usage:
  python tools/agent_board.py --repo owner/repo --issue 1 --me your-github-username --agent codex
  python tools/agent_board.py --repo owner/repo --issue 1 --me your-github-username --agent claude

Advanced: set the AGENT_CMD environment variable to use any other command (overrides --agent).
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

AGENTS = {
    "codex": ["codex", "exec", "--sandbox", "workspace-write"],
    "claude": ["claude", "-p", "--permission-mode", "acceptEdits"],
    "agy": ["agy", "-p"],
}

PROMPT_TEMPLATE = """You were tagged on the team agent board (GitHub issue #{issue} in {repo}) by @{author}.

Message:
---
{body}
---

Instructions:
- Follow the team rules in AGENTS.md. Only edit files inside the folders you own.
- Do the work that was asked. If it needs a change in someone else's folder, do NOT make it; ask them instead.
- Do NOT run git commit or git push. The board script commits and pushes your changes after you finish.
- Your final output is posted to the board as-is. Keep it short:
    1. What you did (1-3 lines)
    2. Files or endpoints changed
    3. Tag (@username) ONLY the people you are handing work to or need something from, and say exactly what you need.
- Do not tag anyone just to say thanks or acknowledge. If nothing is needed from anyone, tag no one.
"""


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd, **kw):
    # UTF-8 everywhere so emoji and non-English text don't crash on Windows.
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def resolve(cmd):
    """Find the real executable (handles codex.cmd / claude.exe on Windows)."""
    exe = shutil.which(cmd[0])
    if not exe:
        sys.exit(f"Could not find '{cmd[0]}'. Is it installed and on your PATH? Try opening a new terminal.")
    return [exe] + cmd[1:]


def load_state(path, from_start):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    # First run: ignore old history unless asked, so you don't replay old messages.
    return {"since": "1970-01-01T00:00:00Z" if from_start else now_iso(), "seen": []}


def save_state(path, state):
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def fetch_comments(repo, issue, since):
    """Fetch comments created/updated since a timestamp, handling pagination."""
    comments, page = [], 1
    while True:
        r = run(["gh", "api", f"repos/{repo}/issues/{issue}/comments?since={since}&per_page=100&page={page}"])
        if r.returncode != 0:
            print(f"[warn] gh api failed: {r.stderr.strip()}", file=sys.stderr)
            return comments
        batch = json.loads(r.stdout or "[]")
        comments.extend(batch)
        if len(batch) < 100:
            return comments
        page += 1


def post_comment(repo, issue, body):
    r = run(["gh", "issue", "comment", str(issue), "--repo", repo, "--body-file", "-"], input=body)
    if r.returncode != 0:
        print(f"[warn] could not post reply: {r.stderr.strip()}", file=sys.stderr)


def commit_and_push(workdir, me, summary):
    """Commit whatever the agent changed and push it. Returns a short status line for the board."""
    run(["git", "add", "-A"], cwd=workdir)
    if run(["git", "diff", "--cached", "--quiet"], cwd=workdir).returncode == 0:
        return "No file changes to commit."
    msg = f"[{me}'s agent] {summary[:60]}"
    c = run(["git", "commit", "-m", msg], cwd=workdir)
    if c.returncode != 0:
        return f"Commit failed: {(c.stderr or c.stdout).strip()[:300]}"
    p = run(["git", "pull", "--rebase"], cwd=workdir)
    if p.returncode != 0:
        run(["git", "rebase", "--abort"], cwd=workdir)
        return f"Committed locally but pull --rebase hit a conflict; {me} please resolve and push."
    push = run(["git", "push"], cwd=workdir)
    if push.returncode != 0:
        return f"Committed locally but push failed: {push.stderr.strip()[:300]}"
    sha = run(["git", "rev-parse", "--short", "HEAD"], cwd=workdir).stdout.strip()
    return f"Pushed commit `{sha}`."


def main():
    ap = argparse.ArgumentParser(description="Agent message board watcher")
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--issue", required=True, type=int, help="issue number used as the board")
    ap.add_argument("--me", required=True, help="your GitHub username (the tag your agent answers to)")
    ap.add_argument("--agent", choices=sorted(AGENTS), default="codex", help="which agent CLI to use (default: codex)")
    ap.add_argument("--workdir", default=".", help="path to your local clone (default: current folder)")
    ap.add_argument("--interval", type=int, default=20, help="seconds between checks (default 20)")
    ap.add_argument("--timeout", type=int, default=1800, help="max seconds per agent run (default 1800)")
    ap.add_argument("--max-runs-per-hour", type=int, default=30, help="safety cap against agent ping-pong")
    ap.add_argument("--from-start", action="store_true", help="also process mentions already on the board")
    args = ap.parse_args()

    me = args.me.lstrip("@")
    workdir = Path(args.workdir).expanduser().resolve()
    state_path = workdir / f".agent_board_{me}.json"
    state = load_state(state_path, args.from_start)
    seen = set(state["seen"])

    marker = f"<!-- agent:{me} -->"
    mention = re.compile(rf"(?<![\w-])@{re.escape(me)}(?![\w-])", re.IGNORECASE)
    agent_cmd = resolve(shlex.split(os.environ["AGENT_CMD"]) if os.environ.get("AGENT_CMD") else AGENTS[args.agent])
    for tool in ("gh", "git"):
        if not shutil.which(tool):
            sys.exit(f"Could not find '{tool}'. Install it and open a new terminal.")
    recent_runs = []

    print(f"Watching {args.repo}#{args.issue} for @{me} every {args.interval}s")
    print(f"Agent: {' '.join(agent_cmd)}")
    print(f"Folder: {workdir}")
    print("Press Ctrl+C to stop.")

    while True:
        comments = sorted(fetch_comments(args.repo, args.issue, state["since"]), key=lambda c: c["created_at"])

        for c in comments:
            state["since"] = max(state["since"], c["updated_at"])
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            body = c.get("body") or ""

            if marker in body or not mention.search(body):
                continue  # our own post, or not for us

            recent_runs = [t for t in recent_runs if time.time() - t < 3600]
            if len(recent_runs) >= args.max_runs_per_hour:
                print(f"[pause] hit {args.max_runs_per_hour} runs/hour cap; skipping {c['html_url']}")
                continue
            recent_runs.append(time.time())

            author = c["user"]["login"]
            print(f"\n[tagged] by @{author}: {c['html_url']}")
            print("[working] agent is running, this can take a few minutes...")
            prompt = PROMPT_TEMPLATE.format(issue=args.issue, repo=args.repo, author=author, body=body)

            try:
                r = run(agent_cmd + [prompt], cwd=workdir, timeout=args.timeout)
                reply = (r.stdout or "").strip() or f"(agent produced no output)\n\n{(r.stderr or '').strip()[-1500:]}"
            except subprocess.TimeoutExpired:
                reply = f"Timed out after {args.timeout}s while working on this. {me}, please take a look."

            first_line = next((ln.strip() for ln in body.splitlines() if ln.strip()), "update")
            git_status = commit_and_push(workdir, me, mention.sub("", first_line).strip() or "update")

            post_comment(
                args.repo,
                args.issue,
                f"{marker}\n**🤖 {me}'s agent** (re: {c['html_url']})\n\n{reply}\n\n_{git_status}_",
            )
            print(f"[replied] {git_status}")

        state["seen"] = list(seen)
        save_state(state_path, state)
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
