"""Reject pathological DOM inputs before allocating a BeautifulSoup tree."""
from __future__ import annotations

from html.parser import HTMLParser

from service_boundary.errors import public_error


class _BudgetParser(HTMLParser):
    def __init__(self, maximum_nodes: int, maximum_depth: int) -> None:
        super().__init__(convert_charrefs=False)
        self.nodes = 0
        self.maximum_nodes, self.maximum_depth = maximum_nodes, maximum_depth
        self.stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.nodes += 1
        if self.nodes > self.maximum_nodes:
            raise public_error("resource_limit")
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(tag)
            if len(self.stack) > self.maximum_depth:
                raise public_error("resource_limit")

    def handle_startendtag(self, tag, attrs):
        self.nodes += 1
        if self.nodes > self.maximum_nodes:
            raise public_error("resource_limit")

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - self.stack[::-1].index(tag) - 1]


def enforce_html_budget(content: str, *, maximum_nodes: int = 50_000, maximum_depth: int = 128) -> None:
    parser = _BudgetParser(maximum_nodes, maximum_depth)
    parser.feed(content)
    parser.close()
