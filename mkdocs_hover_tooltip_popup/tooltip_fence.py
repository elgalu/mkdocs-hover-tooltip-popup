"""Build-time handling of the ``mermaid-tooltips`` fenced block.

A ``mermaid-tooltips`` fence sits in the Markdown source right after the
``mermaid`` block it annotates and declares per-node hover popups, e.g.::

    ```mermaid-tooltips
    - node: A
      text: "Info about **A** with a [link](https://example.com)"
    - node: My Label
      text: "Matched by visible label text"
    ```

Each entry's ``text`` is rendered from Markdown to HTML at build time. The
formatter emits a hidden ``<div class="hover-tooltip-popup-tooltips-data">`` carrying one
child element per entry; the bundled ``zoompan.js`` reads it at runtime, locates
the matching SVG node, and shows the pre-rendered HTML on hover.

Targeting: an entry's ``node`` is treated as a Mermaid node id when it looks like
an identifier (``data-node-id``); otherwise it is matched against the node's
visible label text (``data-node-text``).
"""

import html
import logging
import re
from collections.abc import Callable
from typing import Any

import markdown
import yaml


logger = logging.getLogger(__name__)

# A bare Mermaid node id (e.g. A, B2, node_1). Anything else (spaces, punctuation)
# is treated as visible label text to match instead.
_NODE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _render_markdown(text: str) -> str:
    """Render tooltip Markdown to HTML using a fresh, isolated parser.

    A new ``markdown.Markdown`` instance is used per call rather than the page's
    shared instance, which is stateful and not re-entrant: rendering tooltip
    content through it mid-page would corrupt the page render.
    """
    parser = markdown.Markdown(extensions=["extra"])
    rendered: str = parser.convert(text)
    return rendered


def _build_entry_html(node: Any, text: Any) -> str | None:
    """Build the hidden child element for one tooltip entry.

    ``node`` and ``text`` come from untrusted parsed YAML, so they may be any type.
    Returns ``None`` if the entry is unusable (non-string, missing, or blank).
    """
    if not isinstance(node, str) or not isinstance(text, str):
        logger.warning("Skipping mermaid-tooltips entry with non-string node/text")
        return None

    node = node.strip()
    if not node or not text.strip():
        logger.warning("Skipping mermaid-tooltips entry with empty node or text")
        return None

    attr = "data-node-id" if _NODE_ID_RE.match(node) else "data-node-text"
    rendered = _render_markdown(text)
    return f'<div {attr}="{html.escape(node, quote=True)}">{rendered}</div>'


def _build_tooltips_html(source: str) -> str:
    """Parse the fence ``source`` (a YAML list) and build the hidden data div.

    Returns an empty string for malformed input or when no usable entries remain,
    so the fence never renders as a visible code block.
    """
    try:
        parsed: Any = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        logger.warning(f"Could not parse mermaid-tooltips block as YAML: {exc}")
        return ""

    if not isinstance(parsed, list):
        logger.warning("mermaid-tooltips block must be a YAML list of {node, text} entries")
        return ""

    children: list[str] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            logger.warning("Skipping non-mapping mermaid-tooltips entry")
            continue
        child = _build_entry_html(entry.get("node"), entry.get("text"))
        if child is not None:
            children.append(child)

    if not children:
        return ""

    return '<div class="hover-tooltip-popup-tooltips-data" hidden>' + "".join(children) + "</div>"


def make_tooltip_formatter() -> Callable[..., str]:
    """Return a pymdownx.superfences ``format`` callback for ``mermaid-tooltips``.

    The callback signature matches superfences:
    ``formatter(source, language, class_name, options, md, **kwargs) -> str``.
    """

    def formatter(
        source: str,
        language: str,
        class_name: str,
        options: dict[str, Any],
        md: Any,
        **kwargs: Any,
    ) -> str:
        return _build_tooltips_html(source)

    return formatter
