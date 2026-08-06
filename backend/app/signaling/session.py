import uuid


def call_id_for_pair(user_a: uuid.UUID, user_b: uuid.UUID) -> str:
    """Deterministic call id both matched clients derive independently.

    Sorting the pair means either side computes the same id from its own
    user_id + partner_id without a server round trip to agree on one.
    """
    first, second = sorted((user_a, user_b))
    return f"{first}:{second}"
