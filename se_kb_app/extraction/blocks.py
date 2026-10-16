"""One semantic traversal for technical HTML and all its downstream views."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4.element import NavigableString, Tag


def _inline(node: Any, base_url: str, *, markdown: bool) -> str:
    if isinstance(node, NavigableString):
        return re.sub(r"\s+", " ", str(node))
    if not isinstance(node, Tag):
        return ""
    if node.name in {"ul", "ol", "table", "pre"}:
        return ""
    if node.name == "br":
        return "\n"
    if node.name == "img":
        src = str(node.get("src") or node.get("data-src") or "")
        return f"![{node.get('alt', '')}]({urljoin(base_url, src)})" if markdown and src else ""
    text = "".join(_inline(child, base_url, markdown=markdown) for child in node.children)
    if node.name == "code" and markdown:
        fence = "``" if "`" in text else "`"
        return f"{fence}{text}{fence}"
    if node.name == "a" and markdown:
        target = urljoin(base_url, str(node.get("href", "")))
        if target.startswith(("http://", "https://")):
            return f"[{text.strip()}]({target})"
    return text


def collect_blocks(root: Tag, base_url: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    def add(kind: str, node: Tag, **fields: Any) -> None:
        text = _inline(node, base_url, markdown=False).strip()
        markdown = _inline(node, base_url, markdown=True).strip()
        if text or fields:
            blocks.append({"kind": kind, "text": text, "markdown": markdown, **fields})

    def walk(node: Any) -> None:
        if not isinstance(node, Tag):
            if isinstance(node, NavigableString) and str(node).strip():
                text = re.sub(r"\s+", " ", str(node)).strip()
                blocks.append({"kind": "paragraph", "text": text, "markdown": text})
            return
        name = node.name
        if name in {f"h{i}" for i in range(1, 7)}:
            add("heading", node, level=int(name[1]))
        elif name == "pre":
            code = node.get_text("", strip=False)
            if code:
                fence = "`" * max(3, max((len(x) for x in re.findall(r"`+", code)), default=0) + 1)
                blocks.append({"kind": "code", "text": code, "markdown": f"{fence}\n{code}\n{fence}"})
        elif name == "table":
            rows = []
            for row in node.find_all("tr"):
                if row.find_parent("table") is node:
                    cells = [_inline(cell, base_url, markdown=False).strip()
                             for cell in row.find_all(["td", "th"], recursive=False)]
                    if cells:
                        rows.append(cells)
            if rows:
                width = max(map(len, rows))
                padded = [row + [""] * (width - len(row)) for row in rows]
                lines = ["| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in padded]
                lines.insert(1, "| " + " | ".join(["---"] * width) + " |")
                blocks.append({"kind": "table", "rows": rows, "text": "\n".join("\t".join(row) for row in rows),
                               "markdown": "\n".join(lines)})
        elif name in {"ul", "ol"}:
            items = []
            rendered = []
            for index, li in enumerate(node.find_all("li", recursive=False), 1):
                text = _inline(li, base_url, markdown=False).strip()
                md = _inline(li, base_url, markdown=True).strip()
                if text:
                    items.append(text)
                    rendered.append((f"{index}. " if name == "ol" else "- ") + md)
            if items:
                blocks.append({"kind": "list", "items": items, "text": "\n".join(items), "markdown": "\n".join(rendered)})
            for li in node.find_all("li", recursive=False):
                for child in li.find_all(["ul", "ol", "pre", "table"]):
                    if child.find_parent(["ul", "ol"]) is node:
                        walk(child)
        elif name == "blockquote":
            nested = collect_blocks(node, base_url)
            text = render_blocks(nested, markdown=False)
            md = render_blocks(nested)
            if text:
                blocks.append({"kind": "quote", "text": text,
                               "markdown": "\n".join("> " + line for line in md.splitlines())})
        elif name == "p":
            if node.find(["p", "pre", "table", "blockquote"], recursive=False):
                plain: list[str] = []
                formatted: list[str] = []
                def flush_inline():
                    text, md = "".join(plain).strip(), "".join(formatted).strip()
                    if text:
                        blocks.append({"kind": "paragraph", "text": text, "markdown": md})
                    plain.clear()
                    formatted.clear()
                for part in node.children:
                    if isinstance(part, Tag) and part.name in {"p", "pre", "table", "blockquote"}:
                        flush_inline()
                        walk(part)
                    else:
                        plain.append(_inline(part, base_url, markdown=False))
                        formatted.append(_inline(part, base_url, markdown=True))
                flush_inline()
            else:
                add("paragraph", node)
        elif name == "img":
            src = str(node.get("src") or node.get("data-src") or "")
            if src:
                target = urljoin(base_url, src)
                alt = str(node.get("alt", ""))
                blocks.append({"kind": "image", "text": "", "markdown": f"![{alt}]({target})",
                               "src": target, "alt": alt})
        elif name in {"a", "code"}:
            add("paragraph", node)
        else:
            for nested_child in node.children:
                walk(nested_child)

    # The container itself can be article/main or a selected content div.
    for root_child in root.children:
        walk(root_child)
    return blocks


def render_blocks(blocks: list[dict[str, Any]], *, markdown: bool = True) -> str:
    output = []
    for block in blocks:
        value = block.get("markdown" if markdown else "text", "")
        if block["kind"] == "heading" and markdown:
            value = "#" * block["level"] + " " + value
        if value:
            output.append(value)
    return "\n\n".join(output)


def sections_from_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for block in blocks:
        if current is None or block["kind"] == "heading":
            current = {"heading": block["text"] if block["kind"] == "heading" else None,
                       "level": block.get("level"), "text": "", "lists": [], "images": [],
                       "code_blocks": [], "tables": [], "blocks": []}
            sections.append(current)
        current["blocks"].append(block)
        kind = block["kind"]
        if kind in {"paragraph", "quote"}:
            current["text"] += block["text"] + "\n"
        elif kind == "list":
            current["lists"].extend(block["items"])
        elif kind == "code":
            current["code_blocks"].append(block["text"])
        elif kind == "table":
            current["tables"].append(block["rows"])
        elif kind == "image":
            current["images"].append({"src": block["src"], "alt": block["alt"]})
    return sections
