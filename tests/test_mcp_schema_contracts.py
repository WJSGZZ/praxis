"""Audit published MCP inputs and bounded stdio behavior without new dependencies.

This is a fail-closed checker for the JSON Schema keywords used by this registry,
not a general JSON Schema implementation or a strict-client integration test.
Unknown keywords fail the schema audit so a new constraint cannot silently pass.
The tuple convention is JSON Schema 2020-12 ``prefixItems`` plus ``items``.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import mcp_server

from modeling.schema_contracts import ContractError, check_schema, validate


ROOT = Path(__file__).resolve().parents[1]


def rpc(messages):
    result = subprocess.run(
        [sys.executable, "-m", "scripts.mcp_server"], cwd=ROOT,
        input="\n".join(json.dumps(message, allow_nan=False) for message in messages) + "\n",
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return [json.loads(line) for line in result.stdout.splitlines()]


@pytest.mark.parametrize("name", sorted(mcp_server.TOOLS))
def test_all_published_schemas_use_checked_keywords(name):
    schema = mcp_server.TOOLS[name]["schema"]
    check_schema(schema)
    assert schema["type"] == "object"
    assert set(schema["required"]) <= set(schema["properties"])
    assert schema.get("additionalProperties") is False


@pytest.mark.parametrize("name", sorted(mcp_server.TOOLS))
def test_all_registry_input_types_and_named_field_boundaries(name):
    schema = mcp_server.TOOLS[name]["schema"]
    with pytest.raises(ContractError, match="expected"):
        validate([], schema)
    if schema["required"]:
        with pytest.raises(ContractError, match="missing required"):
            validate({}, schema)
    # Insert the unexpected name first so it is checked before placeholder
    # required values. This isolates additionalProperties from field types.
    extra = {"__unexpected_argument__": 1, **{field: None for field in schema["required"]}}
    with pytest.raises(ContractError, match="prohibited"):
        validate(extra, schema)
    wrong_values = {"object": [], "array": {}, "string": 42, "number": True,
                    "integer": True, "boolean": 1, "null": "not null"}
    for child_schema in schema["properties"].values():
        kind = child_schema.get("type")
        if isinstance(kind, str):
            with pytest.raises(ContractError, match="expected"):
                validate(wrong_values[kind], child_schema)


EXAMPLE_CASES = [
    (name, index, example)
    for name, tool in mcp_server.TOOLS.items()
    for index, example in enumerate(tool["schema"].get("examples", []))
]


@pytest.mark.parametrize("name,index,example", EXAMPLE_CASES, ids=[f"{n}-{i}" for n, i, _ in EXAMPLE_CASES])
def test_all_published_examples_satisfy_schema(name, index, example):
    schema = mcp_server.TOOLS[name]["schema"]
    check_schema(schema)
    # Ensure the Python source example is also a valid JSON document.
    json.dumps(example, allow_nan=False)
    validate(example, schema)
    assert mcp_server.EXAMPLES[name] == example


def test_source_examples_and_published_examples_cover_the_same_tools():
    assert set(mcp_server.EXAMPLES) == {name for name, _, _ in EXAMPLE_CASES}
    assert set(mcp_server.EXAMPLES) <= set(mcp_server.TOOLS)


def test_actual_stdio_listing_publishes_the_audited_schema_and_examples():
    replies = rpc([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
    listed = {tool["name"]: tool for tool in replies[0]["result"]["tools"]}
    assert set(listed) == set(mcp_server.TOOLS)
    for name, tool in listed.items():
        schema = tool["inputSchema"]
        assert schema == mcp_server.TOOLS[name]["schema"]
        check_schema(schema)
        for example in schema.get("examples", []):
            validate(example, schema)


def test_flow_contract_rejects_bad_inputs_before_the_computation(monkeypatch):
    def unexpected_execution(arguments):
        raise AssertionError("invalid input reached the mathematical implementation")

    monkeypatch.setitem(mcp_server.TOOLS["min_cost_flow"], "function", unexpected_execution)
    valid = mcp_server.EXAMPLES["min_cost_flow"]
    bad_inputs = [
        {"edges": [["a", "b", 1, 1]]},
        {**valid, "extra": 1},
        {**valid, "edges": [["a", "b", 1, 1, 2]]},
        {**valid, "edges": [["a", "b", "capacity", 1]]},
        {**valid, "edges": [["a", "b", True, 1]]},
        {**valid, "demand": {"a": "supply"}},
    ]
    for arguments in bad_inputs:
        with pytest.raises(ValueError):
            mcp_server.call("min_cost_flow", arguments)


def test_actual_stdio_flow_known_answer_error_delivery_and_recovery():
    valid = mcp_server.EXAMPLES["min_cost_flow"]
    cases = [valid, {**valid, "edges": [["a", "b", "capacity", 1]]},
             {**valid, "edges": [["a", "b", 1, 1, 2]]},
             {**valid, "demand": {"a": "supply"}}]
    messages = [
        {"jsonrpc": "2.0", "id": index + 1, "method": "tools/call",
         "params": {"name": "min_cost_flow", "arguments": arguments}}
        for index, arguments in enumerate(cases)
    ]
    messages.append({"jsonrpc": "2.0", "id": len(cases) + 1, "method": "ping"})
    replies = rpc(messages)
    assert [reply["id"] for reply in replies] == list(range(1, len(messages) + 1))
    result = replies[0]["result"]
    assert result["isError"] is False
    solved = json.loads(result["content"][0]["text"])
    # One unit on the capacity-one route costs 2; the other costs 4.
    assert solved["feasible"] and solved["cost"] == pytest.approx(6)
    for reply in replies[1:-1]:
        assert reply["result"]["isError"] is True
        assert "ContractError" in reply["result"]["content"][0]["text"]
    assert replies[-1]["result"] == {}


@pytest.mark.parametrize("use_float_integers", [False, True])
def test_actual_stdio_flow_json_integer_nodes_match_demand_keys(use_float_integers):
    edge_nodes = [[1, 2, 1, 1], [2, 4, 1, 1], [1, 3, 5, 2], [3, 4, 5, 2]]
    if use_float_integers:
        edge_nodes = [[float(u), float(v), cap, cost] for u, v, cap, cost in edge_nodes]
    arguments = {"edges": edge_nodes, "demand": {"1": -2, "2": 0, "3": 0, "4": 2}}
    validate(arguments, mcp_server.TOOLS["min_cost_flow"]["schema"])
    replies = rpc([{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "min_cost_flow", "arguments": arguments}}])
    result = replies[0]["result"]
    assert result["isError"] is False
    solved = json.loads(result["content"][0]["text"])
    assert solved["feasible"] and solved["cost"] == pytest.approx(6)


def test_actual_stdio_flow_ambiguous_integer_string_node_collision_is_rejected():
    arguments = {"edges": [[1, "1", 1, 1], ["1", "2", 1, 1]],
                 "demand": {"1": -1, "2": 1}}
    validate(arguments, mcp_server.TOOLS["min_cost_flow"]["schema"])
    replies = rpc([
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "min_cost_flow", "arguments": arguments}},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    ])
    assert replies[0]["result"]["isError"] is True
    assert "Ambiguous node labels" in replies[0]["result"]["content"][0]["text"]
    assert replies[1]["result"] == {}


@pytest.mark.parametrize("requested", ["2025-06-18", "praxis-schema-unsupported-version"])
def test_actual_stdio_supported_and_unknown_protocol_versions(requested):
    replies = rpc([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": requested}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    ])
    assert [reply["id"] for reply in replies] == [1, 2]
    assert replies[0]["result"]["protocolVersion"] == "2025-06-18"
    assert replies[1]["result"] == {}


@pytest.mark.parametrize("name,index,example", EXAMPLE_CASES, ids=[f"{n}-{i}" for n, i, _ in EXAMPLE_CASES])
def test_example_fields_reject_wrong_types_missing_required_and_extra_fields(name, index, example):
    schema = mcp_server.TOOLS[name]["schema"]
    # Missing mandatory arguments and extra named arguments must be rejected by
    # the public schema as well as by the server's independent call guard.
    for field in schema["required"]:
        broken = deepcopy(example)
        del broken[field]
        with pytest.raises(ContractError, match="missing required"):
            validate(broken, schema)
    broken = deepcopy(example)
    broken["__unexpected_argument__"] = "should be rejected"
    with pytest.raises(ContractError, match="prohibited"):
        validate(broken, schema)
    wrong_values = {"object": [], "array": {}, "string": 42, "number": True,
                    "integer": True, "boolean": 1, "null": "not null"}
    for field, child_schema in schema["properties"].items():
        kind = child_schema.get("type")
        if not isinstance(kind, str):
            continue
        broken = deepcopy(example)
        broken[field] = wrong_values[kind]
        with pytest.raises(ContractError, match="expected"):
            validate(broken, schema)


def test_min_cost_flow_tuple_contract_rejects_malformed_edges_and_demand():
    schema = mcp_server.TOOLS["min_cost_flow"]["schema"]
    example = mcp_server.EXAMPLES["min_cost_flow"]
    validate(example, schema)
    for edge in (["a", "b", 1], ["a", "b", 1, 1, 2],
                 ["a", "b", "one", 1], ["a", "b", 1, "cost"],
                 ["a", "b", True, 1], ["a", "b", -1, 1],
                 [True, "b", 1, 1],
                 [["a"], "b", 1, 1]):
        broken = deepcopy(example)
        broken["edges"][0] = edge
        with pytest.raises(ContractError):
            validate(broken, schema)
    broken = deepcopy(example)
    broken["demand"]["a"] = "supply"
    with pytest.raises(ContractError):
        validate(broken, schema)


def test_schema_checker_is_fail_closed_and_handles_json_type_boundaries():
    for unknown in ("pattern", "anyOf", "$ref"):
        with pytest.raises(ContractError, match="unsupported keyword"):
            check_schema({"type": "string", unknown: "unchecked"})
    validate(1.0, {"type": "integer"})  # JSON Schema's integer type is mathematical.
    for value in (True, False, float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ContractError):
            validate(value, {"type": "number"})
    validate(None, {"type": ["number", "null"]})
    with pytest.raises(ContractError):
        validate("bad", {"type": ["number", "null"]})


@pytest.mark.parametrize("schema", [
    {"type": None}, {"type": ["integer", "integer"]}, {"type": []},
    {"type": "unknown"}, {"items": []}, {"prefixItems": {}}, {"prefixItems": []},
    {"required": ["x", "x"]}, {"required": [1]}, {"properties": []},
    {"minItems": True}, {"maxItems": -1}, {"minimum": True},
    {"maximum": float("inf")}, {"examples": {}}, {"enum": {}},
    {"$schema": "https://json-schema.org/draft-07/schema#"},
    {"properties": {"x": {"type": "number", "exclusiveMinimum": 0}}},
])
def test_malformed_or_unsupported_schemas_are_rejected(schema):
    with pytest.raises(ContractError):
        check_schema(schema)


@pytest.mark.parametrize("value,schema", [
    ([[1, 2], [3, "4"]], {"type": "array", "items": {"type": "array", "items": {"type": "number"}}}),
    ([1, "not numeric"], {"type": "array", "prefixItems": [{"type": "string"}, {"type": "number"}], "items": False}),
    (["node", 1, "extra"], {"type": "array", "prefixItems": [{"type": "string"}, {"type": "number"}], "items": False}),
    ([], {"minItems": 1}), ([1, 2], {"maxItems": 1}),
    (-1, {"minimum": 0}), (3, {"maximum": 2}),
    ({"extra": 1}, {"properties": {"x": {"type": "number"}}, "additionalProperties": False}),
    ({"a": "x"}, {"additionalProperties": {"type": "number"}}),
    (True, {"enum": [1]}), ("other", {"enum": ["allowed"]}),
    (1, {"enum": []}),
    (None, False),
    ({"unconstrained": float("nan")}, {"type": "object"}),
    ({1: "not a JSON object key"}, {"type": "object"}),
])
def test_known_invalid_json_or_constraint_violations_are_rejected(value, schema):
    with pytest.raises(ContractError):
        validate(value, schema)


@pytest.mark.parametrize("value,schema", [
    (["node", 1], {"type": "array", "prefixItems": [{"type": "string"}, {"type": "number"}], "items": False}),
    (["node", 1, 2], {"type": "array", "prefixItems": [{"type": "string"}], "items": {"type": "number"}}),
    ([], {"prefixItems": [{"type": "string"}], "items": False}),
    ({"a": 1}, {"additionalProperties": {"type": "number"}}),
    (1.0, {"enum": [1]}), ({"x": [1.0]}, {"enum": [{"x": [1]}]}),
    (1.0, {"enum": [1, 1.0]}), ([], {"maxItems": 0.0}),
    (10 ** 400, {"type": "integer"}),
    (2, {"type": ["string", "integer"]}),
    (None, True), ("unconstrained", {}),
])
def test_known_valid_json_schema_boundary_cases(value, schema):
    validate(value, schema)
