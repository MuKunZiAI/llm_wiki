"""RAG + Wiki 混合查询引擎 — 实现「Wiki 优先，RAG 兜底」决策逻辑"""

from __future__ import annotations

from dataclasses import dataclass

from ..wiki.store import WikiStore
from ..wiki.search import WikiSearcher, WikiHit, WikiResult
from ..rag.retriever import RAGRetriever, ScoredChunk
from ..rag.chunker import Chunk
from .annotator import SourceAnnotator, AnnotatedSegment, SourceLabel


@dataclass
class HybridResult:
    """混合查询最终结果"""
    question: str
    segments: list[AnnotatedSegment]
    wiki_coverage: str         # full / partial / blind
    wiki_hits: list[WikiHit]
    rag_hits: list[ScoredChunk]
    merge_strategy: str         # wiki_only / rag_fallback / wiki_skeleton_rag_supplement / none
    formatted_answer: str = ""

    def __post_init__(self):
        self.formatted_answer = SourceAnnotator().format_answer(self.segments)


class HybridEngine:
    """
    RAG + Wiki 混合查询引擎。

    决策逻辑（三层分流）：
      Step 1 — Wiki 图谱检索（concepts / sources / entities）
      Step 2 — RAG 向量检索（始终执行，全量扫描）
      Step 3 — 结果合并：
        - Wiki + RAG 都命中 → Wiki 骨架 + RAG 补充
        - 仅 RAG 命中      → 直接回答，标注「!! 未经 Wiki 结构化验证」
        - 都未命中          → 诚实回答「未找到相关信息」
    """

    def __init__(self, wiki_store: WikiStore, rag: RAGRetriever):
        self.wiki_searcher = WikiSearcher(wiki_store)
        self.rag = rag
        self.annotator = SourceAnnotator()

    # ------------------------------------------------------------------
    # 主查询入口
    # ------------------------------------------------------------------

    def query(self, question: str) -> HybridResult:
        """执行混合查询"""
        # Step 1: Wiki 图谱检索
        wiki_result = self.wiki_searcher.search(question)

        # Step 2: RAG 向量检索（始终执行）
        rag_hits = self.rag.search(question)

        # Step 3: 结果合并决策
        segments, strategy = self._merge(question, wiki_result, rag_hits)

        return HybridResult(
            question=question,
            segments=segments,
            wiki_coverage=wiki_result.coverage,
            wiki_hits=wiki_result.hits,
            rag_hits=rag_hits,
            merge_strategy=strategy,
        )

    # ------------------------------------------------------------------
    # 合并逻辑
    # ------------------------------------------------------------------

    def _merge(
        self,
        question: str,
        wiki_result: WikiResult,
        rag_hits: list[ScoredChunk],
    ) -> tuple[list[AnnotatedSegment], str]:
        has_concept = self._has_concept_hit(wiki_result)
        has_any_wiki = bool(wiki_result.hits)
        has_rag = bool(rag_hits)

        # — 情况 1：Wiki 有概念 + RAG 命中 → Wiki 骨架 + RAG 补充
        if has_concept and has_rag:
            return self._merge_wiki_skeleton_rag_supplement(wiki_result, rag_hits), \
                   "wiki_skeleton_rag_supplement"

        # — 情况 2：Wiki 有概念 + RAG 未命中
        if has_concept and not has_rag:
            return self._merge_wiki_only(wiki_result), "wiki_only"

        # — 情况 3：Wiki 无概念（盲区/仅来源页）+ RAG 命中 → RAG 兜底
        if not has_concept and has_rag:
            return self._merge_rag_fallback(rag_hits), "rag_fallback"

        # — 情况 4：Wiki 无概念 + RAG 也命中 → 仍以 RAG 兜底（Wiki 只有弱信号）
        if has_any_wiki and has_rag:
            return self._merge_rag_fallback(rag_hits), "rag_fallback"

        # — 情况 5：都未命中
        return [
            self.annotator.annotate_rag_segment(
                "未找到相关信息，建议将相关文档纳入 Wiki 摄入队列。",
                source_file="",
            )
        ], "none"

    @staticmethod
    def _has_concept_hit(wiki_result: WikiResult) -> bool:
        return any(h.kind == "concept" for h in wiki_result.hits)

    # ------------------------------------------------------------------
    # 合并策略实现
    # ------------------------------------------------------------------

    def _merge_wiki_skeleton_rag_supplement(
        self, wiki: WikiResult, rag: list[ScoredChunk]
    ) -> list[AnnotatedSegment]:
        """Wiki 提供结构化骨架，RAG 补充最新细节"""
        segments: list[AnnotatedSegment] = []

        for hit in wiki.hits:
            # Wiki 骨架：definition + key_points
            seg_text = self._build_wiki_segment_text(hit)
            segments.append(self.annotator.annotate_wiki_segment(
                seg_text, source_slug=hit.slug, confidence=hit.confidence,
            ))

            # 矛盾检测：Wiki 中有记录的分歧
            for contradiction in hit.contradictions:
                segments.append(self.annotator.annotate_contradiction(
                    contradiction, source_slug=hit.slug,
                ))

        # RAG 补充：过滤掉已被 Wiki 覆盖的内容
        wiki_texts = self._collect_wiki_texts(wiki)
        new_rag_chunks = [
            r for r in rag
            if not self._is_covered_by_wiki(r.chunk.text, wiki_texts)
        ]
        for rc in new_rag_chunks[:3]:  # 最多补充 3 个 RAG 片段
            segments.append(self.annotator.annotate_rag_segment(
                rc.chunk.text[:200], source_file=rc.chunk.source_file,
            ))

        return segments

    def _merge_wiki_only(self, wiki: WikiResult) -> list[AnnotatedSegment]:
        """仅 Wiki 命中 — 直接以 Wiki 构建答案"""
        segments: list[AnnotatedSegment] = []
        for hit in wiki.hits:
            seg_text = self._build_wiki_segment_text(hit)
            segments.append(self.annotator.annotate_wiki_segment(
                seg_text, source_slug=hit.slug, confidence=hit.confidence,
            ))
            for contradiction in hit.contradictions:
                segments.append(self.annotator.annotate_contradiction(
                    contradiction, source_slug=hit.slug,
                ))
        return segments

    def _merge_rag_fallback(self, rag: list[ScoredChunk]) -> list[AnnotatedSegment]:
        """仅 RAG 命中 — 标注盲区警告"""
        segments: list[AnnotatedSegment] = []

        # 前置警告
        segments.append(self.annotator.annotate_rag_segment(
            "!! Wiki 盲区：该主题尚未被摄入知识图谱，以下内容来自文档原始片段，未经结构化验证。",
            source_file="",
        ))

        for rc in rag[:3]:
            segments.append(self.annotator.annotate_rag_segment(
                rc.chunk.text[:300], source_file=rc.chunk.source_file,
            ))

        # 尾部建议
        segments.append(self.annotator.annotate_rag_segment(
            "[建议]：若此问题被多次查询，系统将标记该主题进入 INGEST 队列。",
            source_file="",
        ))

        return segments

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _build_wiki_segment_text(self, hit: WikiHit) -> str:
        """将 WikiHit 构建为可读的段落文本"""
        parts: list[str] = [hit.title]

        if hit.definition:
            parts.append(hit.definition)
        if hit.summary:
            parts.append(hit.summary)
        if hit.key_points:
            parts.append("要点：" + "；".join(hit.key_points))
        if hit.evolution_log:
            evo_lines = [
                f"  [{e.date}] {e.summary}" if hasattr(e, 'date') else f"  - {e}"
                for e in hit.evolution_log[:5]
            ]
            parts.append("演化日志：\n" + "\n".join(evo_lines))

        return "\n".join(parts)

    def _collect_wiki_texts(self, wiki: WikiResult) -> set[str]:
        """收集 Wiki 已覆盖的文本片段，用于去重"""
        texts: set[str] = set()
        for hit in wiki.hits:
            texts.add(hit.title)
            if hit.definition:
                texts.update(hit.definition.split())
        return texts

    @staticmethod
    def _is_covered_by_wiki(chunk_text: str, wiki_texts: set[str]) -> bool:
        """简单判断：Chunk 是否与 Wiki 内容高度重叠"""
        chunk_words = set(chunk_text.split())
        for wt in wiki_texts:
            wt_words = set(wt.split())
            if len(wt_words) > 2 and len(chunk_words & wt_words) / max(len(wt_words), 1) > 0.5:
                return True
        return False
