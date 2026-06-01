"""Tests for the mermaid-tooltips fence formatter (build-time tooltip pipeline)."""

from bs4 import BeautifulSoup

from mkdocs_hover_tooltip_popup.tooltip_fence import make_tooltip_formatter


def _render(source: str) -> str:
    """Run the formatter on a fence source and return the emitted HTML."""
    formatter = make_tooltip_formatter()
    return formatter(source, "mermaid-tooltips", "hover-tooltip-popup-tooltips-data", {}, None)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestTooltipFormatter:
    """The formatter parses YAML and emits a hidden data div."""

    def test_basic_node_id_entry(self):
        """A bare-identifier node yields a data-node-id child."""
        out = _render('- node: A\n  text: "**hello**"')
        soup = _soup(out)
        container = soup.find("div", class_="hover-tooltip-popup-tooltips-data")
        assert container is not None
        assert container.has_attr("hidden")
        child = container.find("div")
        assert child["data-node-id"] == "A"
        assert child.find("strong").text == "hello"

    def test_node_text_entry_for_label_with_spaces(self):
        """A node value with spaces is matched by visible text (data-node-text)."""
        out = _render('- node: My Label\n  text: "info"')
        child = _soup(out).find("div", class_="hover-tooltip-popup-tooltips-data").find("div")
        assert child["data-node-text"] == "My Label"
        assert not child.has_attr("data-node-id")

    def test_node_id_detection_variants(self):
        """Identifier-shaped nodes use id; anything else uses text."""
        cases = {
            "A": "data-node-id",
            "node_1": "data-node-id",
            "n-2": "data-node-id",
            "My Node": "data-node-text",
            "a.b": "data-node-text",
            "1A": "data-node-text",  # must start with a letter to be an id
        }
        for node, expected_attr in cases.items():
            out = _render(f'- node: "{node}"\n  text: "x"')
            child = _soup(out).find("div", class_="hover-tooltip-popup-tooltips-data").find("div")
            assert child.has_attr(expected_attr), f"{node!r} -> {expected_attr}"

    def test_markdown_rendered_at_build_time(self):
        """Markdown in text is converted to HTML (links, bold) at build time."""
        out = _render('- node: A\n  text: "**bold** and [link](https://x.com)"')
        child = _soup(out).find("div", class_="hover-tooltip-popup-tooltips-data").find("div")
        assert child.find("strong").text == "bold"
        link = child.find("a")
        assert link["href"] == "https://x.com"
        assert link.text == "link"

    def test_html_content_is_real_html_not_escaped(self):
        """The rendered Markdown is real HTML, not escaped entities."""
        out = _render('- node: A\n  text: "*em*"')
        assert "<em>em</em>" in out
        assert "&lt;em&gt;" not in out

    def test_multiple_entries(self):
        """Each entry becomes its own child of the data div."""
        out = _render('- node: A\n  text: "one"\n- node: B\n  text: "two"')
        children = (
            _soup(out)
            .find("div", class_="hover-tooltip-popup-tooltips-data")
            .find_all("div", recursive=False)
        )
        assert len(children) == 2
        assert children[0]["data-node-id"] == "A"
        assert children[1]["data-node-id"] == "B"

    def test_node_id_is_attribute_escaped(self):
        """A node value with quotes is HTML-escaped in the attribute."""
        out = _render('- node: \'A"B\'\n  text: "x"')
        # The raw output must not contain an unescaped double quote inside the value.
        assert 'data-node-text="A&quot;B"' in out

    def test_malformed_yaml_returns_empty(self):
        """Unparsable YAML yields no output (no visible code block)."""
        assert _render("- : : not valid: [") == ""

    def test_not_a_list_returns_empty(self):
        """A YAML mapping (not a list) yields no output."""
        assert _render("node: A\ntext: hi") == ""

    def test_empty_source_returns_empty(self):
        """Empty source yields no output."""
        assert _render("") == ""

    def test_missing_node_key_skips_entry(self):
        """An entry without a node key is skipped; valid entries survive."""
        out = _render('- text: "orphan"\n- node: A\n  text: "ok"')
        children = (
            _soup(out)
            .find("div", class_="hover-tooltip-popup-tooltips-data")
            .find_all("div", recursive=False)
        )
        assert len(children) == 1
        assert children[0]["data-node-id"] == "A"

    def test_missing_text_key_skips_entry(self):
        """An entry without a text key is skipped."""
        out = _render("- node: A\n- node: B\n  text: ok")
        children = (
            _soup(out)
            .find("div", class_="hover-tooltip-popup-tooltips-data")
            .find_all("div", recursive=False)
        )
        assert len(children) == 1
        assert children[0]["data-node-id"] == "B"

    def test_blank_text_skips_entry(self):
        """An entry with whitespace-only text is skipped."""
        assert _render('- node: A\n  text: "   "') == ""

    def test_non_string_values_skipped(self):
        """Entries whose node/text are not strings are skipped."""
        assert _render("- node: 123\n  text: 456") == ""

    def test_non_mapping_entry_skipped(self):
        """A non-mapping list item is skipped; valid entries survive."""
        out = _render('- just a string\n- node: A\n  text: "ok"')
        children = (
            _soup(out)
            .find("div", class_="hover-tooltip-popup-tooltips-data")
            .find_all("div", recursive=False)
        )
        assert len(children) == 1

    def test_all_entries_invalid_returns_empty(self):
        """If no entry is usable, nothing is emitted."""
        assert _render("- node: A\n- text: orphan") == ""

    def test_does_not_use_page_markdown_instance(self):
        """The formatter must not render through the shared page md instance.

        The page's Markdown instance is stateful/non-reentrant; the formatter must
        use its own. Pass a sentinel whose convert() would raise if touched.
        """

        class _BoomMd:
            def convert(self, *args, **kwargs):
                raise AssertionError("formatter used the page md instance")

        formatter = make_tooltip_formatter()
        out = formatter('- node: A\n  text: "ok"', "mermaid-tooltips", "c", {}, _BoomMd())
        assert "hover-tooltip-popup-tooltips-data" in out
