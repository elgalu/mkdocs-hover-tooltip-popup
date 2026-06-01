"""MkDocs plugin: per-node hover tooltips plus pan/zoom for images and diagrams."""

import logging
import os
from typing import Any

from mkdocs import utils
from mkdocs.config import config_options
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import ConfigurationError
from mkdocs.plugins import BasePlugin
from mkdocs.structure.pages import Page

from mkdocs_hover_tooltip_popup.exclude import exclude
from mkdocs_hover_tooltip_popup.html_page import HTMLPage


logger = logging.getLogger("mkdocs.plugin")
base_path = os.path.dirname(os.path.abspath(__file__))

# The MkDocs entry-point name users put under `plugins:` in mkdocs.yml.
PLUGIN_NAME = "hover-tooltip-popup"


class HoverTooltipPopupPlugin(BasePlugin):
    """MkDocs plugin: per-node hover tooltips plus pan/zoom for images and diagrams."""

    config_scheme = (
        ("mermaid", config_options.Type(bool, default=True)),
        ("images", config_options.Type(bool, default=False)),
        ("full_screen", config_options.Type(bool, default=False)),
        ("always_show_hint", config_options.Type(bool, default=False)),
        ("show_zoom_buttons", config_options.Type(bool, default=False)),
        ("key", config_options.Type(str, default="alt")),
        ("include", config_options.Type(list, default=["*"])),
        ("exclude", config_options.Type(list, default=[])),
        ("include_selectors", config_options.Type(list, default=[])),
        ("exclude_selectors", config_options.Type(list, default=[])),
        ("hint_location", config_options.Type(str, default="bottom")),
        ("initial_zoom_level", config_options.Type(float, default=1.0)),
        ("zoom_step", config_options.Type(float, default=0.2)),
        ("buttons_size", config_options.Type(str, default="1.25em")),
        ("auto_enable", config_options.Type(bool, default=True)),
        ("auto_enable_threshold_lines", config_options.Type(int, default=8)),
        ("auto_enable_threshold_nodes", config_options.Type(int, default=6)),
        ("auto_enable_threshold_edges", config_options.Type(int, default=5)),
        ("auto_enable_threshold_chars", config_options.Type(int, default=200)),
    )

    def on_config(self, config: MkDocsConfig, **kwargs: Any) -> MkDocsConfig:
        """Configure the plugin and validate settings."""
        # Register the mermaid-tooltips fence regardless of the plugins layout.
        self._register_tooltip_fence(config)

        # Handle case where plugins might be missing or different types
        if "plugins" not in config:
            return config

        plugins_config = config["plugins"]
        if isinstance(plugins_config, list):
            # A plugins list may mix bare names ("search") with single-key option
            # mappings ({"hover-tooltip-popup": {...}}). Extract the name from each.
            plugins: list[str] = []
            for entry in plugins_config:
                if isinstance(entry, str):
                    plugins.append(entry)
                elif isinstance(entry, dict):
                    plugins.extend(str(name) for name in entry)
        else:
            # dict / OrderedDict / PluginCollection: the keys are the plugin names.
            plugins = [str(name) for name in plugins_config]

        def check_position(plugin: str, plugins: list[str]) -> None:
            """Check this plugin is positioned correctly relative to other plugins."""
            if plugin in plugins and PLUGIN_NAME in plugins:
                if plugins.index(PLUGIN_NAME) < plugins.index(plugin):
                    raise ConfigurationError(
                        f"[{PLUGIN_NAME}] The {PLUGIN_NAME} plugin should be defined after {plugin}"
                    )

        check_plugins = ["mermaid2"]

        for p in check_plugins:
            check_position(p, plugins)

        # Validate configuration values
        self._validate_config()

        return config

    def _register_tooltip_fence(self, config: MkDocsConfig) -> None:
        """Register the ``mermaid-tooltips`` custom superfence.

        Mirrors how mkdocs-d2-plugin injects its fence: ensure
        ``pymdownx.superfences`` is enabled and append our fence to the
        superfences ``custom_fences`` config. Idempotent so a config hot-reload
        does not register the fence twice.
        """
        try:
            from mkdocs_hover_tooltip_popup.tooltip_fence import make_tooltip_formatter

            markdown_extensions = config.setdefault("markdown_extensions", [])
            if "pymdownx.superfences" not in markdown_extensions:
                markdown_extensions.append("pymdownx.superfences")

            mdx_configs = config.setdefault("mdx_configs", {})
            superfences = mdx_configs.setdefault("pymdownx.superfences", {})
            custom_fences = superfences.setdefault("custom_fences", [])

            if any(f.get("name") == "mermaid-tooltips" for f in custom_fences):
                return

            custom_fences.append(
                {
                    "name": "mermaid-tooltips",
                    "class": "hover-tooltip-popup-tooltips-data",
                    "format": make_tooltip_formatter(),
                }
            )
        except Exception as e:
            logger.warning(f"Could not register the mermaid-tooltips fence: {e}")

    def _validate_config(self) -> None:
        """Validate plugin configuration values."""
        # Validate key options
        valid_keys = {"alt", "ctrl", "shift", "none"}
        key = self.config.get("key", "alt")
        if key not in valid_keys:
            logger.warning(
                f"Invalid key '{key}'. Using default 'alt'. Valid options: {valid_keys}"
            )
            self.config["key"] = "alt"

        # Validate hint location
        valid_locations = {"top", "bottom"}
        hint_location = self.config.get("hint_location", "bottom")
        if hint_location not in valid_locations:
            logger.warning(
                f"Invalid hint_location '{hint_location}'. Using default 'bottom'. "
                f"Valid options: {valid_locations}"
            )
            self.config["hint_location"] = "bottom"

        # Validate zoom values
        zoom_step = self.config.get("zoom_step", 0.2)
        if not isinstance(zoom_step, int | float) or zoom_step <= 0:
            logger.warning(f"Invalid zoom_step '{zoom_step}'. Using default 0.2")
            self.config["zoom_step"] = 0.2

        initial_zoom = self.config.get("initial_zoom_level", 1.0)
        if not isinstance(initial_zoom, int | float) or initial_zoom <= 0:
            logger.warning(f"Invalid initial_zoom_level '{initial_zoom}'. Using default 1.0")
            self.config["initial_zoom_level"] = 1.0

    def on_post_page(self, output: str, /, *, page: Page, config: MkDocsConfig) -> str | None:
        """Process page after HTML generation to add pan-zoom functionality."""
        try:
            excluded_pages = self.config.get("exclude", [])

            if exclude(page.file.src_path, excluded_pages):
                return output  # Return original output for excluded pages

            html_page = HTMLPage(output, self.config, page, config)
            html_page.add_to_page()

            return str(html_page)

        except Exception as e:
            # Avoid re-accessing page.file.src_path here: if that access is what
            # raised, logging it would raise again and defeat the safety net.
            logger.error(f"Error processing page: {e}")
            # Return original output on error to prevent build failure
            return output

    def on_post_build(self, *, config: MkDocsConfig) -> None:
        """Copy plugin assets to the site directory."""
        try:
            output_base_path = os.path.join(config["site_dir"], "assets")

            # Ensure directories exist
            css_path = os.path.join(output_base_path, "stylesheets")
            js_path = os.path.join(output_base_path, "javascripts")

            os.makedirs(css_path, exist_ok=True)
            os.makedirs(js_path, exist_ok=True)

            # Copy CSS file
            utils.copy_file(
                os.path.join(base_path, "custom", "hover-tooltip-popup.css"),
                os.path.join(css_path, "hover-tooltip-popup.css"),
            )

            # Copy JavaScript files
            utils.copy_file(
                os.path.join(base_path, "custom", "hover-tooltip-popup.js"),
                os.path.join(js_path, "hover-tooltip-popup.js"),
            )
            # The bundled pan/zoom engine is the third-party anvaka library; keep
            # its original filename.
            utils.copy_file(
                os.path.join(base_path, "panzoom", "panzoom.min.js"),
                os.path.join(js_path, "panzoom.min.js"),
            )

            logger.debug("Successfully copied plugin assets")

        except Exception as e:
            logger.error(f"Error copying plugin assets: {e}")
            raise
