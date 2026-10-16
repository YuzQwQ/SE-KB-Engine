from __future__ import annotations

from dataclasses import dataclass

from se_kb_app.artifacts.identity import content_id, document_id
from se_kb_app.artifacts.models import SourceAnchor


CLEANER_VERSION = "technical-blocks-v2"


@dataclass(frozen=True)
class CleanSection:
    heading_path: tuple[str, ...]
    text: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class CleanDocument:
    source_url: str
    document_id: str
    content_hash: str
    title: str
    text: str
    sections: tuple[CleanSection, ...]
    cleaner_version: str = CLEANER_VERSION

    def anchor(self, start: int, end: int, heading_path: tuple[str, ...] = ()) -> SourceAnchor:
        quote = self.text[start:end]
        return SourceAnchor(self.document_id, start, end, content_id(quote), heading_path)


class DeterministicCleaner:
    def clean(self, source_url: str, payload: str | bytes) -> CleanDocument:
        from utils.html_cleaner import clean_and_structure
        from service_boundary.decoding import decode_payload

        html = decode_payload(payload)[0] if isinstance(payload, bytes) else payload
        parsed = clean_and_structure(html, source_url)
        title = parsed["title"]
        blocks: list[tuple[tuple[str, ...], str]] = []
        headings: list[tuple[int, str]] = []
        for block in parsed.get("blocks", []):
            text = block["text"]
            if not text:
                continue
            if block["kind"] == "heading":
                level = block["level"]
                headings = [(depth, heading) for depth, heading in headings if depth < level]
                headings.append((level, text))
            blocks.append((tuple(heading for _, heading in headings), text))
        output: list[str] = []
        sections: list[CleanSection] = []
        cursor = 0
        for heading_path, text in blocks:
            if output:
                output.append("\n")
                cursor += 1
            start = cursor
            output.append(text)
            cursor += len(text)
            sections.append(CleanSection(heading_path, text, start, cursor))
        clean_text = "".join(output)
        digest = content_id(clean_text)
        return CleanDocument(
            source_url,
            document_id(source_url, digest),
            digest,
            title,
            clean_text,
            tuple(sections),
        )

