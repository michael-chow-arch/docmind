"""Simple chunk reranker used before answer generation."""

from __future__ import annotations

import re
from typing import TypedDict


class RetrievedChunk(TypedDict):
    chunk_id: int
    content: str
    page_number: int | None
    score: float


class ScoredChunk(TypedDict):
    chunk_id: int
    content: str
    page_number: int | None
    score: float
    answer_weight: float


class AnswerChunkAggregator:
    def __init__(self, max_chunks: int = 5, similarity_threshold: float = 0.75):
        self.max_chunks = max_chunks
        self.similarity_threshold = similarity_threshold

    def aggregate(self, query: str, chunks: list[RetrievedChunk]) -> list[ScoredChunk]:
        if not chunks:
            return []

        normalized_chunks = self._normalize_scores(chunks)
        query_tokens = self._tokenize(query)

        scored_chunks: list[ScoredChunk] = []
        for chunk in normalized_chunks:
            content = chunk["content"]
            content_tokens = self._tokenize(content)

            overlap_score = self._overlap_ratio(query_tokens, content_tokens)
            length_score = self._length_score(content)
            structure_penalty = self._structure_penalty(content)

            answer_weight = (
                0.70 * chunk["normalized_score"]
                + 0.20 * overlap_score
                + 0.10 * length_score
                - structure_penalty
            )
            answer_weight = max(0.0, answer_weight)

            scored_chunks.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "content": chunk["content"],
                    "page_number": chunk.get("page_number"),
                    "score": chunk["score"],
                    "answer_weight": answer_weight,
                }
            )

        scored_chunks.sort(key=lambda x: x["answer_weight"], reverse=True)
        deduplicated = self._deduplicate(scored_chunks)

        return deduplicated[: self.max_chunks]

    def _normalize_scores(self, chunks: list[RetrievedChunk]) -> list[dict]:
        scores = [c["score"] for c in chunks]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            normalized_scores = [0.5] * len(chunks)
        else:
            normalized_scores = [
                (score - min_score) / (max_score - min_score)
                for score in scores
            ]

        result: list[dict] = []
        for chunk, normalized_score in zip(chunks, normalized_scores):
            item = dict(chunk)
            item["normalized_score"] = normalized_score
            result.append(item)

        return result

    def _length_score(self, content: str) -> float:
        length = len(content.strip())

        if 120 <= length <= 1200:
            return 1.0
        if 60 <= length < 120 or 1200 < length <= 2500:
            return 0.6
        if 20 <= length < 60:
            return 0.2
        return 0.0

    def _structure_penalty(self, content: str) -> float:
        text = content.strip()

        if not text:
            return 0.3

        if re.match(r"^\s*(\[\d+\]|\d+\.\d+)", text):
            return 0.10

        if len(text) < 30:
            return 0.15

        return 0.0

    def _deduplicate(self, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
        selected: list[ScoredChunk] = []

        for candidate in chunks:
            candidate_tokens = self._tokenize(candidate["content"])
            is_duplicate = False

            for existing in selected:
                existing_tokens = self._tokenize(existing["content"])
                similarity = self._jaccard_similarity(candidate_tokens, existing_tokens)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                selected.append(candidate)

        return selected

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"\b\w+\b", text.lower())
            if len(token) > 1
        }

    def _overlap_ratio(self, query_tokens: set[str], content_tokens: set[str]) -> float:
        if not query_tokens or not content_tokens:
            return 0.0

        overlap = len(query_tokens & content_tokens)
        return overlap / len(query_tokens)

    def _jaccard_similarity(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0

        union = left | right
        if not union:
            return 0.0

        return len(left & right) / len(union)