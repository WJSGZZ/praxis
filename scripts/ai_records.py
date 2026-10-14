"""Select actual emitted records from an explicitly supplied Codex JSONL export.

No host discovery, reconstruction, upload, or completeness certification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).absolute().parents[1]))

from scripts.feedback import encoded, loads

SCHEMA = "praxis-ai-records/1"
MAX_BYTES = 32 * 1024 * 1024
MAX_CAPTURE_BYTES = 128 * 1024 * 1024
CALLS = {"function_call", "custom_tool_call"}
OUTPUTS = {"function_call_output", "custom_tool_call_output"}
FIELDS = {"type", "id", "role", "content", "phase", "call_id", "name", "arguments", "input", "output", "status"}


def source_identity(rows, thread_id):
    """Validate an active header and the explicit inherited subagent chain."""
    if rows[0].get("type") != "session_meta" or rows[0]["payload"].get("id") != thread_id:
        raise ValueError("Source thread identity mismatch or missing session metadata")
    metas = [row["payload"] for row in rows if row.get("type") == "session_meta"]
    expected = thread_id
    lineage = []
    for meta in metas:
        identity = meta.get("id")
        if identity != expected or identity in lineage:
            raise ValueError("Unrelated or duplicate inherited session metadata")
        lineage.append(identity)
        source = meta.get("source")
        subagent = source.get("subagent") if isinstance(source, dict) else None
        spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
        parent = spawn.get("parent_thread_id") if isinstance(spawn, dict) else None
        if parent:
            if not isinstance(parent, str) or parent == identity:
                raise ValueError("Invalid subagent parent identity")
            for field in ("parent_thread_id", "forked_from_id"):
                if meta.get(field) is not None and meta[field] != parent:
                    raise ValueError("Conflicting subagent parent identities")
        elif meta.get("session_id", identity) != identity:
            raise ValueError("Conflicting source thread identities")
        expected = parent
    permitted_sessions = lineage + ([expected] if expected is not None else [])
    for meta in metas:
        if meta.get("session_id", meta["id"]) not in permitted_sessions:
            raise ValueError("Session identity outside verified source lineage")
    return lineage, expected


def capture(source: Path, output: Path, *, thread_id: str, max_bytes: int | None = None):
    """Write a new private snapshot; verify identity before selecting any content."""
    source = Path(source)
    output = Path(output)
    max_bytes = MAX_BYTES if max_bytes is None else max_bytes
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_CAPTURE_BYTES:
        raise ValueError("Snapshot byte limit must be a positive integer <= 128 MiB")
    if not thread_id or not thread_id.strip():
        raise ValueError("Explicit thread identity required")
    if source.is_symlink() or not source.is_file():
        raise ValueError("Source must be an explicit regular JSONL file")
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if source.stat().st_size > max_bytes:
        raise ValueError("Source exceeds snapshot byte limit")
    data = source.read_bytes()
    if len(data) > max_bytes:
        raise ValueError("Source exceeds snapshot byte limit")
    if not data or not data.endswith(b"\n"):
        raise ValueError("Incomplete JSONL source; retry after host finishes the line")
    rows = [loads(line) for line in data.splitlines()]
    if any(not isinstance(row, dict) or not isinstance(row.get("payload"), dict) for row in rows):
        raise ValueError("Expected Codex JSONL records with object payloads")
    lineage, absent_parent = source_identity(rows, thread_id)
    records, models = [], []
    excluded = Counter()
    pending = set()
    orphan_outputs = []
    compacted = False
    for number, row in enumerate(rows, 1):
        kind, payload = row.get("type"), row["payload"]
        if kind in {"compacted", "context_compacted"} or payload.get("type") in {"context_compacted", "compacted"}:
            compacted = True
        if kind == "turn_context":
            model = {key: payload[key] for key in ("model", "effort") if key in payload}
            if model and model not in models:
                models.append(model)
        item_type = payload.get("type")
        selected = kind == "response_item" and (
            (item_type == "message" and payload.get("role") in {"user", "assistant"}
             and payload.get("channel") != "analysis" and payload.get("phase") != "analysis")
            or item_type in CALLS | OUTPUTS
        )
        if not selected:
            excluded[str(kind) + ":" + str(item_type)] += 1
            continue
        item = {key: value for key, value in payload.items() if key in FIELDS}
        records.append({"source_line": number, "timestamp": row.get("timestamp", "unknown"), "item": item})
        call_id = payload.get("call_id")
        if item_type in CALLS and call_id:
            pending.add(call_id)
        elif item_type in OUTPUTS and call_id:
            if call_id not in pending:
                orphan_outputs.append(call_id)
            pending.discard(call_id)
    if not records:
        raise ValueError("No emitted user/assistant/tool records in source")
    result = {
        "schema": SCHEMA, "captured_utc": datetime.now(timezone.utc).isoformat(),
        "thread_id": thread_id,
        "inherited_thread_ids": lineage[1:],
        "declared_parent_without_metadata": absent_parent,
        "source_snapshot": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "lines": len(rows)},
        "snapshot_byte_limit": max_bytes,
        "model_contexts": {"source": "host-export turn_context; service build unverified", "values": models},
        "coverage": "Selected emitted records from this explicit snapshot; history completeness unverified.",
        "compaction_observed": compacted,
        "pending_call_ids": sorted(pending), "orphan_output_ids": orphan_outputs,
        "excluded_record_counts": dict(sorted(excluded.items())),
        "limitations": [
            "System/developer message records, reasoning records, account header metadata and host state are excluded.",
            "User-role records may include host-injected task context; they are not all human contributions.",
            "Inherited parent context is retained when present; it is not new work performed by this child.",
            "A snapshot can end during an active turn; pending calls and later outputs are not reconstructed.",
            "No historical-completeness, human-verification or contest-compliance certification.",
            "Selected text/tool results are exact and can reproduce private content or metadata; review before any sharing.",
        ],
        "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(encoded(result))
    return {"output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "records": len(records), "source_snapshot": result["source_snapshot"],
            "snapshot_byte_limit": max_bytes,
            "coverage": result["coverage"], "compaction_observed": compacted,
            "inherited_thread_ids": result["inherited_thread_ids"],
            "declared_parent_without_metadata": absent_parent,
            "pending_calls": len(pending), "model_contexts": result["model_contexts"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES,
                        help="Explicit source limit in bytes (default 32 MiB; maximum 128 MiB)")
    args = parser.parse_args(argv)
    try:
        result = capture(args.source, args.output, thread_id=args.thread_id, max_bytes=args.max_bytes)
    except (ValueError, OSError) as error:
        # Retain the established plain-text error/exit-2 contract while making
        # filenames and messages safe for legacy redirected output streams.
        print(str(error).encode('ascii', errors='backslashreplace').decode('ascii'), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
