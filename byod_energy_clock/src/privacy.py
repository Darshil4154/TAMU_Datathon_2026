"""Private identity linking. Never print identifying input values."""
from pathlib import Path
import re
import secrets
import unicodedata
import pandas as pd


def normalize_name(value: object) -> str:
    """Normalize spacing, case and punctuation without guessing identities."""
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).lower()
    return " ".join(re.sub(r"[^\w\s]|_", "", text).split())


class IdentityMap:
    """Persist random assignment order to stable pseudonyms in private storage."""

    def __init__(self, directory: Path, prefix: str = ""):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"{prefix}id_map.csv"
        self.fake = prefix == "FAKE_"
        self.mapping = {}
        self.aliases = {}
        if self.path.exists():
            self.mapping = dict(pd.read_csv(self.path, keep_default_na=False)[["normalized_name", "participant_id"]].values)
        alias_path = directory / f"{prefix}aliases.csv"
        if alias_path.exists():
            pairs = pd.read_csv(alias_path, keep_default_na=False)
            self.aliases = {normalize_name(a): normalize_name(c) for a, c in pairs.values}

    def canonical(self, value: object) -> str:
        """Resolve chained manual aliases and reject cycles without leaking names."""
        name, seen = normalize_name(value), set()
        while name in self.aliases:
            if name in seen:
                raise ValueError("Alias cycle detected in private aliases file.")
            seen.add(name)
            name = self.aliases[name]
        return name

    def assign(self, values: pd.Series) -> pd.Series:
        """Allocate IDs, assigning each blank response an unlinked one-off ID."""
        names = values.map(self.canonical)
        unknown = sorted(set(names) - set(self.mapping) - {""})
        secrets.SystemRandom().shuffle(unknown)
        for name in unknown:
            self.mapping[name] = f"P{len(self.mapping) + 1:02d}"
        result = names.map(lambda n: self.mapping[n] if n else "U" + secrets.token_hex(8))
        mapping = pd.DataFrame(self.mapping.items(), columns=["normalized_name", "participant_id"])
        if self.fake:
            mapping["is_fake"] = True
        mapping.to_csv(self.path, index=False)
        return result

    def pseudonymize(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Remove the linking field after assignment."""
        out = frame.copy()
        out["participant_id"] = self.assign(out["anon_code"])
        return out.drop(columns=["anon_code"])
