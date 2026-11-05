from __future__ import annotations

import re
from dataclasses import dataclass

import trafilatura
import yaml
from selectolax.lexbor import LexborHTMLParser as HTMLParser


def decode(raw: bytes, content_type: str = "") -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def html_to_markdown(html: str, url: str = "") -> tuple[str, dict]:
    """Extract main text as Markdown. Returns (text, metadata)."""
    meta: dict = {}
    text = ""
    try:
        extracted = trafilatura.extract(
            html, url=url, output_format="markdown", include_links=True,
            include_formatting=True, include_comments=False, favor_precision=True,
            with_metadata=True,
        )
        if extracted:
            text = extracted
            md = trafilatura.metadata.extract_metadata(html, default_url=url)
            if md:
                meta = {
                    "title": md.title, "author": md.author,
                    "published_at": md.date, "canonical_url": md.url or url,
                }
    except Exception:
        pass
    if len(text.strip()) < 80:
        tree = HTMLParser(html)
        for node in tree.css("script,style,nav,footer,header,noscript"):
            node.decompose()
        body = tree.css_first("body") or tree.root
        text = body.text(separator="\n", strip=True) if body else ""
        meta.setdefault("title", (tree.css_first("title").text() if tree.css_first("title") else ""))
    return text.strip(), meta


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def split_sections(markdown: str) -> list[tuple[list[str], str]]:
    """Split at headings; each section carries its heading path."""
    lines = markdown.splitlines()
    sections: list[tuple[list[str], list[str]]] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []

    def flush():
        if any(l.strip() for l in buf) or stack:
            sections.append(([t for _, t in stack], list(buf)))

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            buf = [line]
        else:
            buf.append(line)
    flush()
    return [(path, "\n".join(body).strip()) for path, body in sections]


def chunk_markdown(markdown: str, target_tokens: int = 1000) -> list[dict]:
    """One chunk per heading section; split oversized sections by paragraph."""
    chunks: list[dict] = []
    for path, body in split_sections(markdown):
        body = body.strip()
        if not body:
            continue
        tokens = max(1, len(body) // 4)
        if tokens <= int(target_tokens * 1.2):
            chunks.append({"heading_path": path, "text": body})
            continue
        buf: list[str] = []
        used = 0
        for para in body.split("\n\n"):
            pt = max(1, len(para) // 4)
            if buf and used + pt > target_tokens:
                chunks.append({"heading_path": path, "text": "\n\n".join(buf)})
                buf, used = [], 0
            buf.append(para); used += pt
        if buf:
            chunks.append({"heading_path": path, "text": "\n\n".join(buf)})
    return chunks


def front_matter(data: dict) -> str:
    return "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n"


def slugify(value: str, max_len: int = 120) -> str:
    value = re.sub(r"[^\w\-]+", "-", value, flags=re.UNICODE).strip("-").lower()
    return (value or "document")[:max_len]
