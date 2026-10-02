"""Adversarial-input tests: hostile markup through to_standalone_html.

Every input below is attacker-controlled HTML run through the public API
with default security, exercising scheme smuggling, data: URI policy,
raw-text parsing holes, malformed markup repairs, and re-serialization
shape.
"""

import base64

from unmhtml import Document, Resource, Security, to_standalone_html

from .conftest import PNG_BYTES

BASE_URL = "https://example.com/"

PNG_DATA_URI = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode()

PNG_RESOURCES = {
    "https://example.com/a.png": Resource(PNG_BYTES, "image/png"),
    "https://example.com/b.png": Resource(PNG_BYTES, "image/png"),
    "https://example.com/x": Resource(PNG_BYTES, "image/png"),
}


def convert(html, resources=None, security=None):
    document = Document(html=html, resources=resources or {}, base_url=BASE_URL)
    if security is None:
        return to_standalone_html(document)
    return to_standalone_html(document, security=security)


class TestSchemeSmuggling:
    """Disallowed schemes must not survive entity, case, or whitespace tricks."""

    def test_entity_encoded_javascript_in_href(self):
        assert convert('<a href="&#106;avascript:alert(1)">x</a>') == "<a>x</a>"

    def test_tab_smuggled_via_entity(self):
        # Browsers strip tabs inside URLs; the filter must see through it.
        assert convert('<a href="jav&#x09;ascript:alert(1)">x</a>') == "<a>x</a>"

    def test_mixed_case_scheme(self):
        assert convert('<a href="JaVaScRiPt:alert(1)">x</a>') == "<a>x</a>"

    def test_leading_spaces(self):
        assert convert('<a href="  javascript:alert(1)">x</a>') == "<a>x</a>"

    def test_other_script_schemes(self):
        for scheme in ("vbscript", "jscript", "livescript", "mocha"):
            assert convert(f'<a href="{scheme}:alert(1)">x</a>') == "<a>x</a>", scheme

    def test_smuggled_scheme_in_img_src(self):
        assert convert('<img src="jav&#x09;ascript:alert(1)">') == "<img>"


class TestDataUriPolicy:
    """data: URIs are allowed only for passive media types."""

    def test_text_html_dropped_from_href(self):
        assert convert('<a href="data:text/html,<b>hi</b>">x</a>') == "<a>x</a>"

    def test_text_html_dropped_from_embedding_tags(self):
        assert (
            convert('<iframe src="data:text/html,<script>alert(1)</script>"></iframe>')
            == "<iframe></iframe>"
        )
        assert (
            convert('<object data="data:text/html,<b>hi</b>"></object>')
            == "<object></object>"
        )
        assert convert('<embed src="data:text/html,x">') == "<embed>"

    def test_svg_data_uri_denied_on_document_hosts(self):
        svg = "data:image/svg+xml,<svg></svg>"
        assert convert(f'<iframe src="{svg}"></iframe>') == "<iframe></iframe>"
        assert convert(f'<embed src="{svg}">') == "<embed>"
        assert convert(f'<object data="{svg}"></object>') == "<object></object>"

    def test_svg_data_uri_kept_on_img(self):
        assert (
            convert('<img src="data:image/svg+xml,<svg></svg>">')
            == '<img src="data:image/svg+xml,&lt;svg&gt;&lt;/svg&gt;">'
        )

    def test_passive_image_data_uri_kept(self):
        assert (
            convert('<img src="data:image/png;base64,iVBORw0KGgo=">')
            == '<img src="data:image/png;base64,iVBORw0KGgo=">'
        )

    def test_javascript_media_type_dropped(self):
        assert (
            convert('<a href="data:application/javascript,alert(1)">x</a>')
            == "<a>x</a>"
        )

    def test_bare_data_uri_with_empty_media_type_kept(self):
        assert convert('<a href="data:,x">x</a>') == '<a href="data:,x">x</a>'


class TestNoscriptRawTextHole:
    """Content inside noscript parses as raw text in some modes; it must go."""

    def test_script_inside_noscript_removed(self):
        assert convert("<noscript><script>alert(1)</script></noscript>") == ""

    def test_entire_noscript_content_removed(self):
        html = (
            "<noscript><p>Please enable JS</p><img src=x onerror=alert(1)></noscript>ok"
        )
        assert convert(html) == "ok"


class TestSvgAndUnknownElements:
    def test_script_inside_svg_removed_graphics_survive(self):
        assert (
            convert('<svg><script>alert(1)</script><path d="M0 0"/></svg>')
            == '<svg><path d="M0 0"></path></svg>'
        )

    def test_unknown_element_unwrapped_children_kept(self):
        assert (
            convert('<my-widget onclick="x()" data-x="1"><b>keep</b></my-widget>')
            == "<b>keep</b>"
        )


class TestSrcset:
    def test_smuggled_scheme_candidate_drops_whole_attribute(self):
        assert convert('<img srcset="javascript:alert(1) 1x, ok.png 2x">') == "<img>"

    def test_relative_candidates_survive_and_embed(self):
        result = convert('<img srcset="a.png 1x, b.png 2x">', PNG_RESOURCES)

        assert result == f'<img srcset="{PNG_DATA_URI} 1x, {PNG_DATA_URI} 2x">'


class TestMalformedMarkup:
    """Parser-repair tricks must not reassemble into executable elements."""

    def test_interleaved_script_tags_never_reassemble(self):
        result = convert("<scr<script>ipt>alert(1)</scr</script>ipt>")

        # Everything comes back as escaped text, never as markup.
        assert result == "ipt&gt;alert(1)ipt&gt;"
        assert "<script" not in result.lower()

    def test_unquoted_event_handler_gone_src_kept(self):
        result = convert("<img src=x onerror=alert(1)>", PNG_RESOURCES)

        assert "onerror" not in result
        assert result == f'<img src="{PNG_DATA_URI}">'

    def test_unclosed_tags_repaired_content_survives(self):
        assert convert("<div><p>unclosed") == "<div><p>unclosed</p></div>"

    def test_uppercase_tag_and_scheme(self):
        assert convert('<A HREF="JAVASCRIPT:x">y</A>') == "<a>y</a>"


class TestMetaDefusal:
    def test_refresh_mixed_case(self):
        assert (
            convert('<meta http-equiv="Refresh" content="0;url=http://evil.com">')
            == '<meta content="0;url=http://evil.com">'
        )

    def test_refresh_attribute_order_reversed(self):
        assert (
            convert('<meta content="1;url=http://evil.com" http-equiv="rEfReSh">')
            == '<meta content="1;url=http://evil.com">'
        )

    def test_set_cookie_uppercase(self):
        assert (
            convert('<META HTTP-EQUIV="Set-Cookie" content="a=b">')
            == '<meta content="a=b">'
        )

    def test_dns_prefetch_name_dropped(self):
        assert (
            convert('<meta content="evil.com" name="DNS-PREFETCH">')
            == '<meta content="evil.com">'
        )

    def test_charset_and_viewport_untouched(self):
        html = (
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        )
        assert convert(html) == html

    def test_harmless_http_equiv_survives(self):
        assert (
            convert('<meta http-equiv="content-type" content="text/html">')
            == '<meta http-equiv="content-type" content="text/html">'
        )


class TestFormDefusal:
    def test_submission_attributes_stripped_controls_survive(self):
        html = (
            '<form target="_blank">'
            '<button formaction="/go" formtarget="_blank" formmethod="post">Go</button>'
            '<input formmethod="post" type="text" value="v">'
            "</form>"
        )
        assert (
            convert(html)
            == '<form><button>Go</button><input type="text" value="v"></form>'
        )

    def test_submission_attributes_survive_when_forms_enabled(self):
        html = (
            '<form target="_blank">'
            '<button formaction="/go" formmethod="post">Go</button>'
            "</form>"
        )
        result = convert(html, security=Security(disable_forms=False))

        assert (
            result
            == '<form target="_blank"><button formaction="/go" formmethod="post">Go</button></form>'
        )


class TestDuplicateAttributes:
    def test_first_href_wins_on_anchor(self):
        html = '<a href="https://good.example/a" href="javascript:alert(1)">x</a>'
        assert convert(html) == '<a href="https://good.example/a">x</a>'

    def test_first_src_wins_on_img(self):
        html = '<img src="a.png" src="javascript:alert(1)">'
        assert convert(html, PNG_RESOURCES) == f'<img src="{PNG_DATA_URI}">'


class TestCssPostEmbed:
    def test_style_attribute_urls_stripped(self):
        result = convert(
            '<div style="background: url(javascript:alert(1)); color: red">t</div>'
        )

        assert "javascript" not in result
        assert "url(" not in result
        assert "color: red" in result

    def test_style_block_imports_and_external_urls_stripped(self):
        html = (
            "<style>"
            "@import url(https://evil.com/a.css);"
            '@import "https://evil.com/b.css";'
            "body { background: url(https://evil.com/track.png); }"
            "}</style>"
        )
        result = convert(html)

        assert "@import" not in result
        assert "evil.com" not in result

    def test_style_block_fragment_and_data_urls_kept(self):
        html = (
            "<style>"
            ".frag { fill: url(#g); }"
            ".data { list-style: url(data:image/png;base64,iVBORw0KGgo=); }"
            "</style>"
        )
        result = convert(html)

        assert "url(#g)" in result
        assert "url(data:image/png;base64,iVBORw0KGgo=)" in result


class TestCommentsPreserved:
    """Comments survive verbatim — a documented accepted risk (inert in
    modern browsers), asserted here so a behavior change gets noticed."""

    def test_comment_with_script_inside_preserved_as_comment(self):
        html = "<p>a</p><!-- <script>alert(1)</script> --><p>b</p>"
        assert convert(html) == html

    def test_ie_conditional_comment_remains_comment_text(self):
        html = "<!--[if IE]><script>alert(1)</script><![endif]--><p>x</p>"
        assert convert(html) == html


class TestDocumentShape:
    def test_full_document_stripped_to_fragment_with_doctype(self):
        html = (
            "<!DOCTYPE html>"
            "<html><head><title>t</title></head><body><h1>x</h1></body></html>"
        )
        assert convert(html) == "<!DOCTYPE html>\n<title>t</title><h1>x</h1>"

    def test_legacy_doctype_re_emitted_verbatim(self):
        html = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"><p>x</p>'
        assert (
            convert(html)
            == '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">\n<p>x</p>'
        )

    def test_no_doctype_no_skeleton(self):
        assert convert("<h1>x</h1>") == "<h1>x</h1>"
