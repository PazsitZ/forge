#!/usr/bin/env python3
"""Count real reads of lesson/memory files from Claude Code session transcripts.

Transcripts live at ~/.claude/projects/<slug>/*.jsonl and are pruned after
`cleanupPeriodDays` (default 30), so this scanner is only ever a 30-day window.
The caller merges its output into a persisted ledger to get history past that.

Stdlib only. Read-only: never writes, never touches git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

READ_TOOLS = {"Read", "NotebookRead"}
WRITE_TOOLS = {"Write"}
EDIT_TOOLS = {"Edit", "MultiEdit", "NotebookEdit"}
INDEX_NAMES = {"lessons.md", "MEMORY.md"}
ARCHIVE_DIR = "archive"
REPORT_DIR = "curate-notes"


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def transcript_dir(project_dir: Path) -> Path:
    """~/.claude/projects/<cwd with / and . replaced by ->."""
    slug = str(project_dir).replace("/", "-").replace(".", "-")
    return Path.home() / ".claude" / "projects" / slug


def strip_frontmatter(raw: bytes) -> bytes:
    """Drop a leading YAML frontmatter block, if any."""
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != b"---":
        return raw
    for i in range(1, len(lines)):
        if lines[i].strip() == b"---":
            return b"".join(lines[i + 1:])
    return raw


def body_sha(path: Path) -> str:
    """sha256 prefix of the file body, frontmatter excluded.

    Frontmatter carries the name/title a rename rewrites, so hashing it would
    defeat the one match this key exists to make.
    """
    try:
        return hashlib.sha256(strip_frontmatter(path.read_bytes())).hexdigest()[:16]
    except OSError:
        return ""


def item_key(kind: str, path: Path) -> str:
    """Ledger key: namespaced by store, so a lesson and a memory that happen to
    share a filename stay distinct entries. Index files keep their extension.
    """
    return f"{kind}:{path.name if kind == 'index' else path.stem}"


def classify(path: Path, roots: dict[str, Path]) -> tuple[str, str, bool] | None:
    """Map an absolute path to (kind, key, archived); None if outside the corpus.

    kind is the *store* - lesson, memory or index - and does not change when a
    file is archived, so an item's counts survive the move into archive/.
    """
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    for kind, root in roots.items():
        if root is None:
            continue
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.suffix != ".md":
            return None
        parents = rel.parts[:-1]
        if REPORT_DIR in parents:
            return None  # this skill's own reports: no rule, no index line
        if resolved.name in INDEX_NAMES:
            return ("index", item_key("index", resolved), False)
        return (kind, item_key(kind, resolved), ARCHIVE_DIR in parents)
    return None


def scan(project_dir: Path, roots: dict[str, Path], since: datetime | None,
         skip_sessions: set[str]) -> dict:
    tdir = transcript_dir(project_dir)
    files = sorted(tdir.glob("*.jsonl")) if tdir.is_dir() else []

    # key -> list of (ts, session_id, action)
    events: dict[str, list[tuple[datetime, str, str]]] = {}
    kinds: dict[str, str] = {}
    oldest: datetime | None = None
    newest: datetime | None = None

    for f in files:
        with f.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                ts = parse_ts(rec.get("timestamp"))
                if ts is None:
                    continue
                oldest = ts if oldest is None or ts < oldest else oldest
                newest = ts if newest is None or ts > newest else newest
                session = rec.get("sessionId") or f.stem
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    if name in READ_TOOLS:
                        action = "read"
                    elif name in WRITE_TOOLS:
                        action = "write"
                    elif name in EDIT_TOOLS:
                        action = "edit"
                    else:
                        continue
                    inp = block.get("input")
                    if not isinstance(inp, dict):
                        continue
                    raw = inp.get("file_path") or inp.get("notebook_path")
                    if not isinstance(raw, str) or not raw:
                        continue
                    hit = classify(Path(raw), roots)
                    if hit is None:
                        continue
                    kind, key, _archived = hit
                    kinds.setdefault(key, kind)
                    events.setdefault(key, []).append((ts, session, action))

    # A session that writes or edits a file gets no read credit for it. Two
    # false positives collapse into this one rule: the authoring session
    # reading back its own new file, and any later maintenance session, which
    # *must* Read before it is allowed to Edit. Conservative by design - a
    # session that genuinely applied a lesson and also touched the file loses
    # the credit, so counts under-report rather than inflate.
    authoring: dict[str, str] = {}
    modifiers: dict[str, set[str]] = {}
    for key, evs in events.items():
        writers = [e for e in evs if e[2] in ("write", "edit")]
        modifiers[key] = {e[1] for e in writers}
        creators = [e for e in evs if e[2] == "write"] or writers
        if creators:
            authoring[key] = min(creators, key=lambda e: e[0])[1]

    counted: dict[str, dict] = {}
    skipped = {"modifying_session": 0, "curate_session": 0, "before_since": 0}

    for key, evs in events.items():
        kind = kinds[key]
        reads = 0
        last: datetime | None = None
        for ts, session, action in evs:
            if action != "read":
                continue
            if session in skip_sessions:
                skipped["curate_session"] += 1
                continue
            if session in modifiers.get(key, ()):
                skipped["modifying_session"] += 1
                continue
            if since is not None and ts <= since:
                skipped["before_since"] += 1
                continue
            reads += 1
            last = ts if last is None or ts > last else last
        counted[key] = {
            "kind": kind,
            "reads": reads,
            "last_read": last.isoformat() if last else None,
            "authoring_session": authoring.get(key),
        }

    scanned_at = datetime.now(timezone.utc)

    # The window this run actually observed, already clipped to `since`. The
    # caller appends it to the ledger's scans[]; coverage sums those windows, so
    # handing back the raw transcript span - which always reaches ~30 days back,
    # `since` or not - would let every run re-credit time an earlier run already
    # counted, and items would clear the eviction floors in a fraction of the
    # real elapsed time.
    window = None
    gap = None
    if oldest is not None:
        start = oldest
        if since is not None:
            if since < oldest:
                # Transcripts pruned between the runs: nobody was watching in
                # between, and coverage must not claim otherwise.
                gap = {"from": since.isoformat(), "to": oldest.isoformat()}
            else:
                start = since
        window = {"start": start.isoformat(), "end": scanned_at.isoformat()}

    return {
        "scanned_at": scanned_at.isoformat(),
        "project_dir": str(project_dir),
        "transcript_dir": str(tdir),
        "transcripts": len(files),
        "window": window,
        "unobserved_gap": gap,
        "window_oldest": oldest.isoformat() if oldest else None,
        "window_newest": newest.isoformat() if newest else None,
        "since": since.isoformat() if since else None,
        "skipped": skipped,
        "items": counted,
    }


def on_disk(roots: dict[str, Path]) -> dict[str, dict]:
    """Live *and* archived corpus files, so the caller can tell an entry that
    was archived apart from one that vanished, and can match a rename by sha.
    """
    out: dict[str, dict] = {}
    for _kind, root in roots.items():
        if root is None or not root.is_dir():
            continue
        paths = sorted(root.glob("*.md")) + sorted((root / ARCHIVE_DIR).rglob("*.md"))
        for path in paths:
            hit = classify(path, roots)
            if hit is None:
                continue
            kind, key, archived = hit
            st = path.stat()
            out[key] = {
                "kind": kind,
                "path": str(path),
                "archived": archived,
                "body_sha": body_sha(path),
                "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).date().isoformat(),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", default=os.getcwd())
    ap.add_argument("--lessons-dir", default=None,
                    help="default <project>/docs/lessons")
    ap.add_argument("--memories-dir", default=None,
                    help="default <project>/docs/memories if present")
    ap.add_argument("--since", default=None,
                    help="ISO timestamp; only count reads strictly after it")
    ap.add_argument("--exclude-session", action="append", default=[],
                    help="session id to ignore (previous curate runs); repeatable")
    args = ap.parse_args()

    project = Path(args.project_dir).resolve()
    lessons = Path(args.lessons_dir).resolve() if args.lessons_dir else project / "docs" / "lessons"

    if not lessons.is_dir():
        print(f"no lessons directory at {lessons}", file=sys.stderr)
        return 2

    # An explicitly named memory store that does not exist is an error, not an
    # empty one: reporting "0 memories" for a mistyped path reads as a curated
    # store rather than a missing one.
    if args.memories_dir:
        memories = Path(args.memories_dir).resolve()
        if not memories.is_dir():
            print(f"no memories directory at {memories}", file=sys.stderr)
            return 2
    else:
        memories = project / "docs" / "memories"
        if not memories.is_dir():
            memories = None

    roots = {"lesson": lessons, "memory": memories}
    result = scan(project, roots, parse_ts(args.since), set(args.exclude_session))
    result["roots"] = {k: (str(v) if v else None) for k, v in roots.items()}
    result["memories_scanned"] = memories is not None
    result["on_disk"] = on_disk(roots)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
