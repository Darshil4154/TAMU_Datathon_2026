"""Check tracked and proposed files without printing private identifiers."""
from pathlib import Path
import re
import subprocess
import sys
import pandas as pd
from .privacy import normalize_name

ROOT = Path(__file__).resolve().parents[1]


def forbidden_name(text: str, names: list[str]) -> bool:
    """Match normalized names with word boundaries, including punctuation variants."""
    normalized = normalize_name(text)
    return any(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", normalized) for name in names if name)


def main() -> None:
    """Fail closed if Git inventory fails; scope formatting checks to this project."""
    repo = ROOT.parent
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True, check=True).stdout.decode().split("\0")
    proposed = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "-z", "--", ROOT.name], cwd=repo, capture_output=True, check=True).stdout.decode().split("\0")
    paths = [repo / p for p in set(tracked + proposed) if p]
    names = []
    mapping = ROOT / "data/private/id_map.csv"
    if mapping.exists():
        names = pd.read_csv(mapping, keep_default_na=False).normalized_name.map(normalize_name).tolist()
    aliases = ROOT / "data/private/aliases.csv"
    if aliases.exists():
        names += [normalize_name(v) for v in pd.read_csv(aliases, keep_default_na=False).values.ravel()]
    problems = []
    for path in paths:
        if not path.is_file():
            continue
        if ROOT / "data/raw" in path.parents or ROOT / "data/private" in path.parents:
            problems.append("Private input is included in Git inventory.")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if forbidden_name(content, names):
            problems.append("Private identifier detected in a tracked or proposed file. Inspect locally; identifiers and paths withheld.")
        if ROOT in path.parents and any(char in content for char in [chr(0x2013), chr(0x2014)]):
            problems.append("Forbidden dash character in " + str(path.relative_to(ROOT)))
    if problems:
        print("\n".join(sorted(set(problems))))
        sys.exit(1)
    print("Privacy and ASCII-dash checks passed.")


if __name__ == "__main__":
    main()
