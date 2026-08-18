from flag_engine import evaluate


def test_missing_flag():
    config = {"flags": {}}
    result = evaluate(config, "missing-flag", {"id": "user-1"})

    assert result["flag_key"] == "missing-flag"
    assert result["enabled"] is False
    assert result["variant"] is None
    assert result["reason"] == "FLAG_NOT_FOUND"
    assert result["rule_id"] is None


def test_disabled_flag():
    config = {
        "flags": {
            "disabled-flag": {
                "state": "disabled",
                "default_variant": "control",
                "variants": [{"name": "control", "weight": 100}],
                "rules": [],
            }
        }
    }

    result = evaluate(config, "disabled-flag", {"id": "user-1"})

    assert result["enabled"] is False
    assert result["reason"] == "FLAG_DISABLED"
    assert result["variant"] is None
    assert result["rule_id"] is None


def test_weighted_variant_with_full_weight():
    config = {
        "salt": "public-salt",
        "flags": {
            "simple-flag": {
                "state": "enabled",
                "default_variant": "control",
                "variants": [
                    {"name": "control", "weight": 100},
                ],
                "rules": [],
            }
        },
    }

    result = evaluate(config, "simple-flag", {"id": "user-1"})

    assert result["enabled"] is True
    assert result["variant"] == "control"
    assert result["reason"] == "WEIGHTED_VARIANT"
    assert result["rule_id"] is None


def test_rule_match():
    config = {
        "salt": "public-salt",
        "flags": {
            "rule-flag": {
                "state": "enabled",
                "default_variant": "control",
                "variants": [
                    {"name": "control", "weight": 0},
                    {"name": "treatment", "weight": 0},
                ],
                "rules": [
                    {
                        "id": "beta",
                        "conditions": [
                            {
                                "attribute": "beta",
                                "operator": "equals",
                                "value": True,
                            }
                        ],
                        "variant": "treatment",
                    }
                ],
            }
        },
    }

    result = evaluate(config, "rule-flag", {"id": "user-1", "beta": True})

    assert result["enabled"] is True
    assert result["variant"] == "treatment"
    assert result["reason"] == "RULE_MATCH"
    assert result["rule_id"] == "beta"
