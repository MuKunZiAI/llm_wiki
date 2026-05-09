"""Wiki 知识图谱 — 检索引擎"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .store import WikiStore
from .schema import Concept, Source, Entity


@dataclass
class WikiHit:
    """Wiki 检索命中结果"""
    slug: str
    title: str
    kind: str               # concept / source / entity
    matched_by: str         # slug / alias / concept_ref
    match_text: str         # 具体命中关键词
    definition: str = ""
    key_points: list[str] = None
    contradictions: list[str] = None
    confidence: str = "low"
    source_slugs: list[str] = None
    evolution_log: list = None
    summary: str = ""

    def __post_init__(self):
        self.key_points = self.key_points or []
        self.contradictions = self.contradictions or []
        self.source_slugs = self.source_slugs or []
        self.evolution_log = self.evolution_log or []


@dataclass
class WikiResult:
    hits: list[WikiHit]
    coverage: str           # full / partial / blind
    blind_areas: list[str]  # 未覆盖的主题名称


class WikiSearcher:
    """在 Wiki 知识图谱中执行检索"""

    CHINESE_KW_PATTERN = re.compile(r"[一-鿿]{2,}")

    def __init__(self, store: WikiStore):
        self.store = store

    def search(self, query: str, top_k: int = 5) -> WikiResult:
        """全文匹配 + 别名匹配"""
        keywords = self._extract_keywords(query)
        hits: list[WikiHit] = []

        # 1) slug 精确匹配
        for kw_slug in self._to_slugs(keywords):
            c = self.store.get_concept(kw_slug)
            if c:
                hits.append(self._concept_to_hit(c, "slug", kw_slug))
            s = self.store.get_source(kw_slug)
            if s:
                hits.append(self._source_to_hit(s, "slug", kw_slug))
            e = self.store.get_entity(kw_slug)
            if e:
                hits.append(self._entity_to_hit(e, "slug", kw_slug))

        # 2) alias / title 模糊匹配
        for kw in keywords:
            c = self.store.find_concept_by_alias(kw)
            if c and not any(h.slug == c.slug for h in hits):
                hits.append(self._concept_to_hit(c, "alias", kw))
            e = self.store.find_entity_by_alias(kw) if hasattr(self.store, "find_entity_by_alias") else None
            if e and not any(h.slug == e.slug for h in hits):
                hits.append(self._entity_to_hit(e, "alias", kw))

        # 3) 全文搜索（摘要 / definition / key_points）
        for c in self.store.concepts.values():
            if any(h.slug == c.slug for h in hits):
                continue
            text = f"{c.title} {c.definition} {' '.join(c.key_points)}"
            if any(kw.lower() in text.lower() for kw in keywords):
                hits.append(self._concept_to_hit(c, "content", keywords[0]))

        for s in self.store.sources.values():
            if any(h.slug == s.slug for h in hits):
                continue
            text = f"{s.title} {s.summary} {' '.join(s.key_concepts)}"
            if any(kw.lower() in text.lower() for kw in keywords):
                hits.append(self._source_to_hit(s, "content", keywords[0]))

        # 去重 & Top-K
        seen: set[str] = set()
        unique: list[WikiHit] = []
        for h in hits:
            if h.slug not in seen:
                seen.add(h.slug)
                unique.append(h)
        hits = unique[:top_k]

        # 覆盖度判断
        coverage = "full" if len(hits) >= 2 else ("partial" if hits else "blind")
        blind_areas = [kw for kw in keywords if not any(
            kw.lower() in h.title.lower() or kw.lower() in " ".join(h.key_points).lower()
            for h in hits
        )]

        return WikiResult(hits=hits, coverage=coverage, blind_areas=blind_areas)

    def _extract_keywords(self, query: str) -> list[str]:
        """提取中英文关键词（含 N-gram 子串提升召回）"""
        kws: list[str] = []
        # 英文词
        en_words = re.findall(r"[a-zA-Z]{2,}", query)
        kws.extend(w.lower() for w in en_words)

        # 中文：提取所有连续中文段，生成 2~4 字 N-gram 子串
        for chinese_block in self.CHINESE_KW_PATTERN.findall(query):
            for n in (4, 3, 2):
                if len(chinese_block) >= n:
                    for i in range(len(chinese_block) - n + 1):
                        kws.append(chinese_block[i:i + n])

        # 兜底
        if not kws:
            kws.append(query)
        # 去重保序
        seen: set[str] = set()
        uniq: list[str] = []
        for k in kws:
            if k.lower() not in seen:
                seen.add(k.lower())
                uniq.append(k)
        return uniq

    def _to_slugs(self, keywords: list[str]) -> list[str]:
        return [kw.lower().replace(" ", "-") for kw in keywords]

    # ------------------------------------------------------------------
    # 转换辅助
    # ------------------------------------------------------------------

    def _concept_to_hit(self, c: Concept, matched_by: str, match_text: str) -> WikiHit:
        return WikiHit(
            slug=c.slug, title=c.title, kind="concept",
            matched_by=matched_by, match_text=match_text,
            definition=c.definition, key_points=c.key_points,
            contradictions=c.contradictions, confidence=c.confidence,
            source_slugs=c.source_slugs,
            evolution_log=c.evolution_log,
        )

    def _source_to_hit(self, s: Source, matched_by: str, match_text: str) -> WikiHit:
        return WikiHit(
            slug=s.slug, title=s.title, kind="source",
            matched_by=matched_by, match_text=match_text,
            summary=s.summary, key_points=s.key_concepts,
            contradictions=s.contradictions,
        )

    def _entity_to_hit(self, e: Entity, matched_by: str, match_text: str) -> WikiHit:
        return WikiHit(
            slug=e.slug, title=e.title, kind="entity",
            matched_by=matched_by, match_text=match_text,
            definition=e.description,
        )


# 补上 find_entity_by_alias 方法到 WikiStore
def _find_entity_by_alias(self: WikiStore, name: str) -> Entity | None:
    key = name.lower()
    for e in self.entities.values():
        if e.title == name or key in (a.lower() for a in e.aliases):
            return e
        if e.slug == key.replace(" ", "-"):
            return e
    return None


WikiStore.find_entity_by_alias = _find_entity_by_alias  # monkey-patch
