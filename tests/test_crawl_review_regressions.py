from __future__ import annotations

import ast
import ipaddress
from pathlib import Path

import httpx
import pytest

from se_kb_app.crawling.http import PooledHttpFetcher
from se_kb_app.domain import FetchRequest
from service_boundary.errors import PublicError
from service_boundary.fetch import FetchLimits, bounded_get
from service_boundary.url_policy import ValidatedURL
from utils.html_cleaner import clean_and_structure
from utils.web_deduplication import WebDeduplication
from utils.webpage_crawler import WebpageCrawler


def validator(url):
    return ValidatedURL(url, httpx.URL(url).host, 443, (ipaddress.ip_address('93.184.216.34'),))


def test_code_block_preserves_leading_and_trailing_newlines():
    code = "\n  if ready:\n      run()\n\n"
    document = clean_and_structure("<article><pre><code>" + code + "</code></pre></article>", "https://fixture.invalid/a")
    assert next(block["text"] for block in document["blocks"] if block["kind"] == "code") == code


def test_cross_origin_redirect_drops_origin_credentials():
    observed = []

    def handler(request):
        observed.append(request)
        if request.url.host == 'one.invalid':
            return httpx.Response(302, headers={'location': 'https://two.invalid/next'})
        return httpx.Response(200, content=b'body')

    with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False,
                      headers={'Authorization': 'Bearer fake-review'}, cookies={'session': 'fake'}) as client:
        bounded_get(client, 'https://one.invalid/', url_validator=validator)
    assert observed[0].headers['authorization'] == 'Bearer fake-review'
    assert 'authorization' not in observed[1].headers
    assert 'cookie' not in observed[1].headers


def test_wire_limit_without_content_length_closes_stream():
    closed = []

    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            yield b'0123456789'

        def close(self):
            closed.append(True)

    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=Stream())
    )) as client:
        with pytest.raises(PublicError):
            bounded_get(client, 'https://fixture.invalid/', url_validator=validator,
                        limits=FetchLimits(compressed_bytes=5, decompressed_bytes=20))
    assert closed


def test_technical_blocks_are_not_duplicated_and_reach_extraction():
    html = ('<article><h4>Deep heading</h4><p>Text <code>inline</code>.</p>'
            '<pre><code>def unique():\n    return 42</code></pre>'
            '<blockquote><p>unique quote</p></blockquote>'
            '<table><tr><th>key</th></tr><tr><td>unique table</td></tr></table>'
            '<p><a href="/reference">Reference</a></p></article>')
    parsed = clean_and_structure(html, 'https://fixture.invalid/article')
    assert parsed['markdown'].count('def unique():') == 1
    assert parsed['markdown'].count('unique quote') == 1
    assert '    return 42' in parsed['clean_text']
    assert any(section['level'] == 4 for section in parsed['sections'])
    assert 'https://fixture.invalid/reference' in parsed['markdown']
    # Exercise the real preparation body without creating a router/model client.
    tree = ast.parse(Path('extractors/pipeline.py').read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ExtractionPipeline')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_prepare_content')
    method.returns = None
    for argument in method.args.args:
        argument.annotation = None
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), 'preparation', 'exec'), namespace)
    content = namespace['_prepare_content'](None, parsed)
    assert 'def unique():' in content and 'unique table' in content


def test_conservative_url_identity():
    dedup = WebDeduplication.__new__(WebDeduplication)
    assert dedup.normalize_url('https://EXAMPLE.com/Doc?v=1') != dedup.normalize_url('https://example.com/Doc?v=2')
    assert dedup.normalize_url('https://example.com/Doc') != dedup.normalize_url('https://example.com/doc')


def test_same_second_snapshots_do_not_overwrite(tmp_path):
    crawler = WebpageCrawler(str(tmp_path))
    try:
        first = crawler.save_data({'parsed_data': {'text': 'first'}}, 'same')
        second = crawler.save_data({'parsed_data': {'text': 'second'}}, 'same')
        assert first['parsed_file'] != second['parsed_file']
        assert 'first' in Path(first['parsed_file']).read_text(encoding='utf-8')
    finally:
        close = getattr(crawler, 'close', lambda: None)
        close()


def test_304_reuses_body_without_rendering():
    def handler(request):
        if 'if-none-match' in request.headers:
            return httpx.Response(304, headers={'etag': 'fixture'})
        return httpx.Response(200, headers={'etag': 'fixture'}, content=b'<article>retained text</article>')

    fetcher = PooledHttpFetcher(url_validator=validator, conditional_requests=True)
    fetcher.client.close()
    fetcher.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        first = fetcher.fetch(FetchRequest('https://fixture.invalid/a'))
        second = fetcher.fetch(FetchRequest('https://fixture.invalid/a'))
        assert first.content == second.content
    finally:
        fetcher.close()
