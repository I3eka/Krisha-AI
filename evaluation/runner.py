import asyncio
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import load_eval_dataset
from metrics import (
    calculate_f1_at_k,
    calculate_mrr_at_k,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
)

from models import MetricResult
from src.models.models import Advert
from src.services.reranker import JinaReranker
from src.services.vector_store import VectorEngine


def load_snapshot(file_path: str) -> list[Advert]:
    """Loads the mock database snapshot into Advert objects."""
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    adverts = []
    for item in data:
        ad = Advert(
            id=item["id"],
            title=item["title"],
            price=item["price"],
            address=item["address"],
            full_text_content=item["full_text_content"],
            url=f"http://mock/{item['id']}",
        )
        adverts.append(ad)
    return adverts


async def run_pipeline_evaluation(
    dataset_path: str,
    snapshot_path: str,
    top_k_retrieval: int = 50,
    top_k_rerank: int = 5,
):
    print(f"Loading Test Cases from: {dataset_path}")
    cases = load_eval_dataset(dataset_path)

    print(f"Loading DB Snapshot from: {snapshot_path}")
    real_adverts = load_snapshot(snapshot_path)
    print(f"Loaded {len(real_adverts)} adverts from snapshot.")

    print("Indexing data in Vector Engine...")
    engine = VectorEngine()
    engine.index_data(real_adverts)

    reranker = JinaReranker()
    results: list[MetricResult] = []

    print(
        "\n--- Starting Pipeline Evaluation ("
        f"K_Retrieve={top_k_retrieval}, K_Rerank={top_k_rerank}"
        ") ---\n"
    )

    for case in cases:
        augmented_query = case.query
        candidates = engine.search(augmented_query, top_k=top_k_retrieval)
        ranked_candidates = []
        if candidates:
            try:
                ranked_candidates = await reranker.rerank(
                    case.query, candidates, top_k=top_k_rerank, threshold=0.35
                )
            except Exception as e:
                print(f"Reranker failed for case {case.id}: {e}")
                ranked_candidates = candidates[:top_k_rerank]

        actual_retrieved_ids = [ad.id for ad in ranked_candidates]
        p_k = calculate_precision_at_k(
            actual_retrieved_ids, case.relevant_ids, top_k_rerank
        )
        r_k = calculate_recall_at_k(
            actual_retrieved_ids, case.relevant_ids, top_k_rerank
        )
        f1_k = calculate_f1_at_k(actual_retrieved_ids, case.relevant_ids, top_k_rerank)
        mrr_k = calculate_mrr_at_k(
            actual_retrieved_ids, case.relevant_ids, top_k_rerank
        )
        ndcg_k = calculate_ndcg_at_k(
            actual_retrieved_ids, case.relevant_ids, top_k_rerank
        )

        result = MetricResult(
            case_id=case.id,
            precision_at_k=p_k,
            recall_at_k=r_k,
            f1_at_k=f1_k,
            mrr_at_k=mrr_k,
            ndcg_at_k=ndcg_k,
        )
        results.append(result)

        print(f"ID: {case.id}")
        print(f"  Query: '{case.query}'")
        print(f"  Found ({len(actual_retrieved_ids)}): {actual_retrieved_ids}")
        print(f"  Target: {case.relevant_ids}")
        print(f"  P: {p_k:.2f} | R: {r_k:.2f} | NDCG: {ndcg_k:.2f}")
        print("-" * 50)

    if results:
        avg_precision = mean(r.precision_at_k for r in results)
        avg_recall = mean(r.recall_at_k for r in results)
        avg_f1 = mean(r.f1_at_k for r in results)
        avg_mrr = mean(r.mrr_at_k for r in results)
        avg_ndcg = mean(r.ndcg_at_k for r in results)

        print("\n=== Final Aggregate Metrics ===")
        print(f"Total Cases:       {len(cases)}")
        print(f"Average Precision: {avg_precision:.4f}")
        print(f"Average Recall:    {avg_recall:.4f}")
        print(f"Average F1 Score:  {avg_f1:.4f}")
        print(f"Average MRR:       {avg_mrr:.4f}")
        print(f"Average NDCG:      {avg_ndcg:.4f}")
        print("===============================")


if __name__ == "__main__":
    DATASET_PATH = "datasets/synthetic_rag_data.json"
    SNAPSHOT_PATH = "datasets/snapshot.json"

    asyncio.run(run_pipeline_evaluation(DATASET_PATH, SNAPSHOT_PATH))
