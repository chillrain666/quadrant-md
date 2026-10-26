"""Synonym table: makes `#TopN` and `#focus`, or `#reading` and `#books`, the same term.

The table has two layers:

- `synonyms.example.json` -- the defaults that ship with the repository
- `synonyms.json` -- the user's own copy, git-ignored, created the first time the
  table is saved

Loading prefers the user copy and falls back to the example, so a fresh clone still
has working synonyms and edits never collide with an upstream pull. Both locations
can be overridden (`SYNONYMS_FILE`, `SYNONYMS_DEFAULTS`).

    {"groups": [["TopN", "focus"], ["reading", "books"]]}

Rules:
- terms in one group are equivalent, and a group may hold **more than two**
- matching is always **case-insensitive**
- groups are not transitive; if a term appears in several groups, the
  **first group wins**
- missing or broken file -> treated as an empty table: everything degrades to
  "no synonyms", nothing raises
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# The user's writable copy (git-ignored) and the shipped defaults (tracked).
SYNONYMS_FILE = Path(os.environ.get("SYNONYMS_FILE", str(_HERE / "synonyms.json")))
SYNONYMS_DEFAULTS = Path(
    os.environ.get("SYNONYMS_DEFAULTS", str(_HERE / "synonyms.example.json"))
)

_cache_key: tuple[float | None, float | None] | None = None
_cache_groups: list[list[str]] | None = None


def _norm(term: str) -> str:
    """Lowercase and strip a leading `#` (both tags and bare words are accepted)."""
    return term.strip().lstrip("#").strip().lower()


def _read_json(path: Path) -> tuple[dict | None, float | None]:
    """Return (payload, mtime); payload is None when the file is missing or broken."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, mtime
    return (data if isinstance(data, dict) else None), mtime


def active_file() -> tuple[Path, str]:
    """Which file is in effect: the user copy when it parses, else the shipped defaults."""
    payload, _ = _read_json(SYNONYMS_FILE)
    if payload is not None:
        return SYNONYMS_FILE, "user"
    payload, _ = _read_json(SYNONYMS_DEFAULTS)
    if payload is not None:
        return SYNONYMS_DEFAULTS, "defaults"
    return SYNONYMS_FILE, "none"


def load_groups(path: Path | None = None) -> list[list[str]]:
    """Load the synonym groups (cached by mtime, so edits apply on the next request).

    A missing or broken user copy falls back to the shipped defaults; only when both
    are unusable does the table become empty. The **original casing** is preserved for
    display; matching normalises on the fly.
    """
    global _cache_key, _cache_groups

    if path is None:
        target, _source = active_file()
        payload, mtime = _read_json(target)
        other_mtime = None
        if target != SYNONYMS_DEFAULTS:
            _, other_mtime = _read_json(SYNONYMS_DEFAULTS)
        key = (mtime, other_mtime)
    else:
        payload, mtime = _read_json(path)
        key = (mtime, None)

    if _cache_key == key and _cache_groups is not None:
        return _cache_groups
    if payload is None:
        _cache_key, _cache_groups = key, []
        return []

    data = payload

    raw = data.get("groups", []) if isinstance(data, dict) else []
    groups: list[list[str]] = []
    for group in raw:
        if not isinstance(group, list):
            continue
        terms: list[str] = []
        seen: set[str] = set()
        for item in group:
            term = str(item).strip().lstrip("#").strip()
            key = term.lower()
            if not term or key in seen:
                continue
            seen.add(key)
            terms.append(term)
        if len(terms) >= 2:
            groups.append(terms)

    _cache_key, _cache_groups = key, groups
    return groups


def save_groups(groups: list[list[str]], path: Path | None = None) -> list[list[str]]:
    """Write the table back. Input is sanitised first: blanks, `#`, case duplicates
    removed, groups with fewer than two terms dropped."""
    global _cache_key

    cleaned: list[list[str]] = []
    for group in groups:
        terms: list[str] = []
        seen: set[str] = set()
        for item in group:
            term = str(item).strip().lstrip("#").strip()
            key = term.lower()
            if not term or key in seen:
                continue
            seen.add(key)
            terms.append(term)
        if len(terms) >= 2:
            cleaned.append(terms)

    target = path or SYNONYMS_FILE
    payload = {
        "_note": "Synonym groups. Terms in a group are equivalent (case-insensitive, two or more). Used by search, tag filtering and Focus.",
        "groups": cleaned,
    }
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, target)

    _cache_key = None  # invalidate so the next read always hits the file
    _cache_groups = cleaned
    return cleaned


def build_mapping(groups: list[list[str]]) -> dict[str, str]:
    """term -> group representative (the first term of the group, lowercased).

    The first group wins when a term appears in several groups. Terms are
    normalised again here because callers may pass raw groups (e.g. the SYN
    fixtures in the tests).
    """
    mapping: dict[str, str] = {}
    for group in groups:
        terms = [t for t in (_norm(x) for x in group) if t]
        if not terms:
            continue
        key = terms[0]
        for term in terms:
            mapping.setdefault(term, key)
    return mapping


def canonical(term: str, mapping: dict[str, str]) -> str:
    """Resolve a term to its representative; unknown terms come back lowercased."""
    return mapping.get(_norm(term), _norm(term))


def expand(term: str, groups: list[list[str]]) -> set[str]:
    """Expand a search term to its whole group (a term outside every group returns itself)."""
    needle = _norm(term)
    for group in groups:
        terms = {_norm(t) for t in group}
        if needle in terms:
            return terms
    return {needle}
