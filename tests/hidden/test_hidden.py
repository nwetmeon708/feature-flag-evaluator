import sys

sys.path.insert(0, "/app")

from flag_engine import evaluate


def make_config(flag, segments=None):
    return {
        "salt": "hidden-salt",
        "segments": segments or {},
        "flags": {
            "flag": flag,
        },
    }


def enabled_flag(**overrides):
    flag = {
        "state": "enabled",
        "default_variant": "control",
        "variants": [
            {"name": "control", "weight": 100},
        ],
        "rules": [],
    }
    flag.update(overrides)
    return flag


def test_invalid_config_not_dict():
    result = evaluate([], "flag", {"id": "user"})
    assert result["enabled"] is False
    assert result["reason"] == "INVALID_CONFIG"


def test_invalid_config_missing_flags():
    result = evaluate({}, "flag", {"id": "user"})
    assert result["enabled"] is False
    assert result["reason"] == "INVALID_CONFIG"


def test_invalid_user_none():
    config = make_config(enabled_flag())
    result = evaluate(config, "flag", None)
    assert result["enabled"] is False
    assert result["reason"] == "INVALID_USER"


def test_invalid_user_missing_id():
    config = make_config(enabled_flag())
    result = evaluate(config, "flag", {})
    assert result["enabled"] is False
    assert result["reason"] == "INVALID_USER"


def test_invalid_user_empty_id():
    config = make_config(enabled_flag())
    result = evaluate(config, "flag", {"id": ""})
    assert result["enabled"] is False
    assert result["reason"] == "INVALID_USER"


def test_flag_not_found():
    config = make_config(enabled_flag())
    result = evaluate(config, "missing", {"id": "user"})
    assert result["enabled"] is False
    assert result["reason"] == "FLAG_NOT_FOUND"


def test_disabled_flag():
    flag = enabled_flag(state="disabled")
    config = make_config(flag)
    result = evaluate(config, "flag", {"id": "user"})
    assert result["enabled"] is False
    assert result["reason"] == "FLAG_DISABLED"
    assert result["variant"] is None


def test_invalid_flag_no_variants():
    flag = enabled_flag(variants=[])
    config = make_config(flag)
    result = evaluate(config, "flag", {"id": "user"})
    assert result["enabled"] is False
    assert result["reason"] == "INVALID_FLAG"


def test_invalid_flag_bad_default():
    flag = enabled_flag(
        default_variant="missing",
        variants=[{"name": "control", "weight": 100}],
    )
    config = make_config(flag)
    result = evaluate(config, "flag", {"id": "user"})
    assert result["enabled"] is False
    assert result["reason"] == "INVALID_FLAG"


def test_weighted_variant_full_weight():
    flag = enabled_flag(
        variants=[{"name": "control", "weight": 100}],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["enabled"] is True
    assert result["variant"] == "control"
    assert result["reason"] == "WEIGHTED_VARIANT"
    assert result["rule_id"] is None


def test_weighted_zero_weights_returns_default():
    flag = enabled_flag(
        variants=[{"name": "control", "weight": 0}],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["enabled"] is True
    assert result["variant"] == "control"
    assert result["reason"] == "DEFAULT"
    assert result["rule_id"] is None


def test_rule_match_condition_equals():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "us-only",
                "conditions": [
                    {
                        "attribute": "country",
                        "operator": "equals",
                        "value": "US",
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "country": "US"})

    assert result["enabled"] is True
    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"
    assert result["rule_id"] == "us-only"


def test_rule_order_first_wins():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "a", "weight": 0},
            {"name": "b", "weight": 0},
        ],
        rules=[
            {"id": "first", "variant": "a"},
            {"id": "second", "variant": "b"},
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "a"
    assert result["rule_id"] == "first"
    assert result["reason"] == "RULE_MATCH"


def test_missing_attribute_is_false_for_equals():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "us-only",
                "conditions": [
                    {
                        "attribute": "country",
                        "operator": "equals",
                        "value": "US",
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "control"
    assert result["reason"] == "DEFAULT"


def test_not_equals_present_value():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "not-uk",
                "conditions": [
                    {
                        "attribute": "country",
                        "operator": "not_equals",
                        "value": "UK",
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "country": "US"})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_not_equals_missing_attribute_is_false():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "not-uk",
                "conditions": [
                    {
                        "attribute": "country",
                        "operator": "not_equals",
                        "value": "UK",
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "control"
    assert result["reason"] == "DEFAULT"


def test_exists_operator():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "has-email",
                "conditions": [
                    {
                        "attribute": "email",
                        "operator": "exists",
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "email": ""})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_not_exists_operator():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "no-email",
                "conditions": [
                    {
                        "attribute": "email",
                        "operator": "not_exists",
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_in_operator():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "north-america",
                "conditions": [
                    {
                        "attribute": "country",
                        "operator": "in",
                        "value": ["US", "CA"],
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "country": "CA"})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_not_in_operator():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "not-uk",
                "conditions": [
                    {
                        "attribute": "country",
                        "operator": "not_in",
                        "value": ["UK"],
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "country": "US"})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_not_in_missing_attribute_is_false():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "not-uk",
                "conditions": [
                    {
                        "attribute": "country",
                        "operator": "not_in",
                        "value": ["UK"],
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "control"
    assert result["reason"] == "DEFAULT"


def test_contains_operator():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "corp-email",
                "conditions": [
                    {
                        "attribute": "email",
                        "operator": "contains",
                        "value": "@corp.com",
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "email": "a@corp.com"})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_ends_with_operator():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "beta-email",
                "conditions": [
                    {
                        "attribute": "email",
                        "operator": "ends_with",
                        "value": "@beta.com",
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "email": "a@beta.com"})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_gt_operator():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "adults",
                "conditions": [
                    {
                        "attribute": "age",
                        "operator": "gt",
                        "value": 18,
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "age": 21})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_gt_operator_with_string_value_is_false():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "adults",
                "conditions": [
                    {
                        "attribute": "age",
                        "operator": "gt",
                        "value": 18,
                    }
                ],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user", "age": "21"})

    assert result["variant"] == "control"
    assert result["reason"] == "DEFAULT"


def test_segment_match():
    segments = {
        "internal": {
            "conditions": [
                {
                    "attribute": "company",
                    "operator": "equals",
                    "value": "Acme",
                }
            ]
        }
    }

    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "internal-rule",
                "segment_keys": ["internal"],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag, segments=segments)

    result = evaluate(config, "flag", {"id": "user", "company": "Acme"})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_missing_segment_does_not_match():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "missing-segment-rule",
                "segment_keys": ["does-not-exist"],
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "control"
    assert result["reason"] == "DEFAULT"


def test_rule_percentage_100_matches_everybody():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "full-rollout",
                "percentage": 100,
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"


def test_rule_percentage_0_matches_nobody():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "zero-rollout",
                "percentage": 0,
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "control"
    assert result["reason"] == "DEFAULT"


def test_invalid_rule_variant_is_skipped():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "bad-rule",
                "variant": "missing-variant",
            },
            {
                "id": "good-rule",
                "variant": "treatment",
            },
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "treatment"
    assert result["rule_id"] == "good-rule"
    assert result["reason"] == "RULE_MATCH"


def test_invalid_percentage_is_skipped():
    flag = enabled_flag(
        variants=[
            {"name": "control", "weight": 0},
            {"name": "treatment", "weight": 0},
        ],
        rules=[
            {
                "id": "bad-percentage",
                "percentage": "100",
                "variant": "treatment",
            }
        ],
    )
    config = make_config(flag)

    result = evaluate(config, "flag", {"id": "user"})

    assert result["variant"] == "control"
    assert result["reason"] == "DEFAULT"


def test_result_shape_and_stability():
    config = make_config(enabled_flag())

    first = evaluate(config, "flag", {"id": "user"})
    second = evaluate(config, "flag", {"id": "user"})

    assert first == second
    assert set(first.keys()) == {
        "flag_key",
        "enabled",
        "variant",
        "reason",
        "rule_id",
    }
