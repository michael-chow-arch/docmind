"""Heuristic chunk reranker. Biased toward academic/technical text. Not a research-grade component."""
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
    def __init__(self, max_chunks: int = 5):
        self.max_chunks = max_chunks
        # Heuristic: biased toward academic/technical text.
        self.quality_phrases = [
            "is defined as",
            "we propose",
            "in this work",
            "we present",
            "the model",
            "this paper",
            "we introduce",
            "is described as",
            "refers to",
            "means that",
        ]
        
        self.low_quality_patterns = [
            r"^\s*\[\d+\]",
            r"^\s*\d+\.\s*\d+",
        ]

    def aggregate(self, query: str, chunks: list[RetrievedChunk]) -> list[ScoredChunk]:
        if not chunks:
            return []
        normalized_chunks = self._normalize_scores(chunks)
        quality_scored = self._score_content_quality(normalized_chunks)
        redundancy_penalized = self._apply_redundancy_penalty(quality_scored)
        scored_chunks = self._calculate_answer_weight(redundancy_penalized)
        scored_chunks.sort(key=lambda x: x["answer_weight"], reverse=True)
        
        return scored_chunks[:self.max_chunks]

    def _normalize_scores(self, chunks: list[RetrievedChunk]) -> list[dict]:
        if not chunks:
            return []
        
        scores = [c["score"] for c in chunks]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            normalized = [0.5] * len(chunks)
        else:
            normalized = [
                (s - min_score) / (max_score - min_score)
                for s in scores
            ]
        
        result = []
        for chunk, norm_score in zip(chunks, normalized):
            chunk_copy = dict(chunk)
            chunk_copy["normalized_score"] = norm_score
            result.append(chunk_copy)
        
        return result

    def _score_content_quality(self, chunks: list[dict]) -> list[dict]:
        result = []
        
        for chunk in chunks:
            content = chunk.get("content", "").lower()
            content_length = len(content)
            
            quality_score = 0.5
            phrase_count = sum(1 for phrase in self.quality_phrases if phrase in content)
            if phrase_count > 0:
                quality_score += min(0.3, phrase_count * 0.1)
            
            if 100 <= content_length <= 2000:
                quality_score += 0.1
            elif content_length < 50:
                quality_score -= 0.2
            elif content_length > 5000:
                quality_score -= 0.1
            for pattern in self.low_quality_patterns:
                if re.search(pattern, content):
                    quality_score -= 0.2
                    break
            quality_score = max(0.0, min(1.0, quality_score))
            
            chunk_copy = dict(chunk)
            chunk_copy["quality_score"] = quality_score
            result.append(chunk_copy)
        
        return result

    def _apply_redundancy_penalty(self, chunks: list[dict]) -> list[dict]:
        result = []
        for i, chunk in enumerate(chunks):
            content_i = self._tokenize(chunk.get("content", ""))
            max_overlap = 0.0
            
            for j, other_chunk in enumerate(chunks):
                if i == j:
                    continue
                
                content_j = self._tokenize(other_chunk.get("content", ""))
                overlap = self._jaccard_similarity(content_i, content_j)
                max_overlap = max(max_overlap, overlap)
            
            if max_overlap > 0.5:
                redundancy_penalty = min(1.0, (max_overlap - 0.5) * 2)
            else:
                redundancy_penalty = 0.0
            
            chunk_copy = dict(chunk)
            chunk_copy["redundancy_penalty"] = redundancy_penalty
            result.append(chunk_copy)
        
        return result

    def _calculate_answer_weight(self, chunks: list[dict]) -> list[ScoredChunk]:
        result = []
        
        for chunk in chunks:
            normalized_score = chunk.get("normalized_score", 0.0)
            quality_score = chunk.get("quality_score", 0.0)
            redundancy_penalty = chunk.get("redundancy_penalty", 0.0)
            
            answer_weight = (
                0.6 * normalized_score
                + 0.3 * quality_score
                - 0.3 * redundancy_penalty
            )
            
            answer_weight = max(0.0, answer_weight)
            
            scored_chunk: ScoredChunk = {
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "page_number": chunk.get("page_number"),
                "score": chunk["score"],
                "answer_weight": answer_weight,
            }
            result.append(scored_chunk)
        
        return result

    def _tokenize(self, text: str) -> set[str]:
        tokens = re.findall(r'\b\w+\b', text.lower())
        return {t for t in tokens if len(t) > 2}

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
