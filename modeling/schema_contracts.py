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


def unique_object_pairs(pairs):
    """Decode one JSON object without silently replacing a repeated name."""
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f'Duplicate JSON key: {name}')
        result[name] = value
    return result


KEYWORDS = {
    "$schema", "type", "properties", "required", "additionalProperties",
    "items", "prefixItems", "minItems", "maxItems", "minimum", "maximum",
    "enum", "description", "examples", "default",
}
TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}


def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _json_value(value, path):
    if type(value) is str:
        try:
            value.encode('utf-8')
        except UnicodeEncodeError as error:
            raise ContractError(f'{path}: expected a Unicode scalar string, not an unpaired surrogate') from error
        return
    if value is None or type(value) in (bool, int):
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
            _json_value(name, f'{path} key')
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
    if "default" in schema:
        _json_value(schema["default"], f"{path}.default")


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


def _record(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required}


_TEXT = {"type": "string"}
_NUMBER = {"type": "number"}
_REFERENCE_MAGNITUDE = _record({
    "value": _NUMBER, "unit": _TEXT, "source": _TEXT,
    "ratio_ok": {"type": "array", "items": _NUMBER, "minItems": 2, "maxItems": 2},
}, ["value", "unit", "source"])

# The structural schema is exportable; cross-field scientific declarations are
# checked below. It deliberately cannot decide whether a declaration is truthful.
MODEL_CONTRACT_V2 = _record({
    "symbols": {"type": "array", "items": _record({
        "symbol": _TEXT, "unit": _TEXT, "object": _TEXT,
        "uses": {"type": "array", "minItems": 1,
                 "items": _record({"equation": _TEXT, "object": _TEXT})},
        "same_object_justification": _TEXT,
    }, ["symbol", "unit", "object", "uses"])},
    "parameters": {"type": "array", "items": _record({
        "symbol": _TEXT, "value": _NUMBER, "unit": _TEXT,
        "source_level": {"enum": ["measured", "literature", "fitted", "declared"]},
        "source": _TEXT, "real_world_quantity": {"type": "boolean"},
        "reference_magnitude": _REFERENCE_MAGNITUDE, "magnitude_justification": _TEXT,
    }, ["symbol", "value", "unit", "source_level", "source", "real_world_quantity"])},
    "mechanisms": {"type": "array", "items": _record({
        "id": _TEXT, "cause": _TEXT, "effect_variable": _TEXT,
        "sign": {"enum": ["+", "-", "±"]}, "equation": _TEXT,
    })},
    "conserved_quantities": {"type": "array", "items": _record({
        "name": _TEXT, "check_name": _TEXT,
    })},
    "probability_combinations": {"type": "array", "items": _record({
        "expression": _TEXT,
        "independence": {"enum": ["assumed", "derived", "not_assumed"]},
        "justification": _TEXT,
    })},
    "logical_claims": {"type": "array", "items": _record({
        "claim": _TEXT, "type": {"enum": ["sufficient", "necessary", "both"]},
        "proof_ref": _TEXT,
    })},
    "limiting_cases": {"type": "array", "items": _record({"case": _TEXT, "expected": _TEXT})},
    "cheapest_refutation": _record({
        "method": {"enum": ["hand_calc", "small_example", "unit_check"]}, "result": _TEXT,
    }),
    "information_time": _TEXT, "spatial": {"type": "boolean"},
})


def check_model_contract(contract) -> list[str]:
    """Check a schema-2 model's declarations, returning problems rather than a verdict.

    Balance checks are execution evidence and are checked by ``run_case`` after
    validation. This function only audits the authored contract itself.
    """
    try:
        validate(contract, MODEL_CONTRACT_V2, "model-contract")
    except (ContractError, ValueError) as exc:
        return [str(exc)]
    problems = []

    def text(value, path):
        if not value.strip():
            problems.append(f"{path}: expected nonempty text")

    for group, key in (("symbols", "symbol"), ("parameters", "symbol"),
                       ("mechanisms", "id"), ("conserved_quantities", "name")):
        seen = set()
        for row in contract[group]:
            identity = row[key].strip()
            if identity in seen:
                problems.append(f"{group}: duplicate {key} {identity!r}; merge all uses in one declaration")
            seen.add(identity)

    for group, fields in (
            ("symbols", ("symbol", "unit", "object")),
            ("parameters", ("symbol", "unit", "source")),
            ("mechanisms", ("id", "cause", "effect_variable", "equation")),
            ("conserved_quantities", ("name", "check_name")),
            ("logical_claims", ("claim", "proof_ref")),
            ("limiting_cases", ("case", "expected"))):
        for index, row in enumerate(contract[group]):
            for field in fields:
                text(row[field], f"{group}[{index}].{field}")
    for row in contract["symbols"]:
        for use in row["uses"]:
            text(use["equation"], f"symbol {row['symbol']} use equation")
            text(use["object"], f"symbol {row['symbol']} use object")
        objects = {use["object"].strip() for use in row["uses"]}
        if len(objects) > 1 and not row.get("same_object_justification", "").strip():
            problems.append(f"symbol {row['symbol']}: different objects across uses {row['uses']}; "
                            "supply same_object_justification")
    for row in contract["parameters"]:
        reference = row.get("reference_magnitude")
        if row["real_world_quantity"] and reference is None:
            problems.append(f"parameter {row['symbol']}: real-world quantity needs reference_magnitude")
        if reference is None:
            continue
        for field in ("unit", "source"):
            text(reference[field], f"parameter {row['symbol']} reference_magnitude.{field}")
        if reference["unit"].strip() != row["unit"].strip():
            problems.append(f"parameter {row['symbol']}: reference_magnitude unit must match parameter unit")
        low, high = reference.get("ratio_ok", [0.1, 10])
        if not 0 <= low <= high:
            problems.append(f"parameter {row['symbol']}: ratio_ok must be ordered nonnegative bounds")
        elif reference["value"] == 0:
            problems.append(f"parameter {row['symbol']}: reference_magnitude.value must be nonzero")
        elif not low <= row["value"] / reference["value"] <= high \
                and not row.get("magnitude_justification", "").strip():
            problems.append(f"parameter {row['symbol']}: magnitude ratio outside ratio_ok [{low}, {high}]; "
                            "supply magnitude_justification")
    for row in contract["conserved_quantities"]:
        if row["check_name"] != "balance:" + row["name"]:
            problems.append(f"conserved quantity {row['name']}: check_name must be balance:{row['name']}")
    for row in contract["probability_combinations"]:
        text(row["expression"], "probability combination expression")
        if row["independence"] == "assumed" and not row["justification"].strip():
            problems.append(f"probability combination {row['expression']}: assumed independence needs justification")
    text(contract["cheapest_refutation"]["result"], "cheapest_refutation.result")
    text(contract["information_time"], "information_time")
    return problems
