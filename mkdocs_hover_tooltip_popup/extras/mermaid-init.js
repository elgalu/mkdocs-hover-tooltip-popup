// Optional Mermaid initializer shipped with mkdocs-hover-tooltip-popup.
//
// This file is NOT loaded automatically. It is an opt-in convenience for sites that bundle
// Mermaid offline and want it rendered with HTML labels (so styled in-node content like the
// C4 tiers works) alongside this plugin's pan/zoom. Activate it by copying it into your
// extra_javascript, loaded right AFTER the Mermaid library, e.g.:
//
//   extra_javascript:
//     - extra/js/mermaid-11.15.0.min.js                       # the Mermaid UMD bundle
//     - assets/javascripts/hover-tooltip-popup-mermaid-init.js # this file (copied to site assets/)
//
// and use the raw superfence so the source is not HTML-escaped:
//
//   markdown_extensions:
//     - pymdownx.superfences:
//         custom_fences:
//           - name: mermaid
//             class: mermaid
//             format: !!python/name:mermaid2.fence_mermaid   # raw <div class="mermaid">
//
// Why this exists: a UMD Mermaid bundle only sets globalThis.mermaid and does not auto-run
// with the config we want. With `fence_mermaid` each diagram is emitted as
// `<div class="mermaid">RAW source</div>`, so mermaid.run() parses it directly and pan/zoom
// attaches to the <div>. (The escaping `fence_code_format` fence is intentionally not
// supported — it would require heavy DOM surgery to undo the escaping.)
//
// Runs on first load and on Material for MkDocs instant navigation (`document$`).
(function () {
  // Dark/light follows the Material palette. Material exposes `__md_get`, which reads the
  // scope-prefixed localStorage key (`<scope>.__palette`) — a plain `localStorage.__palette`
  // is the wrong key on a real Material site. Guard it: it is null before the user toggles.
  // index 1 == the second palette entry (dark, in a default-first palette order).
  function pickTheme() {
    try {
      var palette = window.__md_get && window.__md_get("__palette");
      return palette && palette.index === 1 ? "dark" : "default";
    } catch (e) {
      return "default";
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
      // loose: required so node labels can carry inline <a> links and so pan/zoom works.
      securityLevel: "loose",
      // htmlLabels: render labels as foreignObject HTML (not flat SVG <text>) so styled
      // in-node spans (e.g. the C4 tiers in diagram-colors.css) honor their CSS. Default for
      // flowcharts; set explicitly so other diagram types behave the same.
      htmlLabels: true,
      flowchart: { htmlLabels: true, wrap: true },
      wrap: true,
      theme: pickTheme(),
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
