"""Fail-closed validation for the JSON Schema subset used by Praxis's MCP registry.

This is not a general JSON Schema implementation. Supported constraint keywords
are listed in ``KEYWORDS``; unsupported keywords and dialects raise rather than
being ignored. Heterogeneous tuples follow JSON Schema 2020-12 ``prefixItems``
and ``items``. Inputs must be finite JSON values, including unconstrained fields.
Shape, units and mathematical admissibility still belong to the tool itself.
"""
import math
import re


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
        # null is allowed only together with source_level "unknown" (checked below).
        "symbol": _TEXT, "value": {"type": ["number", "null"]}, "unit": _TEXT,
        "source_level": {"enum": ["measured", "literature", "fitted", "declared", "unknown"]},
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

DEFAULT_RATIO_OK = (0.1, 10)  # experimental parameter, see references/modeling-gate.md


def _collect(value, schema, path, problems):
    """Like ``_validate`` but records every structural problem instead of stopping at the first."""
    if schema is True:
        return
    if schema is False:
        problems.append(f"{path}: additional value is prohibited")
        return
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        if not any(_is_type(value, kind) for kind in kinds):
            problems.append(f"{path}: expected {kinds}, got {type(value).__name__}")
            return
    if "enum" in schema and not any(_equal(value, choice) for choice in schema["enum"]):
        problems.append(f"{path}: value outside enum")
    if _number(value):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append(f"{path}: value below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            problems.append(f"{path}: value above maximum")
    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - set(value)
        if missing:
            problems.append(f"{path}: missing required fields {sorted(missing)}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for name, child in value.items():
            _collect(child, properties.get(name, additional), f"{path}.{name}", problems)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", math.inf):
            problems.append(f"{path}: array length outside bounds")
        prefix = schema.get("prefixItems", [])
        for index, child in enumerate(value):
            item_schema = prefix[index] if index < len(prefix) else schema.get("items", True)
            _collect(child, item_schema, f"{path}[{index}]", problems)


def symbol_key(symbol):
    """Compare symbol spellings without spaces, braces or backslashes: H_z == H_{z} == \\H_{ z }."""
    return re.sub(r"[\s{}\\]", "", symbol) if isinstance(symbol, str) else None


def reasoned(text):
    """A justification must contain at least three letters (any script, including CJK)."""
    return isinstance(text, str) and len(re.findall(r"[^\W\d_]", text)) >= 3


def check_model_contract(contract, warnings=None) -> list[str]:
    """Check a schema-2 model's declarations, returning every problem found rather than a verdict.

    Structural problems do not stop the cross-field checks: rows or fields with a
    wrong type are skipped there, other rows are still audited. Non-blocking
    findings (unknown parameter values and differing object descriptions) are appended to ``warnings``
    when a list is supplied. Balance checks are execution evidence and are checked
    by ``run_case`` after validation.
    """
    warnings = [] if warnings is None else warnings
    try:
        check_schema(MODEL_CONTRACT_V2)
        _json_value(contract, "model-contract")
    except (ContractError, ValueError) as exc:
        return [str(exc)]
    problems = []
    _collect(contract, MODEL_CONTRACT_V2, "model-contract", problems)
    if not isinstance(contract, dict):
        return problems

    def rows(group):
        value = contract.get(group)
        return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []

    def text(value, path):
        if isinstance(value, str) and not value.strip():
            problems.append(f"{path}: expected nonempty text")

    symbols = rows("symbols")
    if isinstance(contract.get("symbols"), list) and not contract["symbols"]:
        problems.append("model-contract.symbols: declare at least one symbol with its physical object and uses")
    declared = {symbol_key(row.get("symbol")) for row in symbols if isinstance(row.get("symbol"), str)}

    for group, key, normalise in (("symbols", "symbol", symbol_key), ("parameters", "symbol", symbol_key),
                                  ("mechanisms", "id", str.strip), ("conserved_quantities", "name", str.strip)):
        seen = set()
        for row in rows(group):
            if not isinstance(row.get(key), str):
                continue
            identity = normalise(row[key])
            if identity in seen:
                problems.append(f"{group}: duplicate {key} {row[key]!r}; merge all uses in one declaration")
            seen.add(identity)

    for group, fields in (
            ("symbols", ("symbol", "unit", "object")),
            ("parameters", ("symbol", "unit", "source")),
            ("mechanisms", ("id", "cause", "effect_variable", "equation")),
            ("conserved_quantities", ("name", "check_name")),
            ("logical_claims", ("claim", "proof_ref")),
            ("limiting_cases", ("case", "expected"))):
        for index, row in enumerate(rows(group)):
            for field in fields:
                text(row.get(field), f"{group}[{index}].{field}")
    for row in symbols:
        name = row.get("symbol")
        uses = [use for use in row.get("uses", []) if isinstance(use, dict)] if isinstance(row.get("uses"), list) else []
        for use in uses:
            text(use.get("equation"), f"symbol {name} use equation")
            text(use.get("object"), f"symbol {name} use object")
        objects = {value.strip() for value in [row.get("object")] + [use.get("object") for use in uses]
                   if isinstance(value, str) and value.strip()}
        if len(objects) > 1 and not reasoned(row.get("same_object_justification")):
            warnings.append(f"symbol {name}: different object descriptions across declaration and uses "
                            f"(object {row.get('object')!r}; uses {uses}); supply same_object_justification "
                            "(at least three letters)")
    for index, row in enumerate(rows("mechanisms")):
        effect = row.get("effect_variable")
        if isinstance(effect, str) and effect.strip() and symbol_key(effect) not in declared:
            problems.append(f"mechanisms[{index}].effect_variable {effect!r} is not a declared symbol")
    for row in rows("parameters"):
        name = row.get("symbol")
        if isinstance(name, str) and name.strip() and symbol_key(name) not in declared:
            problems.append(f"parameter {name}: symbol is not declared in symbols")
        value, level = row.get("value"), row.get("source_level")
        reference = row.get("reference_magnitude")
        if value is None and "value" in row:
            if level != "unknown":
                problems.append(f"parameter {name}: value null requires source_level unknown")
                continue
            warnings.append(f"parameter {name}: value explicitly unknown; downstream results depend on an unmeasured input")
            if isinstance(reference, dict):
                warnings.append(f"parameter {name}: value unknown, magnitude check skipped")
            continue
        if level == "unknown":
            problems.append(f"parameter {name}: source_level unknown requires value null")
        if row.get("real_world_quantity") is True and reference is None:
            problems.append(f"parameter {name}: real-world quantity needs reference_magnitude")
        if not isinstance(reference, dict) or not _number(value):
            continue
        for field in ("unit", "source"):
            text(reference.get(field), f"parameter {name} reference_magnitude.{field}")
        if isinstance(reference.get("unit"), str) and isinstance(row.get("unit"), str) \
                and reference["unit"].strip() != row["unit"].strip():
            problems.append(f"parameter {name}: reference_magnitude unit must match parameter unit")
        bounds = reference.get("ratio_ok", list(DEFAULT_RATIO_OK))
        reference_value = reference.get("value")
        if not (isinstance(bounds, list) and len(bounds) == 2 and all(_number(b) for b in bounds)
                and _number(reference_value)):
            continue
        low, high = bounds
        justified = reasoned(row.get("magnitude_justification"))
        if not 0 < low <= high:
            problems.append(f"parameter {name}: ratio_ok lower bound must be positive and no greater than the upper bound")
            continue
        if (low < DEFAULT_RATIO_OK[0] or high > DEFAULT_RATIO_OK[1]) and not justified:
            problems.append(f"parameter {name}: ratio_ok [{low}, {high}] is wider than the default "
                            f"{list(DEFAULT_RATIO_OK)}; supply magnitude_justification")
        if reference_value == 0:
            problems.append(f"parameter {name}: reference_magnitude.value must be nonzero")
            continue
        try:
            ratio = value / reference_value
        except OverflowError:
            ratio = math.inf
        if not math.isfinite(ratio):
            problems.append(f"parameter {name}: value / reference_magnitude.value is too large to compute "
                            "as a finite ratio; rescale the unit")
        elif not low <= ratio <= high and not justified:
            problems.append(f"parameter {name}: magnitude ratio outside ratio_ok [{low}, {high}]; "
                            "supply magnitude_justification")
    for row in rows("conserved_quantities"):
        if isinstance(row.get("name"), str) and row.get("check_name") != "balance:" + row["name"]:
            problems.append(f"conserved quantity {row['name']}: check_name must be balance:{row['name']}")
    for row in rows("probability_combinations"):
        text(row.get("expression"), "probability combination expression")
        if row.get("independence") == "assumed" and not reasoned(row.get("justification")):
            problems.append(f"probability combination {row.get('expression')}: assumed independence needs "
                            "justification (at least three letters)")
    refutation = contract.get("cheapest_refutation")
    if isinstance(refutation, dict):
        text(refutation.get("result"), "cheapest_refutation.result")
    text(contract.get("information_time"), "information_time")
    return problems
