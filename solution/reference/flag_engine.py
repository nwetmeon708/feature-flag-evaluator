"""Reference implementation for the feature flag evaluation engine."""

import hashlib
from typing import Any, Dict, Optional


def _result(
    flag_key: Any,
    enabled: bool = False,
    variant: Optional[str] = None,
    reason: str = "ERROR",
    rule_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "flag_key": flag_key,
        "enabled": enabled,
        "variant": variant,
        "reason": reason,
        "rule_id": rule_id,
    }


def _is_strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return _is_strict_int(value) or isinstance(value, float)


def _hash_bucket(key: str, total: int) -> int:
    if total <= 0:
        return 0

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest, 16) % total


def _condition_matches(condition: Any, user: Dict[str, Any]) -> bool:
    if not isinstance(condition, dict):
        return False

    attribute = condition.get("attribute")
    operator = condition.get("operator")

    if not isinstance(attribute, str):
        return False

    if operator == "exists":
        return attribute in user

    if operator == "not_exists":
        return attribute not in user

    if attribute not in user:
        return False

    actual = user[attribute]
    value = condition.get("value")

    if operator == "equals":
        return actual == value

    if operator == "not_equals":
        return actual != value

    if operator == "in":
        return isinstance(value, list) and actual in value

    if operator == "not_in":
        return isinstance(value, list) and actual not in value

    if operator == "contains":
        return isinstance(actual, str) and isinstance(value, str) and value in actual

    if operator == "ends_with":
        return isinstance(actual, str) and isinstance(value, str) and actual.endswith(value)

    if operator in {"gt", "gte", "lt", "lte"}:
        if not _is_number(actual) or not _is_number(value):
            return False

        if operator == "gt":
            return actual > value
        if operator == "gte":
            return actual >= value
        if operator == "lt":
            return actual < value
        if operator == "lte":
            return actual <= value

    return False


def _segment_matches(segment: Any, user: Dict[str, Any]) -> bool:
    if not isinstance(segment, dict):
        return False

    conditions = segment.get("conditions", [])
    if not isinstance(conditions, list):
        return False

    for condition in conditions:
        if not _condition_matches(condition, user):
            return False

    return True


def _rule_targeting_matches(
    rule: Dict[str, Any],
    segments: Dict[str, Any],
    user: Dict[str, Any],
) -> bool:
    conditions = rule.get("conditions", [])
    if not isinstance(conditions, list):
        return False

    for condition in conditions:
        if not _condition_matches(condition, user):
            return False

    segment_keys = rule.get("segment_keys", [])
    if not isinstance(segment_keys, list):
        return False

    for segment_key in segment_keys:
        if not isinstance(segment_key, str):
            return False

        segment = segments.get(segment_key)
        if not _segment_matches(segment, user):
            return False

    return True


def _in_percentage(
    flag_key: str,
    user_id: str,
    salt: str,
    rule_id: str,
    percentage: int,
) -> bool:
    if percentage <= 0:
        return False

    if percentage >= 100:
        return True

    key = f"{flag_key}:{user_id}:{salt}:{rule_id}"
    return _hash_bucket(key, 100) < percentage


def _choose_weighted_variant(
    flag_key: str,
    user_id: str,
    salt: str,
    variants: list,
) -> Optional[str]:
    entries = []
    total_weight = 0

    for variant in variants:
        if not isinstance(variant, dict):
            continue

        name = variant.get("name")
        weight = variant.get("weight", 0)

        if not isinstance(name, str) or not name:
            continue

        if not _is_strict_int(weight):
            continue

        if weight <= 0:
            continue

        entries.append((name, weight))
        total_weight += weight

    if total_weight <= 0:
        return None

    key = f"{flag_key}:{user_id}:{salt}:variant"
    bucket = _hash_bucket(key, total_weight)

    cumulative = 0
    for name, weight in entries:
        cumulative += weight
        if bucket < cumulative:
            return name

    return entries[-1][0] if entries else None


def evaluate(config: Any, flag_key: Any, user: Any) -> Dict[str, Any]:
    if not isinstance(flag_key, str):
        return _result(flag_key, reason="FLAG_NOT_FOUND")

    if not isinstance(user, dict):
        return _result(flag_key, reason="INVALID_USER")

    user_id = user.get("id")
    if not isinstance(user_id, str) or not user_id:
        return _result(flag_key, reason="INVALID_USER")

    if not isinstance(config, dict):
        return _result(flag_key, reason="INVALID_CONFIG")

    flags = config.get("flags")
    if not isinstance(flags, dict):
        return _result(flag_key, reason="INVALID_CONFIG")

    if flag_key not in flags:
        return _result(flag_key, reason="FLAG_NOT_FOUND")

    flag = flags[flag_key]
    if not isinstance(flag, dict):
        return _result(flag_key, reason="INVALID_FLAG")

    if flag.get("state") != "enabled":
        return _result(flag_key, reason="FLAG_DISABLED")

    variants = flag.get("variants")
    if not isinstance(variants, list):
        return _result(flag_key, reason="INVALID_FLAG")

    variant_names = set()
    for variant in variants:
        if (
            isinstance(variant, dict)
            and isinstance(variant.get("name"), str)
            and variant.get("name")
        ):
            variant_names.add(variant.get("name"))

    if not variant_names:
        return _result(flag_key, reason="INVALID_FLAG")

    default_variant = flag.get("default_variant")
    if not isinstance(default_variant, str) or default_variant not in variant_names:
        return _result(flag_key, reason="INVALID_FLAG")

    salt = config.get("salt", "")
    if not isinstance(salt, str):
        salt = ""

    segments = config.get("segments", {})
    if not isinstance(segments, dict):
        segments = {}

    rules = flag.get("rules", [])
    if not isinstance(rules, list):
        rules = []

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        if not _rule_targeting_matches(rule, segments, user):
            continue

        if "percentage" in rule:
            percentage = rule.get("percentage")

            if not _is_strict_int(percentage):
                continue

            if percentage < 0 or percentage > 100:
                continue

            raw_rule_id = rule.get("id")
            rule_id_for_hash = raw_rule_id if isinstance(raw_rule_id, str) else ""

            if not _in_percentage(
                flag_key,
                user_id,
                salt,
                rule_id_for_hash,
                percentage,
            ):
                continue

        variant = rule.get("variant")
        if isinstance(variant, str) and variant in variant_names:
            rule_id = rule.get("id")
            return _result(
                flag_key,
                enabled=True,
                variant=variant,
                reason="RULE_MATCH",
                rule_id=rule_id if isinstance(rule_id, str) else None,
            )

    weighted_variant = _choose_weighted_variant(
        flag_key,
        user_id,
        salt,
        variants,
    )

    if weighted_variant is not None:
        return _result(
            flag_key,
            enabled=True,
            variant=weighted_variant,
            reason="WEIGHTED_VARIANT",
        )

    return _result(
        flag_key,
        enabled=True,
        variant=default_variant,
        reason="DEFAULT",
    )
