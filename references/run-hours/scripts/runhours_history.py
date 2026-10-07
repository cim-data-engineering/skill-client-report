#!/usr/bin/env python3
"""Load offloaded PEAK responses for the run-hours check.

Not a general history loader — this reads the `platform.history` results that
the platform offloaded to disk for the run-hours check only, keyed on BACnet
favourite ids, plus the discovery pages the plan reads. The other health-check
reports do not use it.

Two hazards it exists to handle, both of which corrupt results silently:

1. The offloaded payload's shape varies by client — an MCP text-block wrapper,
   a bare ``{"results": [...]}`` dict, or a bare list.
2. The tool-results directory is shared across concurrent sessions, so a file
   may carry rows for fav_ids that are not yours, and one chunk's rows may be
   split across several files.

Usage as a library (the normal case)::

    from runhours_history import load_rows, read_results
    rows = load_rows(paths, fav_ids)     # history, filtered to your fav_ids
    rows = read_results(path)            # any saved response, unfiltered

Usage as a CLI, for a sanity check that prints only derived counts::

    python3 runhours_history.py <fav_ids_csv> <file.json> [more.json ...]

Standard library only — no third-party dependencies, by design, so the script
runs wherever the skill is unpacked.
"""
import json
import sys

__all__ = ["load_rows", "read_page", "read_results", "summarise"]


def _unwrap(obj):
    """Reduce any of the known payload shapes to (row dicts, pagination total or None)."""
    total = None
    for _ in range(4):                      # bounded: shapes nest at most twice
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict) and "text" in obj[0]:
                obj = json.loads(obj[0]["text"])     # MCP text-block wrapper
                continue
            return obj, total                         # bare list of rows
        if isinstance(obj, dict):
            if total is None and isinstance(obj.get("pagination"), dict):
                total = obj["pagination"].get("total")
            if "results" in obj:
                obj = obj["results"]                  # bare {"results": [...]}
                continue
            if "text" in obj:
                obj = json.loads(obj["text"])
                continue
        break
    if isinstance(obj, list):
        return obj, total
    raise ValueError(f"unrecognised history payload shape: {type(obj).__name__}")


def read_page(path):
    """Return (rows, total) for one saved response, whatever its wrapper.

    `total` is the response's `pagination.total` where the MCP reported one —
    a `limit: 1` call is a count — and None otherwise. Raises on a file that
    cannot be read or parsed rather than returning nothing: a silently empty
    page would drop equipment or understate run hours, which is worse than
    failing loudly.
    """
    try:
        with open(path) as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError(f"could not read response file {path}: {exc}") from exc
    return _unwrap(payload)


def read_results(path):
    """Return the result rows of one saved response, whatever its wrapper."""
    return read_page(path)[0]


def load_rows(paths, fav_ids):
    """Return de-duplicated history rows for `fav_ids` across `paths`.

    Filters to your own fav_ids and de-dups on (fav_id, ts) across files, so
    passing extra or overlapping files is safe.
    """
    if isinstance(paths, (str, bytes)):
        paths = [paths]
    want = {str(f) for f in fav_ids}
    if not want:
        raise ValueError("fav_ids is empty — refusing to load unfiltered history")

    kept = {}
    for path in paths:
        for row in read_results(path):
            if not isinstance(row, dict):
                continue
            fid = str(row.get("fav_id"))
            if fid not in want:
                continue                              # another session's rows
            kept[(fid, row.get("ts"))] = row
    return list(kept.values())


def summarise(rows):
    """Derived counts only — never returns or prints raw rows."""
    by_fav = {}
    for r in rows:
        by_fav[str(r.get("fav_id"))] = by_fav.get(str(r.get("fav_id")), 0) + 1
    ts = [r.get("ts") for r in rows if r.get("ts")]
    return {
        "rows": len(rows),
        "fav_ids": len(by_fav),
        "rows_per_fav_min": min(by_fav.values()) if by_fav else 0,
        "rows_per_fav_max": max(by_fav.values()) if by_fav else 0,
        "ts_min": min(ts) if ts else None,
        "ts_max": max(ts) if ts else None,
    }


def main(argv):
    if len(argv) < 3:
        sys.exit("usage: python3 runhours_history.py <fav_ids_csv> <file.json> ...")
    fav_ids = [f for f in argv[1].split(",") if f]
    rows = load_rows(argv[2:], fav_ids)
    print(json.dumps(summarise(rows), indent=2))


if __name__ == "__main__":
    main(sys.argv)
