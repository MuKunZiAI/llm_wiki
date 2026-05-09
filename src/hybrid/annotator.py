"""来源标注器 — 为答案段落标注来源和置信度"""

from __future__ import annotations

from dataclasses import dataclass


class SourceLabel:
    """来源标签常量"""
    WIKI = "Wiki"                      # 来源于 Wiki 知识图谱
    RAG_UNVERIFIED = "RAG"             # 来源于 RAG，未经结构化验证
    RAG_VERIFIED = "RAG+Wiki"          # RAG 结果通过 Wiki 交叉验证
    UNKNOWN = "unknown"


@dataclass
class AnnotatedSegment:
    """带标注的答案段落"""
    text: str
    source_label: str           # Wiki / RAG / RAG+Wiki / unknown
    source_slug: str = ""       # 具体来源页面 slug
    confidence: str = "low"     # low / medium / high
    is_contradiction: bool = False
    contradiction_note: str = ""


class SourceAnnotator:
    """为混合答案的每个段落标注来源和置信度"""

    def annotate_wiki_segment(
        self, text: str, source_slug: str = "", confidence: str = "medium"
    ) -> AnnotatedSegment:
        """标注一段来自 Wiki 的答案"""
        return AnnotatedSegment(
            text=text,
            source_label=SourceLabel.WIKI,
            source_slug=source_slug,
            confidence=confidence,
        )

    def annotate_rag_segment(
        self, text: str, source_file: str = "", verified: bool = False
    ) -> AnnotatedSegment:
        """标注一段来自 RAG 的答案"""
        label = SourceLabel.RAG_VERIFIED if verified else SourceLabel.RAG_UNVERIFIED
        return AnnotatedSegment(
            text=text,
            source_label=label,
            source_slug=source_file,
            confidence="low",
        )

    def annotate_contradiction(
        self, text: str, source_slug: str = ""
    ) -> AnnotatedSegment:
        """标注矛盾信息"""
        return AnnotatedSegment(
            text=text,
            source_label=SourceLabel.WIKI,
            source_slug=source_slug,
            confidence="low",
            is_contradiction=True,
            contradiction_note="分歧状态",
        )

    def format_answer(self, segments: list[AnnotatedSegment]) -> str:
        """将带标注的段落格式化为最终答案字符串"""
        lines: list[str] = []
        for seg in segments:
            if seg.is_contradiction:
                prefix = f"  → 分歧 [{seg.source_label}, {seg.source_slug}]"
            elif seg.source_label == SourceLabel.WIKI:
                prefix = f"  → [{seg.source_label}, confidence: {seg.confidence}]"
            elif seg.source_label == SourceLabel.RAG_UNVERIFIED:
                prefix = f"  → [{seg.source_label}, !! 未经 Wiki 验证]"
            elif seg.source_label == SourceLabel.RAG_VERIFIED:
                prefix = f"  → [{seg.source_label}, 交叉验证通过]"
            else:
                prefix = f"  → [{seg.source_label}]"
            lines.append(f"{prefix}\n     {seg.text}")
        return "\n".join(lines)
