"""Wiki 知识图谱 — 数据模型"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class EvolutionEntry:
    """演化日志条目"""
    date: str               # YYYY-MM-DD
    summary: str            # 单句描述本次变化
    source_slug: str        # 来源 slug


@dataclass
class Concept:
    """概念卡片"""
    slug: str
    title: str              # 中文主名称
    aliases: list[str] = field(default_factory=list)
    definition: str = ""
    key_points: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    my_position: str = ""
    source_slugs: list[str] = field(default_factory=list)
    source_count: int = 0
    confidence: str = "low"       # low / medium / high
    evolution_log: list[EvolutionEntry] = field(default_factory=list)
    last_reviewed: str = ""       # YYYY-MM-DD


@dataclass
class Source:
    """来源档案"""
    slug: str
    title: str
    source_url: str = ""
    domain: str = ""
    canonical_source: str = ""
    raw_file: str = ""
    raw_sha256: str = ""
    summary: str = ""
    key_concepts: list[str] = field(default_factory=list)
    key_entities: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    possibly_outdated: bool = False
    last_verified: str = ""
    date: str = ""


@dataclass
class Entity:
    """实体卡片（人、组织、项目、工具等）"""
    slug: str
    title: str
    aliases: list[str] = field(default_factory=list)
    entity_type: str = ""        # person / project / tool / organization
    description: str = ""
    related_concepts: list[str] = field(default_factory=list)
    source_slugs: list[str] = field(default_factory=list)
    source_count: int = 0
    confidence: str = "low"
    last_reviewed: str = ""
