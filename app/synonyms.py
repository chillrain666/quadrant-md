"""Synonym table: makes `#TopN` and `#focus`, or `#reading` and `#books`, the same term.

The table lives in `synonyms.json` (override the location with `SYNONYMS_FILE`):

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

SYNONYMS_FILE = Path(
    os.environ.get("SYNONYMS_FILE", str(Path(__file__).with_name("synonyms.json")))
)

_cache_mtime: float | None = None
_cache_groups: list[list[str]] | None = None


def _norm(term: str) -> str:
    """Lowercase and strip a leading `#` (both tags and bare words are accepted)."""
    return term.strip().lstrip("#").strip().lower()


def load_groups(path: Path | None = None) -> list[list[str]]:
    """Load the synonym groups (cached by file mtime, so edits apply on the next request).

    The **original casing** written by the user is preserved for display; matching
    normalises on the fly.
    """
    global _cache_mtime, _cache_groups

    path = path or SYNONYMS_FILE
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return []

    if _cache_mtime == mtime and _cache_groups is not None:
        return _cache_groups

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

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

    _cache_mtime, _cache_groups = mtime, groups
    return groups


def save_groups(groups: list[list[str]], path: Path | None = None) -> list[list[str]]:
    """Write the table back. Input is sanitised first: blanks, `#`, case duplicates
    removed, groups with fewer than two terms dropped."""
    global _cache_mtime

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

    _cache_mtime = None  # invalidate so the next read always hits the file
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
