"""Wiki 知识图谱 — 存储层（JSON 文件持久化）"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Concept, Source, Entity, EvolutionEntry


class WikiStore:
    """管理 concept / source / entity 的 CRUD"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self._concepts: dict[str, Concept] = {}
        self._sources: dict[str, Source] = {}
        self._entities: dict[str, Entity] = {}
        self._load_all()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _load_all(self):
        self._concepts = self._load_dir("concepts", Concept)
        self._sources = self._load_dir("sources", Source)
        self._entities = self._load_dir("entities", Entity)

    def _load_dir(self, sub: str, cls: type):
        items: dict[str, object] = {}
        subdir = self.data_dir / sub
        if not subdir.exists():
            subdir.mkdir(parents=True, exist_ok=True)
        for f in sorted(subdir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            if cls is Concept:
                data["evolution_log"] = [EvolutionEntry(**e) for e in data.get("evolution_log", [])]
            items[data["slug"]] = cls(**data)
        return items

    def _save(self, obj: Concept | Source | Entity) -> None:
        sub = {Concept: "concepts", Source: "sources", Entity: "entities"}[type(obj)]
        out_dir = self.data_dir / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        data = _dataclass_to_dict(obj)
        (out_dir / f"{obj.slug}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Concept
    # ------------------------------------------------------------------

    @property
    def concepts(self) -> dict[str, Concept]:
        return self._concepts

    def get_concept(self, slug: str) -> Concept | None:
        return self._concepts.get(slug)

    def find_concept_by_alias(self, name: str) -> Concept | None:
        key = name.lower()
        for c in self._concepts.values():
            if c.title == name or key in (a.lower() for a in c.aliases):
                return c
            if c.slug == key.replace(" ", "-"):
                return c
        return None

    def add_concept(self, c: Concept):
        self._concepts[c.slug] = c
        self._save(c)

    # ------------------------------------------------------------------
    # Source
    # ------------------------------------------------------------------

    @property
    def sources(self) -> dict[str, Source]:
        return self._sources

    def get_source(self, slug: str) -> Source | None:
        return self._sources.get(slug)

    def add_source(self, s: Source):
        self._sources[s.slug] = s
        self._save(s)

    # ------------------------------------------------------------------
    # Entity
    # ------------------------------------------------------------------

    @property
    def entities(self) -> dict[str, Entity]:
        return self._entities

    def get_entity(self, slug: str) -> Entity | None:
        return self._entities.get(slug)

    def add_entity(self, e: Entity):
        self._entities[e.slug] = e
        self._save(e)


def _dataclass_to_dict(obj) -> dict:
    """将 dataclass 转为可 JSON 序列化的 dict"""
    import dataclasses
    result = {}
    for f in dataclasses.fields(obj):
        val = getattr(obj, f.name)
        if isinstance(val, list):
            val = [
                dataclasses.asdict(v) if dataclasses.is_dataclass(v) else v
                for v in val
            ]
        result[f.name] = val
    return result
