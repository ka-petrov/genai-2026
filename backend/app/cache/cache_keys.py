"""
Redis key patterns and helpers.
Implementation: Part B.
"""

PREFIX = "v1"


def context_key(context_id: str) -> str:
    return f"{PREFIX}:ctx:{context_id}"


def region_key(region_hash: str) -> str:
    return f"{PREFIX}:region:{region_hash}"


def last_model_key(context_id: str) -> str:
    return f"{PREFIX}:chat:last_model:{context_id}"
