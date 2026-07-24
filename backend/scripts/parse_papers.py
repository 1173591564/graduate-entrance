"""批量解析论文正文并上传到后端。

流程：拉取论文列表 → 下载 PDF → 提取 arXiv 编号 → 抓取 ar5iv HTML 转成
带 LaTeX 公式的分节 Markdown（跳过图表）→ 无 arXiv 版本的用 PDF 文本兜底 →
PUT /api/papers/{id}/content 上传。

用法：
    uv run python scripts/parse_papers.py --base-url http://host --token TOKEN
    uv run python scripts/parse_papers.py ... --only <paper_id>  # 只解析一篇
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import time
import unicodedata
from typing import Any

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from pypdf import PdfReader

AR5IV_URL = "https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
ARXIV_ID_RE = re.compile(r"arXiv:(\d{4}\.\d{4,5})")
LIGATURES = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl"}
PDF_NOISE_LINE = re.compile(r"^(figure\s*\d+|table\s*\d+|https?://|arxiv:|\d{1,3}$)", re.I)
PDF_HEADING_RE = re.compile(r"^(\d{1,2})(\.\d{1,2}){0,2}\.?\s+[A-Z][A-Za-z].{0,60}$")

SKIP_CLASSES = (
    "ltx_figure",
    "ltx_table",
    "ltx_listing",
    "ltx_bibliography",
    "ltx_appendix_toc",
    "ltx_page_footer",
    "ltx_role_footnote",
    "ltx_note",
)

Block = dict[str, Any]


def clean_latex(alt: str) -> str:
    alt = re.sub(r"\s+", " ", alt.strip())
    alt = re.sub(r"\\(footnotesize|small|scriptsize|displaystyle|qquad)\s*", "", alt)
    return alt.rstrip("%").strip()


def clean_citation(text: str) -> str:
    text = re.sub(r"\[\(\s*([^()\[\]]*?)\s*\)\]", r"(\1)", text)
    text = re.sub(r"\(\s*([^()]*?)\s*\)", r"(\1)", text)
    return text


def render_math(node: Tag) -> str:
    alt = clean_latex(str(node.get("alttext") or ""))
    if not alt:
        return ""
    return f"$${alt}$$" if node.get("display") == "block" else f"${alt}$"


def render_inline(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if node.name == "math":
        return render_math(node)
    classes = node.get("class") or []
    if any(c in SKIP_CLASSES for c in classes):
        return ""
    if node.name == "cite":
        return node.get_text(" ", strip=True)
    if node.name in ("script", "style", "figure", "table", "img", "svg"):
        return ""
    return "".join(
        render_inline(child)
        for child in node.children
        if isinstance(child, (Tag, NavigableString))
    )


def para_text(node: Tag) -> str:
    text = "".join(
        render_inline(child)
        for child in node.children
        if isinstance(child, (Tag, NavigableString))
    )
    text = re.sub(r"[ \t]+", " ", text)
    return clean_citation(text).strip()


def emit_block(node: Tag, blocks: list[Block], level: int) -> None:
    classes = node.get("class") or []
    if any(c in SKIP_CLASSES for c in classes):
        return
    name = node.name
    if name == "section":
        walk_section(node, blocks, level + 1)
        return
    if name == "table" and ("ltx_equation" in classes or "ltx_equationgroup" in classes):
        for math in node.find_all("math"):
            alt = clean_latex(str(math.get("alttext") or ""))
            if alt:
                blocks.append({"type": "paragraph", "md": f"$${alt}$$"})
        return
    if name in ("figure", "table"):
        return
    if name in ("ul", "ol"):
        for li in node.find_all("li", recursive=False):
            text = para_text(li)
            if text:
                blocks.append({"type": "paragraph", "md": "• " + text})
        return
    if name == "p" or (name == "div" and "ltx_p" in classes):
        text = para_text(node)
        if text:
            blocks.append({"type": "paragraph", "md": text})
        return
    if name in ("div", "span", "blockquote"):
        for child in node.children:
            if isinstance(child, Tag):
                emit_block(child, blocks, level)


def walk_section(section: Tag, blocks: list[Block], level: int) -> None:
    classes = section.get("class") or []
    if any(c in SKIP_CLASSES for c in classes):
        return
    heading = section.find(re.compile("^h[1-6]$"), recursive=False)
    if isinstance(heading, Tag):
        text = para_text(heading)
        if text:
            blocks.append({"type": "heading", "level": min(level, 6), "md": text})
    for child in section.children:
        if isinstance(child, Tag) and child is not heading:
            emit_block(child, blocks, level)


def ar5iv_to_blocks(html: str) -> list[Block]:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article") or soup
    if not isinstance(article, Tag):
        return []
    blocks: list[Block] = []
    title_el = article.find("h1")
    if isinstance(title_el, Tag):
        blocks.append({"type": "heading", "level": 1, "md": para_text(title_el)})
    abstract = article.find(class_="ltx_abstract")
    if isinstance(abstract, Tag):
        blocks.append({"type": "heading", "level": 2, "md": "Abstract"})
        for p in abstract.find_all("p"):
            text = para_text(p)
            if text:
                blocks.append({"type": "paragraph", "md": text})
    for section in article.find_all("section", recursive=False):
        classes = section.get("class") or []
        if "ltx_section" in classes or "ltx_appendix" in classes:
            walk_section(section, blocks, level=2)
    return blocks


def pdf_clean(raw: str) -> str:
    for source, target in LIGATURES.items():
        raw = raw.replace(source, target)
    raw = unicodedata.normalize("NFKC", raw)
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not PDF_NOISE_LINE.match(line.strip())
    ]
    text = "\n".join(lines)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return text


def pdf_to_blocks(data: bytes, title: str) -> list[Block]:
    reader = PdfReader(io.BytesIO(data))
    blocks: list[Block] = [{"type": "heading", "level": 1, "md": title}]
    for page in reader.pages:
        text = pdf_clean(page.extract_text() or "")
        buffer: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if PDF_HEADING_RE.match(stripped) and len(stripped) < 70:
                if buffer:
                    blocks.append({"type": "paragraph", "md": " ".join(buffer)})
                    buffer = []
                depth = 2 + stripped.split(" ")[0].count(".")
                blocks.append({"type": "heading", "level": min(depth, 6), "md": stripped})
                continue
            buffer.append(stripped)
            if stripped.endswith((".", "!", "?")) and len(" ".join(buffer)) > 300:
                blocks.append({"type": "paragraph", "md": " ".join(buffer)})
                buffer = []
        if buffer:
            blocks.append({"type": "paragraph", "md": " ".join(buffer)})
    return blocks


def extract_arxiv_id(data: bytes) -> str | None:
    try:
        reader = PdfReader(io.BytesIO(data))
        text = reader.pages[0].extract_text() or ""
    except Exception:  # noqa: BLE001
        return None
    match = ARXIV_ID_RE.search(text)
    return match.group(1) if match else None


def parse_paper(client: httpx.Client, base_url: str, paper: dict[str, Any]) -> str:
    paper_id = paper["id"]
    pdf = client.get(f"{base_url}/api/papers/{paper_id}/file")
    pdf.raise_for_status()
    blocks: list[Block] = []
    source = "pdf"
    arxiv_id = extract_arxiv_id(pdf.content)
    if arxiv_id:
        try:
            page = httpx.get(
                AR5IV_URL.format(arxiv_id=arxiv_id),
                follow_redirects=True,
                timeout=120,
            )
            if page.status_code == 200:
                blocks = ar5iv_to_blocks(page.text)
                source = "ar5iv"
        except httpx.HTTPError:
            blocks = []
    if len(blocks) < 5:
        blocks = pdf_to_blocks(pdf.content, paper["title"])
        source = "pdf"
    if len(blocks) < 2:
        return "empty"
    response = client.put(
        f"{base_url}/api/papers/{paper_id}/content",
        json={"source": source, "blocks": blocks},
    )
    response.raise_for_status()
    return f"{source} ({len(blocks)} blocks)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--only", default=None, help="只解析指定 paper_id")
    parser.add_argument("--skip-parsed", action="store_true", help="跳过已有正文的论文")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    client = httpx.Client(
        headers={"Authorization": f"Bearer {args.token}"},
        timeout=300,
    )
    listing = client.get(f"{base_url}/api/papers")
    listing.raise_for_status()
    papers = [
        paper
        for group in listing.json()["groups"]
        for paper in group["papers"]
        if paper["has_file"]
    ]
    if args.only:
        papers = [paper for paper in papers if paper["id"] == args.only]
    if args.skip_parsed:
        papers = [paper for paper in papers if not paper.get("has_content")]
    failures = 0
    for index, paper in enumerate(papers, start=1):
        try:
            outcome = parse_paper(client, base_url, paper)
        except Exception as error:  # noqa: BLE001
            outcome = f"FAILED: {error}"
            failures += 1
        print(f"[{index}/{len(papers)}] {paper['title'][:50]}: {outcome}", flush=True)
        time.sleep(1)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
