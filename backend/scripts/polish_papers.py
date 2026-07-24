"""用 AI 润色论文正文排版，提升可读性（不改动英文原意、不翻译、不摘要）。

流程：拉取论文列表 → 按分类/标题筛选 → 读取现有 blocks →
重建为 Markdown → 按小节分块送 AI 清理排版（修断句、去目录点线/页码、
去图表坐标乱码、接回被切断的句子、保留公式与标题）→ 重新解析为 blocks →
备份原始 blocks 后 PUT /api/papers/{id}/content 回写。

用法：
    uv run python scripts/polish_papers.py \
        --base-url http://host --token TOKEN \
        --ai-base-url https://.../v1 --ai-key KEY --ai-model gpt-5.5 \
        --category Deepseek --backup-dir ./polish-backups

    # 只跑一篇、先预览不回写：
    uv run python scripts/polish_papers.py ... --only "DeepSeek V4" --dry-run

AI 相关参数缺省时从环境变量 APP_AI_BASE_URL / APP_AI_API_KEY / APP_AI_MODEL 读取。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

Block = dict[str, Any]

SYSTEM_PROMPT = (
    "You are a meticulous copy editor. You are given raw text extracted from an "
    "academic paper (often from a PDF), which has broken line wrapping, hyphenated "
    "words split across lines, merged or fragmented sentences, table-of-contents "
    "dotted leaders with page numbers, page headers/footers, and garbled figure/chart "
    "axis dumps.\n\n"
    "Your job is ONLY to clean up formatting and readability so it reads smoothly, "
    "WITHOUT changing the meaning:\n"
    "- Keep the language exactly as-is (English stays English). Do NOT translate.\n"
    "- Do NOT summarize, paraphrase, rewrite, or add any commentary or new content.\n"
    "- Rejoin words split by hyphenation (e.g. 'Mixture-ofExperts' -> 'Mixture-of-Experts', "
    "'repre- sentation' -> 'representation').\n"
    "- Merge sentence fragments that were wrongly split across lines into flowing paragraphs.\n"
    "- Remove table-of-contents lines (dotted leaders '. . . .' followed by page numbers), "
    "stray page numbers, running headers/footers, and garbled figure/chart numeric dumps.\n"
    "- Preserve genuine section headings. Mark headings with Markdown '#' (use the same "
    "nesting level implied by their numbering: '# ' for top sections, '## ' for x.y, etc.).\n"
    "- Preserve LaTeX math verbatim (inline $...$ and display $$...$$). Preserve bullet "
    "points (lines starting with '•').\n"
    "- Separate paragraphs with a single blank line.\n"
    "Output ONLY the cleaned Markdown, nothing else."
)


def blocks_to_markdown(blocks: list[Block]) -> str:
    parts: list[str] = []
    for block in blocks:
        md = str(block.get("md", "")).strip()
        if not md:
            continue
        if block.get("type") == "heading":
            level = int(block.get("level", 1) or 1)
            level = min(max(level, 1), 6)
            parts.append("#" * level + " " + md)
        else:
            parts.append(md)
    return "\n\n".join(parts)


def markdown_to_blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    for chunk in re.split(r"\n\s*\n", text):
        piece = chunk.strip()
        if not piece:
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", piece)
        if heading and "\n" not in piece:
            blocks.append(
                {
                    "type": "heading",
                    "level": len(heading.group(1)),
                    "md": heading.group(2).strip(),
                }
            )
        else:
            # collapse hard-wrapped single newlines inside a paragraph into spaces
            para = re.sub(r"\s*\n\s*", " ", piece).strip()
            blocks.append({"type": "paragraph", "md": para})
    return blocks


def chunk_markdown(text: str, max_chars: int) -> list[str]:
    """Split markdown into chunks near heading boundaries, each <= max_chars."""
    segments = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    chunks: list[str] = []
    current = ""
    for seg in segments:
        if not seg.strip():
            continue
        if current and len(current) + len(seg) > max_chars:
            chunks.append(current)
            current = seg
        elif len(seg) > max_chars:
            # a single oversized segment: flush current, then hard-split by paragraphs
            if current:
                chunks.append(current)
                current = ""
            paras = re.split(r"\n\s*\n", seg)
            buf = ""
            for para in paras:
                if buf and len(buf) + len(para) > max_chars:
                    chunks.append(buf)
                    buf = para
                else:
                    buf = f"{buf}\n\n{para}" if buf else para
            if buf:
                current = buf
        else:
            current = f"{current}\n\n{seg}" if current else seg
    if current.strip():
        chunks.append(current)
    return chunks


def polish_chunk(
    client: httpx.Client,
    ai_base_url: str,
    ai_key: str,
    ai_model: str,
    chunk: str,
) -> str:
    url = f"{ai_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": chunk},
        ],
    }
    headers = {"Authorization": f"Bearer {ai_key}"}
    response = client.post(url, json=payload, headers=headers)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("AI returned empty content")
    return content.strip()


def polish_blocks(
    client: httpx.Client,
    ai_base_url: str,
    ai_key: str,
    ai_model: str,
    blocks: list[Block],
    max_chars: int,
) -> list[Block]:
    markdown = blocks_to_markdown(blocks)
    chunks = chunk_markdown(markdown, max_chars)
    cleaned_parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        cleaned = polish_chunk(client, ai_base_url, ai_key, ai_model, chunk)
        cleaned_parts.append(cleaned)
        print(
            f"    chunk {index}/{len(chunks)} ok ({len(chunk)}->{len(cleaned)} chars)",
            flush=True,
        )
    return markdown_to_blocks("\n\n".join(cleaned_parts))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--ai-base-url", default=os.environ.get("APP_AI_BASE_URL", ""))
    parser.add_argument("--ai-key", default=os.environ.get("APP_AI_API_KEY", ""))
    parser.add_argument("--ai-model", default=os.environ.get("APP_AI_MODEL", ""))
    parser.add_argument("--category", default=None, help="按分类子串筛选，如 Deepseek")
    parser.add_argument("--only", default=None, help="只处理指定标题或 paper_id")
    parser.add_argument("--max-chars", type=int, default=9000, help="每次送 AI 的最大字符数")
    parser.add_argument("--backup-dir", default="./polish-backups")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不回写")
    parser.add_argument("--ai-timeout", type=float, default=300.0)
    args = parser.parse_args()

    if not (args.ai_base_url and args.ai_key and args.ai_model):
        print(
            "ERROR: AI 未配置（--ai-base-url/--ai-key/--ai-model 或 APP_AI_* 环境变量）",
            file=sys.stderr,
        )
        return 2

    base_url = args.base_url.rstrip("/")
    api = httpx.Client(headers={"Authorization": f"Bearer {args.token}"}, timeout=300)
    ai = httpx.Client(timeout=args.ai_timeout)

    listing = api.get(f"{base_url}/api/papers")
    listing.raise_for_status()
    papers = [
        paper
        for group in listing.json()["groups"]
        for paper in group["papers"]
        if paper.get("has_content")
    ]
    if args.category:
        papers = [p for p in papers if args.category.lower() in (p.get("category") or "").lower()]
    if args.only:
        papers = [p for p in papers if args.only in (p["id"], p.get("title"))]
    if not papers:
        print("没有匹配的论文", file=sys.stderr)
        return 1

    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for index, paper in enumerate(papers, start=1):
        title = paper.get("title", paper["id"])
        print(f"[{index}/{len(papers)}] {title}", flush=True)
        try:
            content = api.get(f"{base_url}/api/papers/{paper['id']}/content").json()
            original = content.get("blocks", [])
            source = content.get("source", "pdf")
            backup_path = backup_dir / f"{paper['id']}.json"
            backup_path.write_text(
                json.dumps({"source": source, "blocks": original}, ensure_ascii=False),
                encoding="utf-8",
            )
            polished = polish_blocks(
                ai, args.ai_base_url, args.ai_key, args.ai_model, original, args.max_chars
            )
            print(f"    blocks {len(original)} -> {len(polished)}", flush=True)
            if args.dry_run:
                preview = backup_dir / f"{paper['id']}.polished.json"
                preview.write_text(
                    json.dumps({"source": source, "blocks": polished}, ensure_ascii=False),
                    encoding="utf-8",
                )
                print(f"    dry-run: 预览写入 {preview}", flush=True)
            else:
                resp = api.put(
                    f"{base_url}/api/papers/{paper['id']}/content",
                    json={"source": source, "blocks": polished},
                )
                resp.raise_for_status()
                print("    回写完成", flush=True)
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"    FAILED: {error}", flush=True)
        time.sleep(1)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
