"""向量存储 — 内存实现，支持余弦相似度搜索"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .chunker import Chunk


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float               # 相似度分数 [0, 1]


class VectorStore:
    """基于内存的向量存储 + 余弦相似度检索"""

    def __init__(self):
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def add(self, chunks: list[Chunk], vectors: list[list[float]]):
        """批量添加 Chunk 及对应向量"""
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)

    def clear(self):
        self._chunks.clear()
        self._vectors.clear()

    @property
    def size(self) -> int:
        return len(self._chunks)

    def search(
        self, query_vector: list[float], top_k: int = 10, threshold: float = 0.0
    ) -> list[ScoredChunk]:
        """余弦相似度搜索"""
        if not self._vectors:
            return []
        scored: list[ScoredChunk] = []
        for chunk, vec in zip(self._chunks, self._vectors):
            sim = self._cosine_similarity(query_vector, vec)
            if sim >= threshold:
                scored.append(ScoredChunk(chunk=chunk, score=sim))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def search_by_texts(self, texts: list[str]) -> list[ScoredChunk]:
        """按文本内容召回 Chunk"""
        matched: list[ScoredChunk] = []
        for chunk in self._chunks:
            for t in texts:
                if t in chunk.text:
                    matched.append(ScoredChunk(chunk=chunk, score=0.95))
                    break
        return matched

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            # 对齐到较长维度
            max_len = max(len(a), len(b))
            a = a + [0.0] * (max_len - len(a))
            b = b + [0.0] * (max_len - len(b))
        dot = sum(ai * bi for ai, bi in zip(a, b))
        na = math.sqrt(sum(ai * ai for ai in a)) or 1.0
        nb = math.sqrt(sum(bi * bi for bi in b)) or 1.0
        return dot / (na * nb)
