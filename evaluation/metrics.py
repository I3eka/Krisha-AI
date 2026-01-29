import math


def calculate_precision_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    """
    Calculates Precision based on the retrieved items.
    If the system returns fewer than k items (due to thresholding),
    we evaluate precision based on what was actually returned.

    P = (Relevant & Retrieved) / len(Retrieved)
    """
    if not retrieved:
        return 0.0

    top_k_retrieved = retrieved[:k]
    if not top_k_retrieved:
        return 0.0

    hits = sum(1 for doc_id in top_k_retrieved if doc_id in relevant)

    return hits / len(top_k_retrieved)


def calculate_recall_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    top_k_retrieved = retrieved[:k]
    hits = sum(1 for doc_id in top_k_retrieved if doc_id in relevant)
    return hits / len(relevant)


def calculate_f1_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    p = calculate_precision_at_k(retrieved, relevant, k)
    r = calculate_recall_at_k(retrieved, relevant, k)
    if (p + r) == 0:
        return 0.0
    return 2 * (p * r) / (p + r)


def calculate_mrr_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    top_k_retrieved = retrieved[:k]
    for rank, doc_id in enumerate(top_k_retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def calculate_ndcg_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    top_k_retrieved = retrieved[:k]
    if not top_k_retrieved:
        return 0.0

    dcg = 0.0
    for i, doc_id in enumerate(top_k_retrieved):
        rel = 1.0 if doc_id in relevant else 0.0
        dcg += rel / math.log2((i + 1) + 1)

    num_relevant_in_k = min(len(relevant), k)
    ideal_results = [1.0] * num_relevant_in_k
    idcg = 0.0
    for i, rel in enumerate(ideal_results):
        idcg += rel / math.log2((i + 1) + 1)

    if idcg == 0:
        return 0.0
    return dcg / idcg
