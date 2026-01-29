import faiss
import numpy as np
from openai import OpenAI
from rank_bm25 import BM25Okapi
from typing import List
from src.config.settings import settings
from src.models import Advert
from src.utils.text_processing import clean_text_content

OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


class VectorEngine:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.index = None
        self.adverts: List[Advert] = []
        self.bm25 = None

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generates embeddings using OpenAI API with batching.
        """
        if not texts:
            return np.array([])

        clean_texts = [t.replace("\n", " ") for t in texts]

        all_embeddings = []
        batch_size = 100

        for i in range(0, len(clean_texts), batch_size):
            batch = clean_texts[i : i + batch_size]
            try:
                response = self.client.embeddings.create(
                    input=batch, model=OPENAI_EMBEDDING_MODEL
                )
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                print(f"Error generating embeddings for batch {i}: {e}")
                all_embeddings.extend([[0.0] * EMBEDDING_DIMENSION] * len(batch))

        return np.array(all_embeddings, dtype="float32")

    def index_data(self, adverts: List[Advert]):
        """
        1. Cleans text.
        2. Generates OpenAI Embeddings.
        3. Creates FAISS index (Dense Retrieval).
        4. Creates BM25 index (Sparse Retrieval).
        """
        self.adverts = adverts
        if not adverts:
            return

        corpus = [clean_text_content(ad.full_text_content) for ad in adverts]

        embeddings = self._get_embeddings(corpus)

        faiss.normalize_L2(embeddings)

        self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self.index.add(embeddings)

        tokenized_corpus = [doc.split(" ") for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 20) -> List[Advert]:
        """
        Hybrid Search: Combines OpenAI Vector similarity with BM25 re-ranking.
        """
        if not self.adverts or self.index is None:
            return []

        query_embedding = self._get_embeddings([query])
        faiss.normalize_L2(query_embedding)

        search_k = min(100, len(self.adverts))
        D, Indexies = self.index.search(query_embedding, k=search_k)

        candidate_indices = Indexies[0]
        vector_scores = D[0]

        clean_query = clean_text_content(query)
        tokenized_query = clean_query.split(" ")

        all_bm25_scores = self.bm25.get_scores(tokenized_query)

        candidate_bm25_scores = []
        for idx in candidate_indices:
            if idx != -1:
                candidate_bm25_scores.append(all_bm25_scores[idx])
            else:
                candidate_bm25_scores.append(0.0)

        if candidate_bm25_scores:
            max_bm25 = max(candidate_bm25_scores)
            if max_bm25 > 0:
                candidate_bm25_scores = [s / max_bm25 for s in candidate_bm25_scores]

        alpha = 0.7
        hybrid_results = []

        for i, idx in enumerate(candidate_indices):
            if idx == -1:
                continue

            v_score = vector_scores[i]
            b_score = candidate_bm25_scores[i]

            final_score = (alpha * v_score) + ((1 - alpha) * b_score)

            hybrid_results.append({"advert": self.adverts[idx], "score": final_score})

        hybrid_results.sort(key=lambda x: x["score"], reverse=True)

        return [item["advert"] for item in hybrid_results[:top_k]]
