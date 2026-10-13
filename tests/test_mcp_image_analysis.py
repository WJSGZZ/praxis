"""MCP schema, lazy-loading, describe and stdio recovery for image measurements."""
import json
import subprocess
import sys
from pathlib import Path

from scripts import mcp_server

ROOT = Path(__file__).resolve().parents[1]


def _rpc(*messages):
    process = subprocess.run([sys.executable, "-m", "scripts.mcp_server"], cwd=ROOT,
                           input="\n".join(json.dumps(message) for message in messages) + "\n",
                           capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stderr
    return [json.loads(line) for line in process.stdout.splitlines()]


def test_schema_is_explicit_nullable_bounded_and_describable():
    schema = mcp_server.TOOLS["binary_components"]["schema"]
    assert schema["required"] == ["mask"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["mask"]["maxItems"] == 512
    assert schema["properties"]["pixel_size"]["type"] == ["array", "null"]
    assert schema["properties"]["pixel_size"]["items"] is False
    assert schema["properties"]["unit"]["type"] == ["string", "null"]
    assert {key: schema["properties"][key]["default"] for key in ("connectivity", "min_pixels", "exclude_border", "max_components", "pixel_size", "unit")} == {"connectivity": 8, "min_pixels": 1, "exclude_border": False, "max_components": 200, "pixel_size": None, "unit": None}
    assert schema["properties"]["connectivity"]["enum"] == [4, 8]
    described = subprocess.run([sys.executable, "-m", "scripts.mcp_server", "--describe", "binary_components"],
                               cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
    output = json.loads(described.stdout)
    assert output["name"] == "binary_components"
    assert output["input"] == schema


def test_lazy_module_loads_only_for_tool_call_in_fresh_process():
    code = (
        "import sys; from scripts import mcp_server; "
        "assert 'modeling.image_analysis' not in sys.modules; "
        "r=mcp_server.call('binary_components', {'mask': [[0,1],[0,0]]}); "
        "assert r['raw_component_count']==1; "
        "assert 'modeling.image_analysis' in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, timeout=30)


def test_stdio_tool_error_does_not_prevent_next_valid_image_call():
    valid = {"mask": [[0, 0, 0], [0, 1, 1], [0, 0, 0]], "pixel_size": [2, 3], "unit": "mm"}
    ragged = {"mask": [[1, 0], [1]]}
    replies = _rpc(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "binary_components", "arguments": valid}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "binary_components", "arguments": ragged}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "binary_components", "arguments": valid}},
    )
    assert len(replies) == 3
    first = json.loads(replies[0]["result"]["content"][0]["text"])
    assert replies[0]["result"]["isError"] is False
    assert first["components"][0]["physical_area"] == 12.0
    assert replies[1]["result"]["isError"] is True
    assert replies[2]["result"]["isError"] is False
    assert json.loads(replies[2]["result"]["content"][0]["text"])["raw_component_count"] == 1


def test_schema_rejects_wrong_types_limits_and_nullability():
    bad_arguments = [
        {"mask": [["1"]]},
        {"mask": [[1]], "connectivity": True},
        {"mask": [[1]], "connectivity": 6},
        {"mask": [[1]], "pixel_size": ["2", 3], "unit": "mm"},
        {"mask": [[1]], "pixel_size": [2, 3]},
        {"mask": [[1]], "pixel_size": None, "unit": "mm"},
        {"mask": [[1]], "unknown": 1},
        {"mask": [[1]], "max_components": 1001},
    ]
    for arguments in bad_arguments:
        try:
            mcp_server.call("binary_components", arguments)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(f"Accepted invalid image arguments: {arguments!r}")


def test_schema_accepts_explicit_nullables_and_defaults():
    defaulted = mcp_server.call("binary_components", {"mask": [[1]]})
    explicit_null = mcp_server.call("binary_components", {"mask": [[1]], "pixel_size": None, "unit": None})
    assert defaulted["connectivity"] == explicit_null["connectivity"] == 8
    assert defaulted["max_components"] == explicit_null["max_components"] == 200
    assert "calibration" not in defaulted
    assert explicit_null["components"] == defaulted["components"]
