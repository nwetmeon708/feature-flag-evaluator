# Feature Flag Evaluation Engine

Implement a deterministic feature flag evaluation engine in Python.

## Starting point

The file `/app/flag_engine.py` contains this stub:

```python
def evaluate(config, flag_key, user):
    raise NotImplementedError
```

You must implement the `evaluate` function.

## Public interface

Implement:

```python
evaluate(config: dict, flag_key: str, user: dict) -> dict
```

The function must return a dictionary with exactly these keys:

```python
{
    "flag_key": str,
    "enabled": bool,
    "variant": str | None,
    "reason": str,
    "rule_id": str | None,
}
```

## Reason codes

Your implementation must use these reason strings exactly:

```text
INVALID_CONFIG
INVALID_USER
FLAG_NOT_FOUND
INVALID_FLAG
FLAG_DISABLED
RULE_MATCH
WEIGHTED_VARIANT
DEFAULT
```

## Evaluation order

The evaluator must use this order:

1. If `flag_key` is not a string, return `FLAG_NOT_FOUND`.
2. If `user` is not a dictionary, return `INVALID_USER`.
3. If `user["id"]` is missing, not a string, or empty, return `INVALID_USER`.
4. If `config` is not a dictionary, return `INVALID_CONFIG`.
5. If `config["flags"]` is missing or not a dictionary, return `INVALID_CONFIG`.
6. If `flag_key` is not present in `config["flags"]`, return `FLAG_NOT_FOUND`.
7. If the flag object is not a dictionary, return `INVALID_FLAG`.
8. If the flag state is not exactly `"enabled"`, return `FLAG_DISABLED`.
9. Validate the flag variants and default variant.
10. Evaluate rules in order.
11. If no rule returns a variant, evaluate weighted variants.
12. If no weighted variant is selected, return the default variant.

## Enabled result

For successful enabled evaluation, return:

```python
"enabled": True
```

This applies to:

```text
RULE_MATCH
WEIGHTED_VARIANT
DEFAULT
```

For failures and disabled flags, return:

```python
"enabled": False
```

## Flag structure

A flag is a dictionary:

```python
{
    "state": "enabled",
    "default_variant": "control",
    "variants": [
        {"name": "control", "weight": 50},
        {"name": "treatment", "weight": 50}
    ],
    "rules": [
        {
            "id": "beta-users",
            "conditions": [
                {
                    "attribute": "email",
                    "operator": "ends_with",
                    "value": "@beta.com"
                }
            ],
            "percentage": 100,
            "variant": "treatment"
        }
    ]
}
```

## Variant validation

A valid flag must have:

1. `variants` as a list.
2. At least one variant object with a non-empty string `name`.
3. `default_variant` as a non-empty string.
4. `default_variant` must exist in the variant names.

If any of these are invalid, return:

```text
INVALID_FLAG
```

Variant weights must be strict integers. Floats, booleans, strings, and negative weights are invalid. Invalid weights are treated as zero.

If all variant weights are zero, return the default variant with reason:

```text
DEFAULT
```

If at least one variant has positive weight, choose a weighted variant using stable hashing and return reason:

```text
WEIGHTED_VARIANT
```

## Rules

Rules are evaluated in array order.

The first matching rule with a valid variant wins.

A rule may contain:

```python
{
    "id": "rule-id",
    "conditions": [...],
    "segment_keys": [...],
    "percentage": 0-100,
    "variant": "variant-name"
}
```

A rule matches only if:

1. All direct conditions match.
2. All listed segments match.
3. The percentage check passes.
4. The rule variant exists in the flag variants.

If a rule has no conditions and no segment keys, its targeting matches every user.

If a rule has an invalid variant, skip that rule and continue.

If a rule has an invalid percentage, skip that rule and continue.

If a rule matches and its variant is valid, return:

```python
{
    "enabled": True,
    "variant": rule_variant,
    "reason": "RULE_MATCH",
    "rule_id": rule_id_if_string_else_None,
}
```

## Conditions

Each condition is a dictionary:

```python
{
    "attribute": "attribute_name",
    "operator": "operator_name",
    "value": some_value
}
```

All conditions inside a rule are combined with logical AND.

The supported operators are:

```text
equals
not_equals
in
not_in
contains
ends_with
gt
gte
lt
lte
exists
not_exists
```

For all operators except `exists` and `not_exists`, if the attribute is missing from the user, the condition evaluates to `False`.

### Operator behavior

- `equals`: user attribute equals value.
- `not_equals`: user attribute exists and does not equal value.
- `in`: value must be a list and user attribute must be in that list.
- `not_in`: value must be a list and user attribute must not be in that list.
- `contains`: user attribute must be a string and must contain the string value.
- `ends_with`: user attribute must be a string and must end with the string value.
- `gt`, `gte`, `lt`, `lte`: both user attribute and value must be numbers. Booleans are not numbers.
- `exists`: true if the attribute key exists in the user dictionary.
- `not_exists`: true if the attribute key does not exist in the user dictionary.

If a condition has a missing or non-string attribute, it evaluates to `False`, except where impossible for `exists` and `not_exists`.

## Segments

The top-level config may contain reusable segments:

```python
{
    "segments": {
        "internal": {
            "conditions": [
                {
                    "attribute": "company",
                    "operator": "equals",
                    "value": "Acme"
                }
            ]
        }
    }
}
```

A rule can reference segments:

```python
{
    "segment_keys": ["internal"]
}
```

A segment matches when all of its conditions match.

A rule with multiple segment keys matches only if every referenced segment matches.

If a referenced segment is missing or invalid, that segment does not match.

## Salt

The top-level config may contain:

```python
{
    "salt": "some-salt"
}
```

If `salt` is missing or not a string, use an empty string.

## Percentage bucketing

Rule percentage must be a strict integer from 0 to 100.

If `percentage` is omitted, the rule has no percentage restriction.

If percentage is present but invalid, skip the rule.

To determine whether a user is inside the percentage:

1. Build this key:

```text
{flag_key}:{user_id}:{salt}:{rule_id}
```

If the rule id is missing or not a string, use an empty string for `rule_id`.

2. Compute SHA-256 of that key.
3. Convert the hex digest to an integer.
4. Take modulo 100.
5. The user is included if the bucket is less than the percentage.

So:

```text
percentage = 0 matches nobody
percentage = 100 matches everybody
percentage = 25 matches buckets 0 through 24
```

## Weighted variant bucketing

To choose a weighted variant:

1. Consider only variants with valid positive integer weights.
2. Sum the valid positive weights into `total_weight`.
3. If `total_weight <= 0`, do not choose a weighted variant.
4. Build this key:

```text
{flag_key}:{user_id}:{salt}:variant
```

5. Compute SHA-256 of that key.
6. Convert the hex digest to an integer.
7. Take modulo `total_weight`.
8. Walk through the valid weighted variants in order, accumulating weights.
9. Return the first variant where the bucket is less than the accumulated weight.

## Invalid rules

Invalid rules must be skipped.

Examples of invalid rule data:

- rule is not a dictionary;
- conditions is not a list;
- segment_keys is not a list;
- percentage is not a strict integer between 0 and 100;
- rule variant is missing or not a valid variant name.

Invalid rules must not cause an error unless the whole flag is invalid according to the flag validation rules.

## Visible tests

You can run the public tests with:

```bash
cd /app
python -m pytest public_tests -q
```

## Done criteria

The task is complete when the public and hidden tests pass.
