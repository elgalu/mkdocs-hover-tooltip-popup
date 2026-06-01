// Initialize and render the bundled Mermaid runtime.
//
// Mermaid is loaded from a local UMD bundle (extra/js/mermaid-<version>.min.js) so the
// docs never fetch it from a CDN. That bundle only exposes `globalThis.mermaid`; it does
// not auto-run. The mermaid2 plugin's `fence_mermaid` formatter emits each diagram as
// `<div class="mermaid">RAW source</div>` (source unescaped), so mermaid.run() can parse
// the elements directly.
//
// Runs on first load and on Material for MkDocs instant navigation (`document$`), which
// swaps page content without a full reload.
(function () {
  function paletteIsDark() {
    try {
      var palette = JSON.parse(localStorage.getItem("__palette"));
      return !!(palette && palette.index === 1);
    } catch (e) {
      return false;
    }
  }

  function renderMermaid() {
    if (typeof window.mermaid === "undefined") {
      return;
    }
    var pending = [];
    document.querySelectorAll(".mermaid").forEach(function (el) {
      if (!el.dataset.mermaidProcessed && (el.textContent || "").trim()) {
        el.dataset.mermaidProcessed = "true";
        pending.push(el);
      }
    });
    if (!pending.length) {
      return;
    }
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: paletteIsDark() ? "dark" : "default",
    });
    window.mermaid.run({ nodes: pending });
  }

  if (typeof document$ !== "undefined" && document$.subscribe) {
    document$.subscribe(renderMermaid);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderMermaid);
  } else {
    renderMermaid();
  }
})();
