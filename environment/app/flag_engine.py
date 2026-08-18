"""Stub module for the feature flag evaluation engine."""


def evaluate(config, flag_key, user):
    """
    Evaluate a feature flag for a user.

    Args:
        config: Feature flag configuration dictionary.
        flag_key: Flag key to evaluate.
        user: User dictionary. Must contain a non-empty string "id".

    Returns:
        A dictionary with keys:
        - flag_key
        - enabled
        - variant
        - reason
        - rule_id
    """
    raise NotImplementedError("Implement evaluate")
