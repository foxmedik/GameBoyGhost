from __future__ import annotations

import fnmatch
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx

from .config import Source
from .model import Document
from .net import Fetcher, FetchError, github_headers
from .normalize import decode, html_to_markdown
from .store import BANNED_EXT

LOCK_PATH = Path(__file__).resolve().parents[2] / "sources.lock.json"


def load_lock() -> dict:
    if LOCK_PATH.exists():
        return json.loads(LOCK_PATH.read_text())
    return {}


def save_lock(lock: dict):
    LOCK_PATH.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def _banned(path: str) -> bool:
    return Path(path).suffix.lower() in BANNED_EXT


def _glob_re(pattern: str):
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif pattern.startswith("**", i):
            out += ".*"; i += 2
        elif pattern[i] == "*":
            out += "[^/]*"; i += 1
        elif pattern[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(pattern[i]); i += 1
    return re.compile("^" + out + "$")


def _matches(path: str, include: list[str], exclude: list[str]) -> bool:
    if _banned(path):
        return False
    if any(_glob_re(pat).match(path) for pat in exclude):
        return False
    return any(_glob_re(pat).match(path) for pat in include)


def _detect_license(text: str) -> str:
    t = text.lower()
    if "cc0" in t or "creative commons zero" in t:
        return "CC0-1.0"
    if "attribution-sharealike 4.0" in t or "by-sa 4.0" in t:
        return "CC-BY-SA-4.0"
    if "attribution-sharealike 3.0" in t or "by-sa 3.0" in t:
        return "CC-BY-SA-3.0"
    if "attribution 4.0" in t:
        return "CC-BY-4.0"
    if "gnu general public license" in t and "version 3" in t:
        return "GPL-3.0"
    if "gnu general public license" in t and "version 2" in t:
        return "GPL-2.0"
    if "apache license" in t:
        return "Apache-2.0"
    if "mit license" in t or "permission is hereby granted, free of charge" in t:
        return "MIT"
    if "mozilla public license" in t:
        return "MPL-2.0"
    if "bsd" in t and "redistribution" in t:
        return "BSD"
    return "unknown"


# ---------------------------------------------------------------- GitHub

def _github_commit(fetcher: Fetcher, repo: str, ref: str) -> tuple[str, str]:
    """Return (sha, default_branch). Pins the resolved SHA in sources.lock.json."""
    lock = load_lock()
    key = repo
    if key in lock and lock[key].get("sha"):
        return lock[key]["sha"], lock[key].get("branch", "main")

    headers = github_headers()
    info = fetcher.get(f"https://api.github.com/repos/{repo}", headers=headers).json()
    branch = info.get("default_branch", "main")
    target = branch if ref in (None, "auto", "") else ref
    commit = fetcher.get(f"https://api.github.com/repos/{repo}/commits/{target}", headers=headers).json()
    sha = commit["sha"]
    lock[key] = {"repo": repo, "ref": target, "sha": sha, "branch": branch,
                 "pinned_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    save_lock(lock)
    return sha, branch


def _github_license(fetcher: Fetcher, repo: str, sha: str, tree: list[dict]) -> str:
    for item in tree:
        name = Path(item["path"]).name.upper()
        if item.get("type") == "blob" and name.startswith(("LICENSE", "COPYING", "LICENCE")):
            try:
                r = fetcher.get(f"https://raw.githubusercontent.com/{repo}/{sha}/{item['path']}")
                return _detect_license(decode(r.content))
            except Exception:
                continue
    return "unknown"


def fetch_github_raw(src: Source, limit: int | None = None) -> list[Document]:
    fetcher = Fetcher(rate_limit_rps=src.get("rate_limit_rps", 1))
    try:
        repo = src.repo
        sha, branch = _github_commit(fetcher, repo, src.get("ref", "auto"))
        headers = github_headers()
        tree_resp = fetcher.get(
            f"https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1", headers=headers)
        tree = tree_resp.json().get("tree", [])
        license_id = _github_license(fetcher, repo, sha, tree)
        include = src.get("include", ["**/*.md"])
        exclude = src.get("exclude", [])
        paths = [i["path"] for i in tree if i.get("type") == "blob" and _matches(i["path"], include, exclude)]
        paths.sort()
        if limit:
            paths = paths[:limit]

        docs = []
        for path in paths:
            url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
            r = fetcher.get(url)
            text = decode(r.content)
            if len(text.strip()) < 40:
                continue
            title = next((l.lstrip("# ").strip() for l in text.splitlines()
                          if l.lstrip().startswith("# ")), Path(path).stem)
            ext = Path(path).suffix.lstrip(".") or "txt"
            docs.append(Document(
                source_id=src.id, kind=src.kind,
                url=f"https://github.com/{repo}/blob/{sha}/{path}",
                canonical_url=f"https://github.com/{repo}/blob/{sha}/{path}",
                title=title, text=text, raw=r.content, ext=ext,
                license=license_id, revision=sha,
                content_type="text/markdown" if ext == "md" else "text/plain",
                extra={"repo": repo, "path": path},
            ))
        return docs
    finally:
        fetcher.close()


# ---------------------------------------------------------------- MediaWiki

def parse_mediawiki(data: dict, api: str, page: str, mode: str,
                    source_id: str, kind: str, license_id: str) -> Document:
    if "error" in data:
        raise FetchError(200, api, f"mediawiki error: {data['error'].get('info')}")
    parse = data["parse"]
    revid = str(parse.get("revid", ""))
    if mode == "wikitext":
        text = parse.get("wikitext", "")
        ctype = "text/x-wiki"
    else:
        html = parse.get("text", "")
        text, _ = html_to_markdown(html, api)
        ctype = "text/markdown"
    title = parse.get("title", page)
    host = urlparse(api).netloc
    canonical = f"https://{host}/wiki/{quote(title.replace(' ', '_'))}"
    raw = json.dumps(data, indent=2).encode()
    return Document(
        source_id=source_id, kind=kind, url=canonical, canonical_url=canonical,
        title=title, text=f"# {title}\n\n{text}", raw=raw, ext="json",
        license=license_id, revision=revid, content_type=ctype,
        extra={"api": api, "page": page},
    )


def fetch_mediawiki(src: Source) -> list[Document]:
    fetcher = Fetcher(rate_limit_rps=src.get("rate_limit_rps", 1))
    try:
        api = src.api
        params = {
            "action": "parse", "page": src.page, "format": "json",
            "formatversion": "2", "redirects": "1",
            "prop": "wikitext|revid" if src.get("mode", "wikitext") == "wikitext" else "text|revid",
        }
        r = fetcher.get(api, params=params)
        return [parse_mediawiki(r.json(), api, src.page,
                                src.get("mode", "wikitext"), src.id, src.kind,
                                src.get("license", "unknown"))]
    finally:
        fetcher.close()


# ---------------------------------------------------------------- arXiv

ATOM = "{http://www.w3.org/2005/Atom}"


def fetch_arxiv(src: Source) -> list[Document]:
    fetcher = Fetcher(rate_limit_rps=src.get("rate_limit_rps", 1))
    try:
        arxiv_id = src.arxiv_id
        r = fetcher.get("https://export.arxiv.org/api/query", params={"id_list": arxiv_id})
        root = ET.fromstring(r.content)
        entry = root.find(f"{ATOM}entry")
        if entry is None:
            raise FetchError(200, "arxiv", "no entry")
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
        published = entry.findtext(f"{ATOM}published")
        updated = entry.findtext(f"{ATOM}updated")
        authors = [a.findtext(f"{ATOM}name") for a in entry.findall(f"{ATOM}author")]
        link = entry.findtext(f"{ATOM}id") or f"https://arxiv.org/abs/{arxiv_id}"
        rev = "v1"
        m = re.search(r"v(\d+)$", link)
        if m:
            rev = "v" + m.group(1)
        doi = None
        for node in entry.findall("{http://arxiv.org/schemas/atom}doi"):
            doi = node.text
        text = (
            f"# {title}\n\n"
            f"**Authors:** {', '.join(a for a in authors if a)}\n\n"
            f"**Published:** {published}  \n**Updated:** {updated}  \n"
            f"**arXiv:** {link}  \n**DOI:** {doi or 'none'}\n\n"
            f"## Abstract\n\n{summary}\n"
        )
        return [Document(
            source_id=src.id, kind=src.kind, url=link, canonical_url=link,
            title=title, text=text, raw=r.content, ext="xml",
            author=", ".join(a for a in authors if a), published_at=published,
            license=src.get("license", "arxiv-metadata-only"), revision=rev,
            content_type="application/atom+xml", extra={"doi": doi, "arxiv_id": arxiv_id},
        )]
    finally:
        fetcher.close()


# ---------------------------------------------------------------- Speedrun.com

def fetch_speedrun(src: Source) -> list[Document]:
    fetcher = Fetcher(rate_limit_rps=src.get("rate_limit_rps", 1))
    try:
        game_id = src.game_id
        base = "https://www.speedrun.com/api/v1"
        docs = []

        game = fetcher.get(f"{base}/games/{game_id}", params={"embed": "categories.variables"}).json()
        docs.append(_json_doc(src, f"{base}/games/{game_id}", f"Speedrun.com game {game_id}", game,
                              f"https://www.speedrun.com/{game_id}"))

        cats = ((game.get("data") or {}).get("categories") or {}).get("data") or []
        for cat in cats[: int(src.get("categories_limit", 12))]:
            cid, cname = cat["id"], cat["name"]
            lb_url = f"{base}/leaderboards/{game_id}/category/{cid}"
            try:
                lb = fetcher.get(lb_url, params={"top": 10}).json()
            except Exception:
                continue
            docs.append(_json_doc(src, lb_url, f"Leaderboard: {cname}", lb,
                                  f"https://www.speedrun.com/{game_id}?x={cid}"))

        runs_url = f"{base}/runs"
        runs = fetcher.get(runs_url, params={"game": game_id, "orderby": "date",
                                             "direction": "desc", "max": int(src.get("runs_limit", 20))}).json()
        docs.append(_json_doc(src, runs_url, "Recent runs", runs,
                              f"https://www.speedrun.com/{game_id}/run"))
        return docs
    finally:
        fetcher.close()


def _json_doc(src: Source, url: str, title: str, payload: dict, canonical: str) -> Document:
    text = f"# {title}\n\n```json\n{json.dumps(payload, indent=2)[:200000]}\n```\n"
    return Document(
        source_id=src.id, kind=src.kind, url=url, canonical_url=canonical,
        title=title, text=text, raw=json.dumps(payload).encode(), ext="json",
        license=src.get("license", "unknown"), revision="",
        content_type="application/json",
    )


# ---------------------------------------------------------------- HTML articles

def fetch_html_article(src: Source) -> list[Document]:
    fetcher = Fetcher(rate_limit_rps=src.get("rate_limit_rps", 1))
    try:
        url = src.url
        r = fetcher.get(url)
        text, meta = html_to_markdown(r.text, url)
        if len(text.strip()) < 80:
            raise FetchError(r.status_code, url, "empty extraction")
        title = meta.get("title") or (r.text.split("<title>")[1].split("</title>")[0] if "<title>" in r.text else url)
        canonical = meta.get("canonical_url") or url
        return [Document(
            source_id=src.id, kind=src.kind, url=url, canonical_url=canonical,
            title=title.strip(), text=text, raw=r.content, ext="html",
            author=meta.get("author"), published_at=meta.get("published_at"),
            license=src.get("license", "unknown"), revision="",
            content_type="text/html",
        )]
    finally:
        fetcher.close()


# ---------------------------------------------------------------- Reddit (P2)

def fetch_reddit(src: Source) -> list[Document]:
    import os
    cid = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        raise FetchError(0, "reddit", "skipped: no REDDIT_CLIENT_ID/SECRET")
    fetcher = Fetcher(rate_limit_rps=src.get("rate_limit_rps", 1))
    try:
        auth = httpx.post("https://www.reddit.com/api/v1/access_token",
                          auth=(cid, secret), data={"grant_type": "client_credentials"},
                          headers={"User-Agent": "gbg-corpus/0.1"}, timeout=30)
        if auth.status_code != 200:
            raise FetchError(auth.status_code, "reddit", "oauth failed")
        token = auth.json()["access_token"]
        sub = src.subreddit
        r = fetcher.get(f"https://oauth.reddit.com/r/{sub}/top",
                        params={"t": "month", "limit": 100},
                        headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        docs = []
        for child in data.get("data", {}).get("children", []):
            p = child["data"]
            text = f"# {p.get('title','')}\n\n{p.get('selftext','')}\n\n[permalink]({p.get('permalink','')})"
            docs.append(Document(
                source_id=src.id, kind=src.kind,
                url="https://www.reddit.com" + p.get("permalink", ""),
                canonical_url="https://www.reddit.com" + p.get("permalink", ""),
                title=p.get("title", ""), text=text, raw=json.dumps(p).encode(), ext="json",
                author=p.get("author"), published_at=datetime.fromtimestamp(
                    p.get("created_utc", 0), timezone.utc).isoformat(),
                license="reddit-api-terms", revision="", content_type="application/json",
            ))
        return docs
    finally:
        fetcher.close()
