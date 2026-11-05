from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Source:
    id: str
    kind: str
    priority: str = "P1"
    raw: dict = field(default_factory=dict)

    def get(self, key, default=None):
        return self.raw.get(key, default)

    def __getattr__(self, name):  # convenience: src.repo
        try:
            return self.raw[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def load_sources(path: Path) -> list[Source]:
    data = tomllib.loads(path.read_text())
    out = []
    for key, value in data.get("sources", {}).items():
        out.append(Source(id=value.get("id", key), kind=value["kind"],
                          priority=value.get("priority", "P1"), raw=value))
    return out


def by_id(sources: list[Source], source_id: str) -> Source:
    for s in sources:
        if s.id == source_id:
            return s
    raise KeyError(f"unknown source: {source_id}")
