from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """Represents a single test case from the dataset."""

    id: str
    description: str | None = None
    query: str
    relevant_ids: set[int] = Field(
        ..., description="set of IDs that are considered Ground Truth"
    )
    retrieved_ids: list[int] = Field(
        ..., description="Ordered list of IDs returned by the system"
    )

    class Config:
        populate_by_name = True


class MetricResult(BaseModel):
    """Holds calculated metrics for a single case."""

    case_id: str
    precision_at_k: float
    recall_at_k: float
    f1_at_k: float
    mrr_at_k: float
    ndcg_at_k: float
