"""Fail-closed validation for the JSON Schema subset used by Praxis's MCP registry.

This is not a general JSON Schema implementation. Supported constraint keywords
are listed in ``KEYWORDS``; unsupported keywords and dialects raise rather than
being ignored. Heterogeneous tuples follow JSON Schema 2020-12 ``prefixItems``
and ``items``. Inputs must be finite JSON values, including unconstrained fields.
Shape, units and mathematical admissibility still belong to the tool itself.
"""
import math


class ContractError(ValueError):
    """The input or schema is outside the audited registry contract."""


KEYWORDS = {
    "$schema", "type", "properties", "required", "additionalProperties",
    "items", "prefixItems", "minItems", "maxItems", "minimum", "maximum",
    "enum", "description", "examples",
}
TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}


def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _json_value(value, path):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _json_value(child, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for name, child in value.items():
            if not isinstance(name, str):
                raise ContractError(f"{path}: JSON object keys must be strings")
            _json_value(child, f"{path}.{name}")
        return
    raise ContractError(f"{path}: expected a finite JSON value, got {type(value).__name__}")


def check_schema(schema, path="$schema"):
    """Audit all constraints, rejecting keywords this checker does not implement."""
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise ContractError(f"{path}: expected a schema object or boolean")
    unsupported = set(schema) - KEYWORDS
    if unsupported:
        raise ContractError(f"{path}: unsupported keyword(s) {sorted(unsupported)}")
    if "$schema" in schema and schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        raise ContractError(f"{path}: unsupported schema dialect")
    kind = schema.get("type")
    if "type" in schema:
        kinds = kind if isinstance(kind, list) else [kind]
        if (not kinds or any(not isinstance(k, str) or k not in TYPES for k in kinds)
                or len(set(kinds)) != len(kinds)):
            raise ContractError(f"{path}: unsupported type declaration")
    for key in ("minItems", "maxItems"):
        if key in schema and (not _number(schema[key]) or schema[key] < 0
                              or (type(schema[key]) is float and not schema[key].is_integer())):
            raise ContractError(f"{path}.{key}: expected a nonnegative integer")
    for key in ("minimum", "maximum"):
        if key in schema and not _number(schema[key]):
            raise ContractError(f"{path}.{key}: expected a finite number")
    if "properties" in schema:
        if not isinstance(schema["properties"], dict):
            raise ContractError(f"{path}.properties: expected an object")
        for name, child in schema["properties"].items():
            if not isinstance(name, str):
                raise ContractError(f"{path}.properties: expected string names")
            check_schema(child, f"{path}.properties.{name}")
    if "required" in schema:
        required = schema["required"]
        if (not isinstance(required, list) or any(not isinstance(k, str) for k in required)
                or len(set(required)) != len(required)):
            raise ContractError(f"{path}.required: expected unique strings")
    if "prefixItems" in schema:
        if not isinstance(schema["prefixItems"], list) or not schema["prefixItems"]:
            raise ContractError(f"{path}.prefixItems: expected a nonempty array")
        for index, child in enumerate(schema["prefixItems"]):
            check_schema(child, f"{path}.prefixItems[{index}]")
    for key in ("items", "additionalProperties"):
        if key in schema:
            check_schema(schema[key], f"{path}.{key}")
    if "enum" in schema:
        if not isinstance(schema["enum"], list):
            raise ContractError(f"{path}.enum: expected an array")
        _json_value(schema["enum"], f"{path}.enum")
    if "description" in schema and not isinstance(schema["description"], str):
        raise ContractError(f"{path}.description: expected a string")
    if "examples" in schema:
        if not isinstance(schema["examples"], list):
            raise ContractError(f"{path}.examples: expected an array")
        _json_value(schema["examples"], f"{path}.examples")


def _is_type(value, kind):
    numeric = _number(value)
    return {
        "object": isinstance(value, dict), "array": isinstance(value, list),
        "string": isinstance(value, str), "number": numeric,
        "integer": numeric and (type(value) is int or value.is_integer()),
        "boolean": isinstance(value, bool), "null": value is None,
    }[kind]


def _equal(left, right):
    """JSON equality treats 1 and 1.0 equally but distinguishes 1 from true."""
    if _number(left) and _number(right):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_equal(left[k], right[k]) for k in left)
    return left == right


def _validate(value, schema, path):
    if schema is True:
        return
    if schema is False:
        raise ContractError(f"{path}: additional value is prohibited")
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        if not any(_is_type(value, kind) for kind in kinds):
            raise ContractError(f"{path}: expected {kinds}, got {type(value).__name__}")
    if "enum" in schema and not any(_equal(value, choice) for choice in schema["enum"]):
        raise ContractError(f"{path}: value outside enum")
    if _number(value):
        if "minimum" in schema and value < schema["minimum"]:
            raise ContractError(f"{path}: value below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ContractError(f"{path}: value above maximum")
    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - set(value)
        if missing:
            raise ContractError(f"{path}: missing required fields {sorted(missing)}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for name, child in value.items():
            _validate(child, properties.get(name, additional), f"{path}.{name}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", math.inf):
            raise ContractError(f"{path}: array length outside bounds")
        prefix = schema.get("prefixItems", [])
        for index, child in enumerate(value):
            item_schema = prefix[index] if index < len(prefix) else schema.get("items", True)
            _validate(child, item_schema, f"{path}[{index}]")


def validate(value, schema, path="$"):
    """Validate finite JSON input against the audited supported keyword subset."""
    check_schema(schema)
    _json_value(value, path)
    _validate(value, schema, path)
