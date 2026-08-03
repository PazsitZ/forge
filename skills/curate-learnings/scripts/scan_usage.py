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


def body_sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def classify(path: Path, roots: dict[str, Path]) -> tuple[str, str] | None:
    """Map an absolute path to (kind, slug); None if outside the corpus.

    kind is one of: lesson, memory, index, archived.
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
        if resolved.name in INDEX_NAMES:
            return ("index", resolved.name)
        if "archive" in rel.parts[:-1]:
            return ("archived", resolved.stem)
        return (kind, resolved.stem)
    return None


def scan(project_dir: Path, roots: dict[str, Path], since: datetime | None,
         skip_sessions: set[str]) -> dict:
    tdir = transcript_dir(project_dir)
    files = sorted(tdir.glob("*.jsonl")) if tdir.is_dir() else []

    # slug -> list of (ts, session_id, action)
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
                    kind, slug = hit
                    kinds.setdefault(slug, kind)
                    events.setdefault(slug, []).append((ts, session, action))

    # A session that writes or edits a file gets no read credit for it. Two
    # false positives collapse into this one rule: the authoring session
    # reading back its own new file, and any later maintenance session, which
    # *must* Read before it is allowed to Edit. Conservative by design - a
    # session that genuinely applied a lesson and also touched the file loses
    # the credit, so counts under-report rather than inflate.
    authoring: dict[str, str] = {}
    modifiers: dict[str, set[str]] = {}
    for slug, evs in events.items():
        writers = [e for e in evs if e[2] in ("write", "edit")]
        modifiers[slug] = {e[1] for e in writers}
        creators = [e for e in evs if e[2] == "write"] or writers
        if creators:
            authoring[slug] = min(creators, key=lambda e: e[0])[1]

    counted: dict[str, dict] = {}
    skipped = {"modifying_session": 0, "curate_session": 0, "before_since": 0}

    for slug, evs in events.items():
        kind = kinds[slug]
        reads = 0
        last: datetime | None = None
        for ts, session, action in evs:
            if action != "read":
                continue
            if session in skip_sessions:
                skipped["curate_session"] += 1
                continue
            if session in modifiers.get(slug, ()):
                skipped["modifying_session"] += 1
                continue
            if since is not None and ts <= since:
                skipped["before_since"] += 1
                continue
            reads += 1
            last = ts if last is None or ts > last else last
        counted[slug] = {
            "kind": kind,
            "reads": reads,
            "last_read": last.isoformat() if last else None,
            "authoring_session": authoring.get(slug),
        }

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "project_dir": str(project_dir),
        "transcript_dir": str(tdir),
        "transcripts": len(files),
        "window_oldest": oldest.isoformat() if oldest else None,
        "window_newest": newest.isoformat() if newest else None,
        "since": since.isoformat() if since else None,
        "skipped": skipped,
        "items": counted,
    }


def on_disk(roots: dict[str, Path]) -> dict[str, dict]:
    """Live corpus files, so the caller can spot ledger entries with no file."""
    out: dict[str, dict] = {}
    for kind, root in roots.items():
        if root is None or not root.is_dir():
            continue
        for path in sorted(root.glob("*.md")):
            if path.name in INDEX_NAMES:
                continue
            st = path.stat()
            out[path.stem] = {
                "kind": kind,
                "path": str(path),
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
    memories = Path(args.memories_dir).resolve() if args.memories_dir else project / "docs" / "memories"

    if not lessons.is_dir():
        print(f"no lessons directory at {lessons}", file=sys.stderr)
        return 2

    roots = {"lesson": lessons, "memory": memories if memories.is_dir() else None}
    result = scan(project, roots, parse_ts(args.since), set(args.exclude_session))
    result["on_disk"] = on_disk(roots)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
