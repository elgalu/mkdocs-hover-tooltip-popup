"""Headless-browser end-to-end tests driving the real runtime (hover-tooltip-popup.js).

Each test loads the hermetically generated site (see conftest) in headless
Chromium and asserts on observable behavior: panzoom initialization, the
zoom/reset/fullscreen controls, the hint toggle, modifier-key gating, and
localStorage persistence.
"""

import re

import pytest

from .conftest import (
    make_async_render_tooltip_site,
    make_prefixed_id_tooltip_site,
    make_site,
    make_site_without_theme_meta,
    make_tooltip_site,
)


pytestmark = pytest.mark.e2e


def _scale_of(page, selector: str) -> float:
    """Return the current X-scale of the transform matrix on the first match."""
    transform = page.locator(selector).first.evaluate("e => e.style.transform")
    match = re.search(r"matrix\(([-0-9.]+)", transform or "matrix(1,")
    return float(match.group(1)) if match else 1.0


class TestInitialization:
    """Panzoom wires up the expected targets and assets without errors."""

    def test_no_page_errors(self, page):
        assert page.page_errors == []

    def test_assets_loaded(self, page):
        # The runtime function from hover-tooltip-popup.js must be present on the page.
        assert page.evaluate("typeof activate_zoom_pan") == "function"
        # The panzoom library must have loaded too.
        assert page.evaluate("typeof panzoom") == "function"

    def test_both_targets_wrapped(self, page):
        assert page.locator(".hover-tooltip-popup-box").count() == 2

    def test_targets_initialized(self, page):
        # img and the inline-SVG .d2 div both get data-zoom set by hover-tooltip-popup.js.
        assert page.evaluate("document.querySelectorAll('[data-zoom]').length") == 2

    def test_controls_present(self, page):
        # show_zoom_buttons + full_screen are enabled in the session site.
        assert page.locator(".hover-tooltip-popup-reset").count() == 2
        assert page.locator(".hover-tooltip-popup-zoom-in").count() == 2
        assert page.locator(".hover-tooltip-popup-zoom-out").count() == 2
        assert page.locator(".hover-tooltip-popup-max").count() == 2


class TestZoomControls:
    """The zoom-in / zoom-out / reset buttons change the element transform."""

    def test_zoom_in_increases_scale(self, page):
        before = _scale_of(page, ".hover-tooltip-popup-box img")
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-zoom-in").first.click()
        page.wait_for_timeout(250)
        after = _scale_of(page, ".hover-tooltip-popup-box img")
        assert after > before

    def test_zoom_out_decreases_scale(self, page):
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-zoom-in").first.click()
        page.wait_for_timeout(200)
        mid = _scale_of(page, ".hover-tooltip-popup-box img")
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-zoom-out").first.click()
        page.wait_for_timeout(200)
        after = _scale_of(page, ".hover-tooltip-popup-box img")
        assert after < mid

    def test_reset_restores_identity(self, page):
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-zoom-in").first.click()
        page.wait_for_timeout(200)
        assert _scale_of(page, ".hover-tooltip-popup-box img") != 1.0
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-reset").first.click()
        page.wait_for_timeout(200)
        assert _scale_of(page, ".hover-tooltip-popup-box img") == 1.0


class TestFullscreen:
    """The maximize/minimize buttons toggle the fullscreen class."""

    def test_maximize_then_minimize(self, page):
        box = page.locator(".hover-tooltip-popup-box").first
        assert box.evaluate("e => e.classList.contains('hover-tooltip-popup-fullscreen')") is False

        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-max").first.click()
        page.wait_for_timeout(150)
        assert box.evaluate("e => e.classList.contains('hover-tooltip-popup-fullscreen')") is True

        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-min").first.click()
        page.wait_for_timeout(150)
        assert box.evaluate("e => e.classList.contains('hover-tooltip-popup-fullscreen')") is False

    def test_escape_exits_fullscreen(self, page):
        """Pressing Escape leaves fullscreen, even though the box has no keyboard focus.

        The handler is on `document` (a `<div>` is not focusable), gated on this box being
        in fullscreen, so Escape elsewhere is a no-op.
        """
        box = page.locator(".hover-tooltip-popup-box").first
        is_fs = "e => e.classList.contains('hover-tooltip-popup-fullscreen')"

        # Escape while not in fullscreen does nothing.
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
        assert box.evaluate(is_fs) is False

        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-max").first.click()
        page.wait_for_timeout(150)
        assert box.evaluate(is_fs) is True

        # Focus is on the page body, not the box; Escape must still exit fullscreen.
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        assert box.evaluate(is_fs) is False
        assert page.page_errors == []


class TestHint:
    """The info button toggles the hint box visibility."""

    def test_info_toggles_hint(self, page):
        hint = page.locator(
            ".hover-tooltip-popup-box .hover-tooltip-popup-info-box, .hover-tooltip-popup-box .hover-tooltip-popup-info-box-top"
        ).first
        assert hint.evaluate("e => e.classList.contains('hover-tooltip-popup-hidden')") is True

        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-info").first.click()
        page.wait_for_timeout(120)
        assert hint.evaluate("e => e.classList.contains('hover-tooltip-popup-hidden')") is False

        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-info").first.click()
        page.wait_for_timeout(120)
        assert hint.evaluate("e => e.classList.contains('hover-tooltip-popup-hidden')") is True

    def test_canvas_hint_text_set_at_runtime(self, page):
        """In canvas mode the runtime rewrites the hint to explain move + zoom gestures."""
        hint = page.locator(
            ".hover-tooltip-popup-box .hover-tooltip-popup-info-box, "
            ".hover-tooltip-popup-box .hover-tooltip-popup-info-box-top"
        ).first
        text = hint.text_content()
        assert "move" in text
        assert "zoom" in text
        assert "right-drag" in text


class TestPersistence:
    """Zoom state is saved to localStorage and cleared on reset."""

    def test_zoom_writes_localstorage(self, page):
        assert (
            page.evaluate(
                "Object.keys(localStorage).filter(k => k.startsWith('hover-tooltip-popup-')).length"
            )
            == 0
        )
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-zoom-in").first.click()
        page.wait_for_timeout(400)  # debounce is 200ms
        keys = page.evaluate(
            "Object.keys(localStorage).filter(k => k.startsWith('hover-tooltip-popup-'))"
        )
        assert len(keys) >= 1

    def test_state_restored_after_reload(self, page):
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-zoom-in").first.click()
        page.wait_for_timeout(400)
        saved = _scale_of(page, ".hover-tooltip-popup-box img")
        assert saved != 1.0

        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_function("document.querySelectorAll('[data-zoom]').length >= 2")
        page.wait_for_timeout(200)
        restored = _scale_of(page, ".hover-tooltip-popup-box img")
        assert restored == saved

    def test_reset_clears_localstorage(self, page):
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-zoom-in").first.click()
        page.wait_for_timeout(400)
        assert (
            page.evaluate(
                "Object.keys(localStorage).filter(k => k.startsWith('hover-tooltip-popup-')).length"
            )
            >= 1
        )
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-reset").first.click()
        # Reset clears storage after the reset-triggered pan/zoom events settle
        # (debounce + margin); wait past that window before asserting.
        page.wait_for_function(
            "Object.keys(localStorage).filter(k => k.startsWith('hover-tooltip-popup-')).length === 0",
            timeout=3000,
        )

    def test_reset_state_stays_cleared(self, page):
        """Regression: the debounced save handlers must not re-persist state after reset.

        Previously panzoom_reset() cleared localStorage synchronously, but the
        moveTo/zoomAbs calls emitted pan/zoom events whose debounced handlers
        re-saved an identity state ~200ms later, so the key reappeared.
        """
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-zoom-in").first.click()
        page.wait_for_timeout(400)
        page.locator(".hover-tooltip-popup-box .hover-tooltip-popup-reset").first.click()
        # Wait well past the debounce window, then confirm nothing was re-saved.
        page.wait_for_timeout(600)
        assert (
            page.evaluate(
                "Object.keys(localStorage).filter(k => k.startsWith('hover-tooltip-popup-')).length"
            )
            == 0
        )


class TestModifierKeyGating:
    """The configured modifier key is wired into the box's data-key attribute."""

    def test_data_key_attribute_reflects_config(self, _browser, tmp_path):
        # Build a one-off site with key='ctrl' and confirm the data-key wiring.
        url = make_site(tmp_path, key="ctrl")
        context = _browser.new_context()
        pg = context.new_page()
        pg.goto(url)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_function("document.querySelectorAll('[data-zoom]').length >= 2")
        data_key = pg.locator(".hover-tooltip-popup-box").first.get_attribute("data-key")
        context.close()
        assert data_key == "ctrl"


class TestRobustness:
    """hover-tooltip-popup.js degrades gracefully on unexpected page shapes."""

    def test_missing_theme_meta_does_not_throw(self, _browser, tmp_path):
        """Regression: a missing hover-tooltip-popup-theme meta tag must not crash the script.

        hover-tooltip-popup.js previously did `querySelector(...).content` unguarded, throwing a
        TypeError on any page where the meta tag was absent, which aborted all
        initialization.
        """
        url = make_site_without_theme_meta(tmp_path)
        context = _browser.new_context()
        pg = context.new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        pg.goto(url)
        pg.wait_for_load_state("networkidle")
        # Initialization still proceeds via the polling fallback.
        pg.wait_for_function("document.querySelectorAll('[data-zoom]').length >= 2", timeout=10000)
        context.close()
        assert errors == []


class TestTooltipHover:
    """Per-node hover tooltips show a popover with build-time-rendered HTML."""

    @staticmethod
    def _open_tooltip_page(browser, url):
        context = browser.new_context()
        pg = context.new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        pg.goto(url)
        pg.wait_for_load_state("networkidle")
        # Wait until the runtime has wired the tooltips data block.
        pg.wait_for_function(
            "document.querySelector('.hover-tooltip-popup-tooltips-data[data-tooltips-wired]') !== null",
            timeout=10000,
        )
        pg.page_errors = errors  # type: ignore[attr-defined]
        return context, pg

    def test_not_visible_initially(self, _browser, tmp_path):
        context, pg = self._open_tooltip_page(_browser, make_tooltip_site(tmp_path))
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 0
        context.close()

    def test_appears_on_hover_by_node_id(self, _browser, tmp_path):
        context, pg = self._open_tooltip_page(_browser, make_tooltip_site(tmp_path))
        pg.locator("#flowchart-A-0").hover()
        pg.wait_for_timeout(150)
        popover = pg.locator(".hover-tooltip-popup-tooltip-popover")
        assert popover.count() == 1
        assert "Tooltip for" in popover.inner_text()
        context.close()

    def test_appears_on_hover_by_node_text(self, _browser, tmp_path):
        context, pg = self._open_tooltip_page(_browser, make_tooltip_site(tmp_path))
        pg.locator("#flowchart-B-1").hover()
        pg.wait_for_timeout(150)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 1
        context.close()

    def test_content_is_rendered_html(self, _browser, tmp_path):
        context, pg = self._open_tooltip_page(_browser, make_tooltip_site(tmp_path))
        pg.locator("#flowchart-A-0").hover()
        pg.wait_for_timeout(150)
        # The Markdown **A** must have been rendered to a <strong> at build time.
        assert pg.locator(".hover-tooltip-popup-tooltip-popover strong").count() == 1
        context.close()

    def test_disappears_after_close_delay_on_mouse_leave(self, _browser, tmp_path):
        context, pg = self._open_tooltip_page(_browser, make_tooltip_site(tmp_path))
        pg.locator("#flowchart-A-0").hover()
        pg.wait_for_timeout(150)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 1
        pg.mouse.move(5, 5)  # move away from the node
        # A short grace period (TOOLTIP_CLOSE_DELAY ~250ms) keeps the popover briefly
        # so the cursor can travel into it; it is still present right after leaving.
        pg.wait_for_timeout(100)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 1
        # ...and gone once the grace period elapses.
        pg.wait_for_timeout(400)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 0
        context.close()

    def test_stays_open_while_hovering_popover(self, _browser, tmp_path):
        """The popover persists while the cursor is over it (to click links / copy text)."""
        context, pg = self._open_tooltip_page(_browser, make_tooltip_site(tmp_path))
        pg.locator("#flowchart-A-0").hover()
        pg.wait_for_timeout(150)
        popover = pg.locator(".hover-tooltip-popup-tooltip-popover")
        assert popover.count() == 1
        # Move from the node into the popover and dwell well past the close delay.
        popover.hover()
        pg.wait_for_timeout(600)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 1
        # Leaving the popover closes it after the grace period.
        pg.mouse.move(5, 5)
        pg.wait_for_timeout(400)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 0
        context.close()

    def test_works_without_panzoom_box(self, _browser, tmp_path):
        """Tooltips work on an un-wrapped diagram (decoupled from pan/zoom)."""
        context, pg = self._open_tooltip_page(_browser, make_tooltip_site(tmp_path, wrapped=False))
        # No hover-tooltip-popup-box on this page, but tooltips still wire up.
        assert pg.locator(".hover-tooltip-popup-box").count() == 0
        pg.locator("#flowchart-A-0").hover()
        pg.wait_for_timeout(150)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 1
        context.close()

    def test_no_page_errors(self, _browser, tmp_path):
        context, pg = self._open_tooltip_page(_browser, make_tooltip_site(tmp_path))
        pg.locator("#flowchart-A-0").hover()
        pg.wait_for_timeout(150)
        pg.mouse.move(5, 5)
        pg.wait_for_timeout(150)
        assert pg.page_errors == []

    def test_matches_prefixed_and_state_node_ids(self, _browser, tmp_path):
        """Tooltips match Mermaid 11's prefixed ids and fall back to label text.

        Mermaid 11 ids node groups as ``mermaid-<ts>-flowchart-A-0`` (prefixed) and
        ``mermaid-<ts>-state-Proc-2`` (state diagrams). A ``data-node-id`` must match the
        embedded ``flowchart-<id>-`` segment, and for the state id (no ``flowchart-``)
        fall back to the visible label.
        """
        context, pg = self._open_tooltip_page(_browser, make_prefixed_id_tooltip_site(tmp_path))
        pg.locator('g[id$="-flowchart-A-0"]').hover()
        pg.wait_for_timeout(150)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 1
        pg.mouse.move(5, 5)
        pg.wait_for_timeout(150)
        pg.locator('g[id$="-state-Proc-2"]').hover()
        pg.wait_for_timeout(150)
        popover = pg.locator(".hover-tooltip-popup-tooltip-popover")
        assert popover.count() == 1
        assert "State tooltip" in popover.inner_text()
        context.close()

    def test_wires_up_when_diagram_renders_after_poll_window(self, _browser, tmp_path):
        """Tooltips wire up even when the SVG appears after the activation poll ends.

        Mermaid renders asynchronously and may inject its SVG well after page load.
        The MutationObserver must wire the tooltips whenever the SVG arrives, not
        only during the initial 5s poll window.
        """
        context = _browser.new_context()
        pg = context.new_page()
        pg.goto(make_async_render_tooltip_site(tmp_path))
        # The SVG is injected at ~6s, past the runtime's 5s poll window; the
        # observer must still wire the tooltips once it appears.
        pg.wait_for_function(
            "document.querySelector('.hover-tooltip-popup-tooltips-data[data-tooltips-wired]') !== null",
            timeout=15000,
        )
        pg.locator("#flowchart-A-0").hover()
        pg.wait_for_timeout(150)
        assert pg.locator(".hover-tooltip-popup-tooltip-popover").count() == 1
        context.close()


class TestCanvasNavigation:
    """Canvas-style navigation (the default): wheel pans, ctrl-wheel zooms, right-drag pans."""

    @staticmethod
    def _open(browser, url):
        context = browser.new_context(viewport={"width": 1000, "height": 800})
        pg = context.new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        pg.goto(url)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_function("document.querySelectorAll('[data-zoom]').length >= 1")
        pg.page_errors = errors  # type: ignore[attr-defined]
        return context, pg

    def test_plain_wheel_pans(self, _browser, tmp_path):
        """A wheel event without ctrl pans (translation changes, scale does not)."""
        context, pg = self._open(_browser, make_site(tmp_path))
        sel = ".hover-tooltip-popup-box [data-zoom]"
        assert _scale_of(pg, sel) == 1.0
        box = pg.locator(".hover-tooltip-popup-box").first.bounding_box()
        pg.evaluate(
            """(pt) => document.querySelector('.hover-tooltip-popup-box').dispatchEvent(
                new WheelEvent('wheel', {deltaX: 40, deltaY: 60, ctrlKey: false,
                    clientX: pt.x, clientY: pt.y, bubbles: true, cancelable: true}))""",
            {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2},
        )
        pg.wait_for_timeout(200)
        transform = pg.locator(sel).first.evaluate("e => e.style.transform")
        # Panned: translation present, scale still 1.
        assert "matrix(1," in transform
        assert transform != "matrix(1, 0, 0, 1, 0, 0)"
        assert pg.page_errors == []
        context.close()

    def test_ctrl_wheel_zooms(self, _browser, tmp_path):
        """A wheel event with ctrlKey zooms (scale changes)."""
        context, pg = self._open(_browser, make_site(tmp_path))
        sel = ".hover-tooltip-popup-box [data-zoom]"
        assert _scale_of(pg, sel) == 1.0
        box = pg.locator(".hover-tooltip-popup-box").first.bounding_box()
        pg.evaluate(
            """(pt) => document.querySelector('.hover-tooltip-popup-box').dispatchEvent(
                new WheelEvent('wheel', {deltaY: -120, ctrlKey: true,
                    clientX: pt.x, clientY: pt.y, bubbles: true, cancelable: true}))""",
            {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2},
        )
        pg.wait_for_timeout(200)
        assert _scale_of(pg, sel) > 1.0
        context.close()

    def test_right_drag_pans(self, _browser, tmp_path):
        """Holding the right mouse button and dragging pans the diagram."""
        context, pg = self._open(_browser, make_site(tmp_path))
        sel = ".hover-tooltip-popup-box [data-zoom]"
        box = pg.locator(".hover-tooltip-popup-box").first.bounding_box()
        cx = box["x"] + box["width"] / 2
        cy = box["y"] + min(box["height"] / 2, 200)
        pg.mouse.move(cx, cy)
        pg.mouse.down(button="right")
        pg.mouse.move(cx + 100, cy + 70, steps=5)
        pg.mouse.up(button="right")
        pg.wait_for_timeout(200)
        transform = pg.locator(sel).first.evaluate("e => e.style.transform")
        assert transform != "matrix(1, 0, 0, 1, 0, 0)"
        assert pg.page_errors == []
        context.close()

    def test_shift_right_click_does_not_pan_or_block_menu(self, _browser, tmp_path):
        """Shift+right-click is reserved for the browser's native context menu.

        Regression: it must NOT start a pan, and the contextmenu must NOT be
        default-prevented (so Copy / Inspect / ... stay available). A plain right-click
        still suppresses the menu so right-drag panning works.
        """
        context, pg = self._open(_browser, make_site(tmp_path))
        box = pg.locator(".hover-tooltip-popup-box").first.bounding_box()
        pt = {"x": box["x"] + box["width"] / 2, "y": box["y"] + min(box["height"] / 2, 200)}
        result = pg.evaluate(
            """(pt) => {
                const box = document.querySelector('.hover-tooltip-popup-box');
                const sel = '.hover-tooltip-popup-box [data-zoom]';
                const mk = (type, opts) => new MouseEvent(type, Object.assign(
                    {clientX: pt.x, clientY: pt.y, bubbles: true, cancelable: true}, opts));
                // Shift+right press then drag (right button held): must not pan.
                box.dispatchEvent(mk('mousedown', {button: 2, shiftKey: true, buttons: 2}));
                window.dispatchEvent(mk('mousemove', {buttons: 2, clientX: pt.x + 60, clientY: pt.y + 60}));
                const panned = getComputedStyle(document.querySelector(sel)).transform
                    !== 'matrix(1, 0, 0, 1, 0, 0)';
                // Native menu must be allowed on Shift, suppressed on a plain right-click.
                const shiftPrevented = !box.dispatchEvent(mk('contextmenu', {button: 2, shiftKey: true}));
                const plainPrevented = !box.dispatchEvent(mk('contextmenu', {button: 2, shiftKey: false}));
                return {panned, shiftPrevented, plainPrevented};
            }""",
            pt,
        )
        assert result["panned"] is False
        assert result["shiftPrevented"] is False  # browser menu allowed
        assert result["plainPrevented"] is True  # plain right-click suppressed for panning
        context.close()

    def test_right_drag_pan_self_heals_on_missed_mouseup(self, _browser, tmp_path):
        """A missed right-button release must not leave the pan stuck to the cursor.

        If the mouseup is swallowed (e.g. the native menu grabbed it), the next
        mousemove sees the button is no longer held and stops panning.
        """
        context, pg = self._open(_browser, make_site(tmp_path))
        box = pg.locator(".hover-tooltip-popup-box").first.bounding_box()
        pt = {"x": box["x"] + box["width"] / 2, "y": box["y"] + min(box["height"] / 2, 200)}
        stayed = pg.evaluate(
            """(pt) => {
                const box = document.querySelector('.hover-tooltip-popup-box');
                const sel = '.hover-tooltip-popup-box [data-zoom]';
                const mk = (type, opts) => new MouseEvent(type, Object.assign(
                    {clientX: pt.x, clientY: pt.y, bubbles: true, cancelable: true}, opts));
                box.dispatchEvent(mk('mousedown', {button: 2, buttons: 2}));
                // Missed mouseup: subsequent moves report no button held (buttons: 0).
                window.dispatchEvent(mk('mousemove', {buttons: 0, clientX: pt.x + 40, clientY: pt.y + 40}));
                const a1 = getComputedStyle(document.querySelector(sel)).transform;
                window.dispatchEvent(mk('mousemove', {buttons: 0, clientX: pt.x + 120, clientY: pt.y + 120}));
                const a2 = getComputedStyle(document.querySelector(sel)).transform;
                return a1 === a2;  // no further panning after the button was released
            }""",
            pt,
        )
        assert stayed is True
        assert pg.page_errors == []
        context.close()

    def test_classic_mode_right_drag_does_not_pan(self, _browser, tmp_path):
        """In classic mode the canvas layer is absent, so right-drag does not pan.

        (The library only pans on left/middle drag, and never on right-button drag.)
        """
        context, pg = self._open(_browser, make_site(tmp_path, navigation="classic", key="alt"))
        sel = ".hover-tooltip-popup-box [data-zoom]"
        box = pg.locator(".hover-tooltip-popup-box").first.bounding_box()
        cx = box["x"] + box["width"] / 2
        cy = box["y"] + min(box["height"] / 2, 200)
        pg.mouse.move(cx, cy)
        pg.mouse.down(button="right")
        pg.mouse.move(cx + 100, cy + 70, steps=5)
        pg.mouse.up(button="right")
        pg.wait_for_timeout(200)
        # No right-drag pan in classic mode: transform stays at identity.
        assert pg.locator(sel).first.evaluate("e => e.style.transform") in (
            "",
            "matrix(1, 0, 0, 1, 0, 0)",
        )
        context.close()

    @staticmethod
    def _wheel(pg, ctrl=False, alt=False):
        box = pg.locator(".hover-tooltip-popup-box").first.bounding_box()
        pg.evaluate(
            """(a) => document.querySelector('.hover-tooltip-popup-box').dispatchEvent(
                new WheelEvent('wheel', {deltaY: -120, ctrlKey: a.ctrl, altKey: a.alt,
                    clientX: a.x, clientY: a.y, bubbles: true, cancelable: true}))""",
            {
                "ctrl": ctrl,
                "alt": alt,
                "x": box["x"] + box["width"] / 2,
                "y": box["y"] + box["height"] / 2,
            },
        )
        pg.wait_for_timeout(200)

    def test_classic_key_none_wheel_zooms(self, _browser, tmp_path):
        """Classic + key 'none': a plain wheel zooms (the modifier gate is off)."""
        context, pg = self._open(_browser, make_site(tmp_path, navigation="classic", key="none"))
        sel = ".hover-tooltip-popup-box [data-zoom]"
        assert _scale_of(pg, sel) == 1.0
        self._wheel(pg)
        assert _scale_of(pg, sel) > 1.0
        context.close()

    def test_classic_key_alt_requires_modifier(self, _browser, tmp_path):
        """Classic + key 'alt': plain wheel does nothing; alt+wheel zooms.

        Regression: the old gate was inverted (modifier vetoed instead of enabling),
        so a plain wheel zoomed and alt+wheel did not.
        """
        context, pg = self._open(_browser, make_site(tmp_path, navigation="classic", key="alt"))
        sel = ".hover-tooltip-popup-box [data-zoom]"
        assert _scale_of(pg, sel) == 1.0
        # Plain wheel: the 'alt' modifier is not held, so nothing happens.
        self._wheel(pg)
        assert _scale_of(pg, sel) == 1.0
        # alt+wheel: the modifier is held, so it zooms.
        self._wheel(pg, alt=True)
        assert _scale_of(pg, sel) > 1.0
        context.close()
