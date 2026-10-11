import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import ai_records


def source(tmp_path, *, compacted=False):
    rows = [
        {"type": "session_meta", "payload": {"id": "test-thread", "creator_account_id": "PRIVATE-ACCOUNT", "base_instructions": "PRIVATE-SYSTEM"}},
        {"type": "turn_context", "payload": {"model": "host-model", "effort": "high", "cwd": "/private/path", "developer_instructions": "PRIVATE-DEV"}},
        {"type": "response_item", "payload": {"type": "message", "role": "developer", "content": "PRIVATE-DEV"}},
        {"type": "response_item", "payload": {"type": "reasoning", "summary": "PRIVATE-REASONING"}},
        {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "原句\n\"quoted\""}], "internal_chat_message_metadata_passthrough": "PRIVATE-META"}},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "call_id": "call-1", "name": "functions.exec", "input": "text(1 + 2);"}},
        {"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "call-1", "output": "3\n"}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "phase": "final", "content": [{"type": "output_text", "text": "3。"}]}},
    ]
    if compacted:
        rows.append({"type": "compacted", "payload": {"message": "PRIVATE-SUMMARY"}})
    path = tmp_path / "source.jsonl"
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    return path, rows


def test_exact_emitted_content_and_metadata_exclusion(tmp_path):
    path, rows = source(tmp_path)
    output = tmp_path / "records.json"
    receipt = ai_records.capture(path, output, thread_id="test-thread")
    data = json.loads(output.read_text())
    assert data["records"][0]["item"]["content"] == rows[4]["payload"]["content"]
    assert data["records"][1]["item"]["input"] == "text(1 + 2);"
    assert data["records"][2]["item"]["output"] == "3\n"
    assert data["records"][3]["item"]["content"][0]["text"] == "3。"
    assert "PRIVATE-" not in output.read_text()
    assert receipt["records"] == 4
    assert data["pending_call_ids"] == []
    assert data["model_contexts"]["values"] == [{"model": "host-model", "effort": "high"}]
    assert "unverified" in data["coverage"]


def test_compaction_and_active_call_remain_explicit(tmp_path):
    path, rows = source(tmp_path, compacted=True)
    rows.append({"type": "response_item", "payload": {"type": "function_call", "call_id": "pending", "name": "run", "arguments": "{}"}})
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    ai_records.capture(path, tmp_path / "records.json", thread_id="test-thread")
    data = json.loads((tmp_path / "records.json").read_text())
    assert data["compaction_observed"]
    assert data["pending_call_ids"] == ["pending"]
    assert "PRIVATE-SUMMARY" not in json.dumps(data)


@pytest.mark.parametrize("mutation", ["wrong-thread", "conflicting-thread", "missing-meta", "partial-line", "bad-json"])
def test_rejected_source_never_writes_a_claimed_snapshot(tmp_path, mutation):
    path, rows = source(tmp_path)
    thread = "test-thread"
    if mutation == "wrong-thread":
        thread = "other-thread"
    elif mutation == "conflicting-thread":
        rows[0]["payload"]["session_id"] = "other-thread"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    elif mutation == "missing-meta":
        path.write_text("".join(json.dumps(row) + "\n" for row in rows[1:]))
    elif mutation == "partial-line":
        path.write_bytes(path.read_bytes().rstrip(b"\n"))
    else:
        path.write_text("not json\n")
    output = tmp_path / "records.json"
    with pytest.raises(ValueError):
        ai_records.capture(path, output, thread_id=thread)
    assert not output.exists()


def test_no_overwrite_and_source_preserved_with_cli(tmp_path):
    path, _ = source(tmp_path)
    before = path.read_bytes()
    output = tmp_path / "records.json"
    command = [sys.executable, "-m", "scripts.ai_records", "--source", str(path), "--output", str(output), "--thread-id", "test-thread"]
    result = subprocess.run(command, cwd=Path(ai_records.__file__).parents[1], text=True, capture_output=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)["records"] == 4
    assert path.read_bytes() == before
    snapshot = output.read_bytes()
    result = subprocess.run(command, cwd=Path(ai_records.__file__).parents[1], text=True, capture_output=True)
    assert result.returncode == 2
    assert output.read_bytes() == snapshot
    direct = tmp_path / "direct.json"
    command = [sys.executable, ai_records.__file__, "--source", str(path), "--output", str(direct), "--thread-id", "test-thread"]
    result = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0
    assert json.loads(direct.read_text())["records"] == json.loads(output.read_text())["records"]


def child_source(tmp_path):
    path, rows = source(tmp_path)
    child = {"type": "session_meta", "payload": {
        "id": "child-thread", "session_id": "test-thread", "parent_thread_id": "test-thread",
        "forked_from_id": "test-thread", "source": {"subagent": {"thread_spawn": {"parent_thread_id": "test-thread"}}},
    }}
    rows.insert(0, child)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path, rows


def test_actual_subagent_header_retains_explicit_inherited_parent(tmp_path):
    path, _ = child_source(tmp_path)
    ai_records.capture(path, tmp_path / "records.json", thread_id="child-thread")
    data = json.loads((tmp_path / "records.json").read_text())
    assert data["thread_id"] == "child-thread"
    assert data["inherited_thread_ids"] == ["test-thread"]
    assert len(data["records"]) == 4
    assert "not new work" in " ".join(data["limitations"])


@pytest.mark.parametrize("mutation", ["unrelated", "duplicate", "no-parent-link", "wrong-parent-field", "foreign-session"])
def test_child_lineage_does_not_allow_arbitrary_metadata(tmp_path, mutation):
    path, rows = child_source(tmp_path)
    if mutation == "unrelated":
        rows[1]["payload"]["id"] = "other-thread"
    elif mutation == "duplicate":
        rows.insert(2, rows[1])
    elif mutation == "no-parent-link":
        del rows[1]
        rows[0]["payload"]["source"] = "vscode"
    elif mutation == "wrong-parent-field":
        rows[0]["payload"]["forked_from_id"] = "other-thread"
    else:
        rows[0]["payload"]["session_id"] = "other-thread"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    output = tmp_path / "records.json"
    with pytest.raises(ValueError):
        ai_records.capture(path, output, thread_id="child-thread")
    assert not output.exists()


def test_fresh_subagent_has_explicit_parent_but_no_inherited_history(tmp_path):
    path, rows = child_source(tmp_path)
    del rows[1]
    rows[0]["payload"]["forked_from_id"] = None
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    ai_records.capture(path, tmp_path / "records.json", thread_id="child-thread")
    data = json.loads((tmp_path / "records.json").read_text())
    assert data["inherited_thread_ids"] == []
    assert data["declared_parent_without_metadata"] == "test-thread"


def test_explicit_limit_recovers_same_exact_source_without_slicing(tmp_path, monkeypatch):
    path, _ = source(tmp_path)
    original = path.read_bytes()
    monkeypatch.setattr(ai_records, 'MAX_BYTES', len(original) - 1)
    output = tmp_path / 'records.json'
    with pytest.raises(ValueError, match='byte limit'):
        ai_records.capture(path, output, thread_id='test-thread')
    assert not output.exists()
    receipt = ai_records.capture(path, output, thread_id='test-thread', max_bytes=len(original))
    assert receipt['source_snapshot']['bytes'] == len(original)
    assert receipt['snapshot_byte_limit'] == len(original)
    assert path.read_bytes() == original
    assert json.loads(output.read_text())['snapshot_byte_limit'] == len(original)


@pytest.mark.parametrize('limit', [0, -1, True, 1.5, '1024', ai_records.MAX_CAPTURE_BYTES + 1])
def test_explicit_limit_cannot_be_invalid_or_unbounded(tmp_path, limit):
    path, _ = source(tmp_path)
    output = tmp_path / 'records.json'
    with pytest.raises(ValueError, match='positive integer'):
        ai_records.capture(path, output, thread_id='test-thread', max_bytes=limit)
    assert not output.exists()


def test_cli_explicit_source_limit(tmp_path):
    path, _ = source(tmp_path)
    output = tmp_path / 'records.json'
    argv = [sys.executable, str(ai_records.__file__), '--source', str(path),
            '--output', str(output), '--thread-id', 'test-thread', '--max-bytes']
    result = subprocess.run(argv + [str(path.stat().st_size - 1)], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 2 and not output.exists()
    result = subprocess.run(argv + [str(path.stat().st_size)], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0 and json.loads(result.stdout)['snapshot_byte_limit'] == path.stat().st_size
