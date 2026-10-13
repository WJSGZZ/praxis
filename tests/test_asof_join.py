from datetime import datetime, timedelta, timezone
from importlib.metadata import version
import random

import pytest

from modeling.data_analysis import asof_join


def instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def oracle(queries, versions, on, decision_time, available_time, exact=False):
    keys = [on] if isinstance(on, str) else on
    mappings = []
    counts = {name: 0 for name in
              ("matched", "not_available", "unknown_availability", "ambiguous_latest")}
    for qi, query in enumerate(queries):
        identity = tuple((type(query[key]), query[key]) for key in keys)
        group = [(vi, version) for vi, version in enumerate(versions)
                 if tuple((type(version[key]), version[key]) for key in keys) == identity]
        decision = instant(query[decision_time])
        if any(version[available_time] is None for _, version in group):
            status, winner, available = "unknown_availability", None, None
        else:
            candidates = [(instant(version[available_time]), vi)
                          for vi, version in group
                          if (instant(version[available_time]) <= decision if exact
                              else instant(version[available_time]) < decision)]
            if not candidates:
                status, winner, available = "not_available", None, None
            else:
                latest = max(time for time, _ in candidates)
                ties = [vi for time, vi in candidates if time == latest]
                if len(ties) > 1:
                    status, winner, available = "ambiguous_latest", None, None
                else:
                    status, winner, available = "matched", ties[0], latest
        counts[status] += 1
        mappings.append({"query_index": qi, "status": status,
                         "matched_version_index": winner,
                         "decision_time_utc": decision.isoformat().replace("+00:00", "Z"),
                         "available_time_utc": available.isoformat().replace("+00:00", "Z") if available else None})
    return mappings, counts


def run(queries, versions, on="key", exact=False):
    return asof_join(queries, versions, on, "decision", "available",
                     allow_exact_matches=exact)


def test_unsorted_grouped_offset_and_exact_results_match_independent_oracle():
    queries = [
        {"key": "b", "decision": "2024-01-02T00:00:00Z"},
        {"key": "a", "decision": "2024-01-01T12:00:00+02:00"},
        {"key": "b", "decision": "2024-01-01T00:00:00Z"},
        {"key": "a", "decision": "2024-01-01T09:00:00Z"},
    ]
    versions = [
        {"key": "a", "available": "2024-01-01T07:00:00Z", "payload": "old"},
        {"key": "b", "available": "2024-01-01T00:00:00Z", "payload": "exact"},
        {"key": "a", "available": "2024-01-01T10:00:00+01:00", "payload": "same-instant"},
        {"key": "b", "available": "2024-01-01T12:00:00Z", "payload": "later"},
    ]
    for exact in (False, True):
        result = run(queries, versions, exact=exact)
        expected, counts = oracle(queries, versions, "key", "decision", "available", exact)
        assert result["mappings"] == expected
        assert result["counts"] == counts
        assert result["backend"] == {"library": "pandas", "version": version("pandas"), "direction": "backward"}
        assert result["status"] == ("audited" if exact else "mapped")
        assert "payload" not in str(result)


def test_large_integer_string_leading_zero_and_boolean_keys_keep_types():
    queries = [
        {"int_key": 2**53 + 1, "str_key": "001", "bool_key": True,
         "decision": "2024-01-02T00:00:00Z"},
    ]
    versions = [
        {"int_key": 2**53 + 1, "str_key": "001", "bool_key": True,
         "available": "2024-01-01T00:00:00Z"},
    ]
    result = asof_join(queries, versions, ["int_key", "str_key", "bool_key"],
                       "decision", "available")
    expected, _ = oracle(queries, versions, ["int_key", "str_key", "bool_key"],
                         "decision", "available")
    assert result["mappings"] == expected
    assert result["mappings"][0]["matched_version_index"] == 0


def test_unknown_availability_blocks_entire_group_and_missing_keys_do_not_match():
    queries = [{"key": "x", "decision": "2024-01-02T00:00:00Z"},
               {"key": "y", "decision": "2024-01-02T00:00:00Z"}]
    versions = [{"key": "x", "available": "2024-01-01T00:00:00Z"},
                {"key": "x", "available": None}]
    result = run(queries, versions)
    expected, counts = oracle(queries, versions, "key", "decision", "available")
    assert result["mappings"] == expected
    assert result["counts"] == counts
    assert result["mappings"][0]["status"] == "unknown_availability"
    assert result["mappings"][1]["status"] == "not_available"
    assert result["matched_fraction"] == 0
    assert result["status"] == "mapped"


def test_latest_tie_is_ambiguous_but_older_tie_is_overridden_by_newer_version():
    queries = [{"key": "x", "decision": "2024-01-03T00:00:00Z"},
               {"key": "y", "decision": "2024-01-03T00:00:00Z"}]
    versions = [
        {"key": "x", "available": "2024-01-02T00:00:00Z"},
        {"key": "x", "available": "2024-01-02T00:00:00Z"},
        {"key": "x", "available": "2024-01-02T12:00:00Z"},
        {"key": "y", "available": "2024-01-02T00:00:00Z"},
        {"key": "y", "available": "2024-01-02T00:00:00Z"},
    ]
    result = run(queries, versions)
    expected, counts = oracle(queries, versions, "key", "decision", "available")
    assert result["mappings"] == expected
    assert result["counts"] == counts
    assert result["mappings"][0]["matched_version_index"] == 2
    assert result["mappings"][1]["status"] == "ambiguous_latest"
    assert result["mappings"][1]["matched_version_index"] is None


def test_future_perturbation_cannot_change_earlier_decision_mapping():
    queries = [{"key": "x", "decision": "2024-01-02T00:00:00Z"}]
    versions = [{"key": "x", "available": "2024-01-01T00:00:00Z"}]
    before = run(queries, versions)["mappings"]
    changed = versions + [{"key": "x", "available": "2024-01-03T00:00:00Z"}]
    assert run(queries, changed)["mappings"] == before


def test_deterministic_randomized_groups_and_unsorted_times_match_oracle():
    rng = random.Random(73021)
    queries, versions = [], []
    epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for _ in range(80):
        minute = rng.randrange(0, 180)
        queries.append({"key": f"g{rng.randrange(7)}",
                       "decision": (epoch + timedelta(minutes=minute)).isoformat().replace("+00:00", "Z")})
    for _ in range(120):
        minute = rng.randrange(0, 180)
        versions.append({"key": f"g{rng.randrange(7)}",
                         "available": (epoch + timedelta(minutes=minute)).isoformat().replace("+00:00", "Z")})
    for exact in (False, True):
        result = run(queries, versions, exact=exact)
        expected, counts = oracle(queries, versions, "key", "decision", "available", exact)
        assert result["mappings"] == expected
        assert result["counts"] == counts


def test_naive_latest_join_counterexample_is_rejected_by_real_availability_time():
    # A latest-by-event-time shortcut would pick index 1 (event time is later),
    # even though it was announced after the query decision.
    queries = [{"key": "x", "decision": "2024-01-02T00:00:00Z"}]
    versions = [
        {"key": "x", "available": "2024-01-01T00:00:00Z", "event": "2024-01-01T00:00:00Z"},
        {"key": "x", "available": "2024-01-03T00:00:00Z", "event": "2024-01-10T00:00:00Z"},
        {"key": "x", "available": "2024-01-01T12:00:00Z", "event": "2024-01-08T00:00:00Z"},
    ]
    # A future event is still usable when its availability precedes the query;
    # the later-announced record remains ineligible despite its later event.
    result = asof_join(queries, versions, "key", "decision", "available")
    assert max(range(len(versions)), key=lambda i: instant(versions[i]["event"])) == 1
    assert result["mappings"][0]["matched_version_index"] == 2


def test_empty_input_and_empty_query_fraction():
    result = asof_join([], [], "key", "decision", "available")
    assert result["schema_version"] == 1
    assert result["mappings"] == []
    assert result["query_rows"] == result["version_rows"] == 0
    assert result["matched_fraction"] is None
    assert result["status"] == "audited"


def test_nanosecond_boundary_uses_integer_exactness():
    decision = [{"key": "x", "decision": "2024-01-01T00:00:00.000000000Z"},
                {"key": "x", "decision": "2024-01-01T00:00:00.000000002Z"}]
    versions = [
        {"key": "x", "available": "2024-01-01T00:00:00.000000001Z"},
        {"key": "x", "available": "2024-01-01T00:00:00.000000002Z"},
        {"key": "x", "available": "2024-01-01T00:00:00.000000003Z"},
    ]
    result = run(decision, versions)
    assert result["mappings"][0]["status"] == "not_available"
    assert result["mappings"][1]["matched_version_index"] == 0
    assert result["mappings"][1]["available_time_utc"] == "2024-01-01T00:00:00.000000001Z"
    exact = run(decision, versions, exact=True)
    assert exact["mappings"][1]["status"] == "matched"
    assert exact["mappings"][1]["matched_version_index"] == 1


@pytest.mark.parametrize("bad", [None, "2024-01-01", "2024-01-01T00:00:00",
                                  "2024-01-01t00:00:00Z", "2024-01-01T00:00:00.Z",
                                  "2024-02-30T00:00:00Z", "2024-01-01T00:00:00+24:00",
                                  "1600-01-01T00:00:00Z", "2300-01-01T00:00:00Z"])
def test_invalid_query_instants_are_rejected(bad):
    with pytest.raises(ValueError, match="decision time|expected|invalid|outside"):
        run([{"key": "x", "decision": bad}], [])


def test_input_contract_errors_are_clear():
    with pytest.raises(ValueError, match="unique nonempty"):
        run([], [], on=["key", "key"])
    with pytest.raises(ValueError, match="must not overlap"):
        asof_join([], [], "decision", "decision", "available")
    with pytest.raises(ValueError, match="mixed key types"):
        run([{"key": 1, "decision": "2024-01-02T00:00:00Z"},
             {"key": True, "decision": "2024-01-02T00:00:00Z"}], [])
    with pytest.raises(ValueError, match="incompatible"):
        run([{"key": 1, "decision": "2024-01-02T00:00:00Z"}],
            [{"key": True, "available": "2024-01-01T00:00:00Z"}])
    with pytest.raises(ValueError, match="null"):
        run([{"key": "x", "decision": None}], [])
    with pytest.raises(ValueError, match="Null query join keys"):
        run([{"key": None, "decision": "2024-01-02T00:00:00Z"}], [])
    with pytest.raises(ValueError, match="Null version join keys"):
        run([], [{"key": None, "available": "2024-01-01T00:00:00Z"}])
    with pytest.raises(ValueError, match="consistent column schema"):
        run([{"key": "x", "decision": "2024-01-02T00:00:00Z"}],
            [{"key": "x", "available": "2024-01-01T00:00:00Z"},
             {"key": "y", "available": "2024-01-01T00:00:00Z", "extra": 1}])
    with pytest.raises(ValueError, match="invalid Unicode"):
        asof_join([], [], "key", "bad\ud800name", "available")


def test_same_time_column_name_across_tables_is_allowed_and_inputs_are_unchanged():
    queries = [{"key": "x", "time": "2024-01-02T00:00:00Z"}]
    versions = [{"key": "x", "time": "2024-01-01T00:00:00Z", "payload": [1]}]
    query_before, version_before = [dict(row) for row in queries], [dict(row) for row in versions]
    result = asof_join(queries, versions, "key", "time", "time")
    assert result["mappings"][0]["status"] == "matched"
    assert queries == query_before
    assert versions == version_before


def test_missing_and_invalid_version_availability_fields_are_rejected():
    query = [{"key": "x", "decision": "2024-01-02T00:00:00Z"}]
    with pytest.raises(ValueError, match="missing time column"):
        asof_join(query, [{"key": "x"}], "key", "decision", "available")
    with pytest.raises(ValueError, match="explicit-timezone|expected YYYY"):
        run(query, [{"key": "x", "available": "2024-01-01T00:00:00"}])
    with pytest.raises(ValueError, match="invalid ISO-8601"):
        run([{"key": "x", "decision": "0001-01-01T00:00:00+23:00"}], [])


def test_asymmetric_input_row_limits_are_enforced():
    too_many_queries = [{"key": "x", "decision": "2024-01-02T00:00:00Z"}] * 20_001
    with pytest.raises(ValueError, match="20000 input-row"):
        run(too_many_queries, [])
    too_many_versions = [{"key": "x", "available": "2024-01-01T00:00:00Z"}] * 200_001
    with pytest.raises(ValueError, match="200000 input-row"):
        run([], too_many_versions)
