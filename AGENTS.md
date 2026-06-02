# AGENTS.md

This file provides project overview, context, and coding guidelines for AI coding agents
(Claude Code, Codex, Cursor, etc.) working in this repository.

## Project Overview

`mkdocs-hover-tooltip-popup` is an MkDocs plugin with two features, applied at site-build time to
Mermaid diagrams, D2 diagrams, and images:

1. Per-node hover tooltip popups (the headline feature, Mermaid-only in v1) — see "Per-node hover
   tooltips" below.
2. Pan/zoom UI controls — each target is wrapped in a `hover-tooltip-popup-box` `<div>`, and the
   pan/zoom runtime is the bundled [anvaka/panzoom](https://github.com/anvaka/panzoom) JavaScript
   library (`mkdocs_hover_tooltip_popup/panzoom/panzoom.min.js`).

The plugin entry point is registered in `pyproject.toml`:

```toml
[project.entry-points."mkdocs.plugins"]
hover-tooltip-popup = "mkdocs_hover_tooltip_popup.plugin:HoverTooltipPopupPlugin"
```

## Architecture

Build-time flow (Python, MkDocs hooks):

1. `on_config` (plugin.py): validates config, ensures `hover-tooltip-popup` is registered after plugins
   that rewrite diagram HTML (e.g. `mermaid2`). If `hover-tooltip-popup` comes before `mermaid2` in
   `mkdocs.yml`, a `ConfigurationError` is raised.
2. `on_post_page` (plugin.py → html_page.py): for each rendered page that is not in the
   `exclude` list, parse with BeautifulSoup, find target elements, wrap each in a
   `hover-tooltip-popup-box` div with controls, and inject `<link>` + `<script>` tags pointing to
   the runtime assets. Pages with no matched targets are left untouched (no CSS/JS/meta
   injected), so diagram-free pages don't download the runtime. An element matching
   multiple selectors is wrapped once.
3. `on_post_build` (plugin.py): copies the runtime assets (`hover-tooltip-popup.css`, `hover-tooltip-popup.js`,
   `panzoom.min.js`) into `<site_dir>/assets/{stylesheets,javascripts}/`.

Selector resolution (`html_page.py::HTMLPage._find_elements`):

- Defaults: `{".mermaid", ".d2"}`.
- `exclude_selectors` removes from defaults; `include_selectors` adds. `images: true` adds `img`.
- Legacy `mermaid: false` removes `.mermaid`.
- Final list is stored back into `self.config["selectors"]` and emitted to the runtime via a
  `<meta name="hover-tooltip-popup-data">` JSON tag (also carries `initial_zoom_level`, `zoom_step`,
  `buttons_size`).

Per-diagram opt-out and auto-detection (`yaml_parser.py`, called from
`html_page.py::_should_apply_panzoom`):

- For `<pre class="mermaid">` elements, the inner `<code>` text is parsed for a YAML
  frontmatter block (`---` ... `---`).
- If the frontmatter has `hover-tooltip-popup: { enabled: false }`, panzoom is skipped for that
  diagram (the opt-out key is `yaml_parser.OPT_OUT_KEY`).
- Otherwise, when `auto_enable: true` (default), `should_enable_panzoom()` enables panzoom
  only for diagrams that exceed any of the size thresholds (`auto_enable_threshold_lines`,
  `_nodes`, `_edges`, `_chars`). When `auto_enable: false`, all matched diagrams get panzoom
  (legacy behavior).
- Auto-detection currently runs only for Mermaid `<pre class="mermaid">`. D2 and `<img>`
  always get panzoom.

Per-node hover tooltips (Mermaid only, v1; `tooltip_fence.py` + `hover-tooltip-popup.js`):

- A ` ```mermaid-tooltips ` fenced block placed right after a ` ```mermaid ` block declares
  per-node hover popups. It is a YAML list of `{node, text}` entries; `text` is full Markdown.
- The fence is registered as a pymdownx superfence in `plugin.py::_register_tooltip_fence`
  (called from `on_config`, mirrors mkdocs-d2-plugin). Its formatter
  (`tooltip_fence.py::make_tooltip_formatter`) parses the YAML, renders each `text` to HTML at
  build time with a **fresh** `markdown.Markdown()` (the page's shared instance is non-reentrant),
  and emits a hidden `<div class="hover-tooltip-popup-tooltips-data">` with one child per entry carrying
  `data-node-id` (when `node` looks like an id) or `data-node-text` (otherwise).
- Tooltips are **decoupled from pan/zoom**: they work on any Mermaid diagram, including small ones
  the auto-detect leaves un-wrapped. `add_to_page` therefore injects the runtime assets when a
  tooltips block is present even if no element gets a `hover-tooltip-popup-box`.
- Runtime: `hover-tooltip-popup.js::activate_tooltips` (called from `activate_zoom_pan`, same poll) finds each
  tooltips-data div, resolves the diagram SVG from its previous sibling (the `.mermaid` element or
  the `.hover-tooltip-popup-box` wrapping it; skips control-button icon SVGs), matches each node by
  `g[id^="flowchart-<id>-"]` or by label `textContent`, and on hover shows a body-level
  `position: fixed` `.hover-tooltip-popup-tooltip-popover` to the left of the node (flips right on edge collision).

Runtime assets:

- `mkdocs_hover_tooltip_popup/custom/hover-tooltip-popup.css`: styling for the box, nav, hints, fullscreen modal,
  and the hover tooltip popover (`.hover-tooltip-popup-tooltip-popover`).
- `mkdocs_hover_tooltip_popup/custom/hover-tooltip-popup.js`: reads the `<meta name="hover-tooltip-popup-data">` and
  `<meta name="hover-tooltip-popup-theme">` tags, wires up panzoom on each `.hover-tooltip-popup-box`, persists
  zoom/pan state per diagram in `localStorage` (auto-cleared after 30 days), implements
  reset/fullscreen/hint behavior, and wires per-node hover tooltips.
- `mkdocs_hover_tooltip_popup/panzoom/panzoom.min.js`: pan/zoom engine, originally vendored
  from [anvaka/panzoom](https://github.com/anvaka/panzoom) (MIT). We now maintain it as a
  forked copy and edit it directly when the upstream API can't express what we need (e.g.
  canvas-style navigation). Keep the anvaka MIT `LICENCE` alongside it.

Box structure (`box.py::create_box`): the `nav` always contains a reset
button; info button is added unless `always_show_hint`; zoom-in/out buttons added when
`show_zoom_buttons`; fullscreen min/max buttons added when `full_screen`. The hint info box
is appended at the top or bottom of the hover-tooltip-popup-box depending on `hint_location`.

Custom fonts / styled HTML inside Mermaid nodes (the C4-tier look, demoed in
`docs/Mermaid/custom-fonts.md`): Mermaid renders flowchart node labels as real HTML inside an
SVG `<foreignObject>` when `htmlLabels` is on (its default for flowcharts), so a label can carry
`<span class='c4-name'>…</span><span class='c4-type'>[Kind]</span><span class='c4-detail'>…</span>`
plus inline `<a href>` links. Three authoring rules: concatenate the tier spans with NO `<br/>`
between them (they are `display: block`, so a `<br/>` adds a second empty line and the node looks
double-spaced — keep `<br/>` only for a break *inside* one tier); single-quote the HTML attributes
(a double quote closes Mermaid's `["…"]` label early → `Syntax error in text`); and escape a literal
`&` as `&amp;`.

The tier styles live in `docs/css/diagram-colors.css` (listed in `extra_css`). Two non-obvious CSS
rules, both about how Mermaid sizes the node box:

- The `.c4-name` / `.c4-type` / `.c4-detail` selectors are deliberately NOT scoped under `.mermaid`.
  Mermaid measures each HTML label in a probe element detached from the rendered `.mermaid`
  container, so a `.mermaid .c4-name` rule would not match during measurement and the box would be
  sized for default 16px text, then clip the real tiers. Bare class selectors apply during the
  probe too. These class names only appear inside diagrams, so the un-scoped selector is safe.
- `.c4-name` uses `white-space: nowrap`: Mermaid measures the name as one line, so a name that wraps
  produces a box one line too short that clips the bottom tier. `nowrap` grows the box width instead.

`font-size` on the tiers uses `!important` to beat Mermaid's own `.nodeLabel` size (which would
otherwise flatten all tiers to one size). Note that `!important` makes these sizes harder to
override downstream; that is intended here since the whole point is to win over Mermaid's defaults.

Because the demo uses the `mermaid2.fence_mermaid` fence (raw `<div class="mermaid">`, source not
escaped) and `docs/css/diagram-colors.css` is a real page stylesheet, the tiers size correctly with
no extra runtime config — our shipped `hover-tooltip-popup.js`/`mermaid-init.js` only set
`securityLevel: "loose"` and rely on Mermaid's default `htmlLabels`. A project forced onto
`pymdownx.superfences.fence_code_format` (which HTML-escapes the source into `<pre class="mermaid">
<code>`) needs a heavier init that: captures each diagram's source synchronously at script-eval time,
swaps the `<pre>` for a `<div>` (pan/zoom only attaches to a `<div>`/`<img>`), and renders via
`mermaid.render(id, source)` with `htmlLabels: true` and the tier CSS repeated as `themeCSS` (the
page stylesheet does not apply inside Mermaid's off-DOM measurement probe). The "auto-run empties the
element before you can read it" hazard that motivates the synchronous capture is specific to this
vendored UMD bundle's auto-run interacting with the `<pre><code>` shape, not general Mermaid
behavior. We ship `fence_mermaid` precisely to avoid all of that.

## Development Commands

`make` with no target prints a self-documenting help menu (no side effects). Run
`make setup` explicitly the first time you clone the repo. Each Make target is a
one-line wrapper that delegates to a small focused script under `scripts/`, so the
real logic lives there and is easy to read or run directly.

```bash
make                  # print the help menu (default target)
make setup            # → scripts/contributor-setup.sh (uv, .venv, deps, prek hooks, d2, browser)
make test [ARGS=...]  # → scripts/test.sh (all tests + coverage; ARGS forwarded to pytest)
make test-unit        # → only fast unit tests (-m "not e2e")
make test-e2e         # → only headless-browser E2E tests (-m e2e, no coverage)
make check            # → scripts/check.sh (prek; CI: changed-files only, local: --all-files)
make prek             # → scripts/prek.sh (prek --all-files unconditionally)
make build            # → scripts/build.sh (mkdocs build --strict)
make serve            # → scripts/serve.sh (mkdocs serve --no-strict)
make env              # → scripts/env.sh (print Python / uv / venv diagnostics)
make clean            # → scripts/clean.sh (remove .venv, caches, site/)
```

Aliases: `tests` → `test`, `docs` → `build`, `all` / `hooks` → `check`.

Hooks run via [`prek`](https://github.com/j178/prek), a pre-commit-compatible runner
installed by `make setup` via `uv tool install prek`. The hook config is the standard
`.pre-commit-config.yaml`, so classic `pre-commit` also works if preferred.

CI behavior: `scripts/contributor-setup.sh` and `scripts/check.sh` detect CI via
`CDP_BUILD_VERSION` / `CI` and switch to `uv sync --frozen` and prek with
`--from-ref origin/HEAD --to-ref HEAD` respectively. The setup script also skips
the local-only d2 install in CI.

## Releasing to PyPI (from a laptop)

Releases are cut manually with `uv build` + `uv publish` (no GitHub Actions for publishing).
Auth uses a PyPI API token in `UV_PUBLISH_TOKEN` (TestPyPI uses `UV_PUBLISH_TOKEN_TEST`); tokens
are created at <https://pypi.org/manage/account/token/> (project owner: `elgalu`).

```bash
make version-bump BUMP=patch     # → scripts/version-bump.sh (patch|minor|major; edits pyproject + uv.lock)
make pypi-build                  # → scripts/pypi-build.sh (clean dist/, uv build, twine check)
make pypi-publish-test           # → TestPyPI dry run (needs UV_PUBLISH_TOKEN_TEST)
make pypi-publish                # → PyPI (needs UV_PUBLISH_TOKEN)
make pypi-all BUMP=patch         # test → version-bump → build → publish to PyPI, in one shot
```

`version-bump` only edits files (it does not commit or tag) — review, commit, and tag the version
bump yourself before/after publishing. `dist/` is gitignored. `pypi-check` is an alias for
`pypi-build` (build + validate without uploading).

Run a single test:

```bash
uv run pytest tests/test_yaml_parser.py::test_should_enable_panzoom_with_explicit_yaml -v
```

Run tests without coverage (faster):

```bash
uv run pytest tests/test_html_page.py -v --no-cov
```

Coverage reports are written to `htmlcov/index.html` and `coverage.xml` after `make test`.

## Configuration Reference

Plugin options (defined in `plugin.py::HoverTooltipPopupPlugin.config_scheme`, defaults in parens):

- Selectors: `include_selectors` (`[]`), `exclude_selectors` (`[]`), `mermaid` (`true`),
  `images` (`false`).
- UI: `always_show_hint` (`false`), `hint_location` (`"bottom"` or `"top"`),
  `show_zoom_buttons` (`false`), `buttons_size` (`"1.25em"`), `full_screen` (`false`).
- Zoom: `initial_zoom_level` (`1.0`), `zoom_step` (`0.2`).
- Navigation: `navigation` (`"canvas"` default, or `"classic"`). In `canvas` mode, the wheel /
  trackpad two-finger drag pans, `ctrl`/`cmd`+wheel and trackpad pinch zoom, and right-mouse
  drag pans (left click stays free for nodes/tooltips). In `classic` mode, the `key` modifier
  (`"alt"` default, also `ctrl` / `shift` / `none`) gates the library's left-drag pan + wheel
  zoom. The `key` option only applies in `classic` mode.
- Pages: `exclude` (`[]`), `include` (`["*"]`).
- Auto-detect: `auto_enable` (`true`), `auto_enable_threshold_lines` (`8`), `_nodes` (`6`),
  `_edges` (`5`), `_chars` (`200`).

Note: `site_url` must be set in `mkdocs.yml` for the plugin to function (otherwise relative
asset URLs break).

## Testing

There are two layers:

Unit tests live in `tests/`, named `test_<module>.py` (one file per source module plus
regression tests for specific bugs like `test_hint_button_*`). They mock the MkDocs
`MkDocsConfig`, `Page`, and `File` objects rather than running a full build.

End-to-end tests live in `tests/e2e/`, marked `e2e`, and drive a real headless Chromium
via Playwright. They are hermetic: `tests/e2e/conftest.py` runs the real
`HoverTooltipPopupPlugin.on_post_page` + `on_post_build` to emit a page and copy the real runtime
assets (`hover-tooltip-popup.js`, `panzoom.min.js`, `hover-tooltip-popup.css`) into a temp site dir, then loads it
over `file://`. Diagram targets are inline SVGs, so no Mermaid CDN, d2 binary, or git is
needed. If Playwright or its browser is unavailable, the whole `tests/e2e` package skips
(module-level `pytest.skip`) so `make test` stays green; install the browser with
`playwright install chromium-headless-shell` (done automatically by `make setup`).

Select layers with the marker: `make test-unit` (`-m "not e2e"`) or `make test-e2e`
(`-m e2e`). `make test` runs both.

When adding behavior, prefer extending the matching `tests/test_<module>.py` (or
`tests/e2e/test_browser.py` for runtime behavior) over creating a new file. The repo's
pytest config (`pyproject.toml`) sets `--strict-markers`, `--strict-config`, and runs coverage
by default.

## Code Style

- Python 3.11+ (tested on 3.11–3.14); line length 99 (per `pyproject.toml`, narrower than the global 130).
- `ruff` for linting + formatting; `mypy` is configured but with relaxed settings (most
  strict checks off; `tests/.*` is excluded).
- Pre-commit hook config is in `.pre-commit-config.yaml`.
- File naming: Python uses `underscores`; shell scripts and directories use `hyphens`.

## Plugin Ordering Constraint

In `mkdocs.yml`, list `hover-tooltip-popup` AFTER any plugin that emits the diagram HTML it should wrap.
The check is currently enforced for `mermaid2`, but the same rule applies to any plugin that
generates the targeted selectors (`.mermaid`, `.d2`, `img`). Putting `hover-tooltip-popup` first will
cause it to find no elements (or, for `mermaid2`, raise `ConfigurationError` in `on_config`).

## Repository Layout

| Path                                  | Purpose                                                                       |
| ------------------------------------- | ----------------------------------------------------------------------------- |
| `mkdocs_hover_tooltip_popup/`         | Plugin source                                                                 |
| `mkdocs_hover_tooltip_popup/custom/`  | Bundled CSS + project JS (`hover-tooltip-popup.js`)                           |
| `mkdocs_hover_tooltip_popup/box.py`   | Builds the control-box DOM (`create_box`)                                     |
| `mkdocs_hover_tooltip_popup/panzoom/` | `panzoom.min.js` pan/zoom engine, forked from anvaka (MIT); edit when needed  |
| `tests/`                              | Unit tests, one file per source module                                        |
| `tests/e2e/`                          | Headless-browser E2E tests (Playwright); marked `e2e`, skip if no browser     |
| `docs/`                               | MkDocs documentation source (Mermaid/, D2/, etc.)                             |
| `scripts/`                            | Per-target shell scripts (setup, check, prek, test, build, serve, env, clean) |
| `mkdocs.yml`                          | Demo site config used by `make serve` / `make build`                          |
