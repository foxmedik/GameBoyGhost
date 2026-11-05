from __future__ import annotations

import sqlite3
from pathlib import Path

from .normalize import chunk_markdown

SCHEMA = """
DROP TABLE IF EXISTS docs_fts;
DROP TABLE IF EXISTS docs;
CREATE TABLE docs(
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  url TEXT,
  title TEXT,
  heading_path TEXT,
  chunk_index INTEGER,
  sha256 TEXT,
  license TEXT,
  text TEXT NOT NULL
);
CREATE VIRTUAL TABLE docs_fts USING fts5(
  title, text, heading_path,
  source_id UNINDEXED,
  content='docs', content_rowid='id'
);
"""


def build_index(store, db_path: Path | None = None) -> int:
    db_path = db_path or (store.root / "index.sqlite")
    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA)
    n = 0
    for row in store.all_rows():
        norm = store.root / row["normalized_path"]
        if not norm.exists():
            continue
        text = norm.read_text(errors="replace")
        if text.startswith("---"):
            parts = text.split("---", 2)
            text = parts[2] if len(parts) == 3 else text
        for i, chunk in enumerate(chunk_markdown(text)):
            db.execute(
                "INSERT INTO docs(source_id,kind,url,title,heading_path,chunk_index,sha256,license,text)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (row["source_id"], row["kind"], row["url"], row["title"],
                 " > ".join(chunk["heading_path"]), i, row["sha256"],
                 row["license"], chunk["text"]))
            n += 1
    db.execute("INSERT INTO docs_fts(rowid,title,text,heading_path,source_id) "
               "SELECT id,title,text,heading_path,source_id FROM docs")
    db.commit()
    db.close()
    return n
