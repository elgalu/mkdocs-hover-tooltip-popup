let panzoomScrollPosition = 0;

// Constants for localStorage state management
const THIRTY_DAYS_IN_MS = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds
const SAVE_DEBOUNCE_DELAY_MS = 200; // Debounce delay for saving zoom state in milliseconds

// Constants for zoom functionality
const DEFAULT_ZOOM_LEVEL = 1.0; // Default browser zoom level (100%)
const DEFAULT_ZOOM_STEP = 0.2; // Default zoom step for zoom in/out buttons

// LocalStorage utility functions for saving zoom levels
function getStorageKey(boxId) {
  const pageUrl = window.location.pathname;
  return `hover-tooltip-popup-${pageUrl}-${boxId}`;
}

function saveZoomState(boxId, transform) {
  try {
    const key = getStorageKey(boxId);
    localStorage.setItem(key, JSON.stringify({
      x: transform.x,
      y: transform.y,
      scale: transform.scale,
      timestamp: Date.now()
    }));
  } catch (e) {
    console.warn('Failed to save zoom state to localStorage:', e);
  }
}

function loadZoomState(boxId) {
  try {
    const key = getStorageKey(boxId);
    const saved = localStorage.getItem(key);
    if (saved) {
      const state = JSON.parse(saved);
      // Only use saved state if it's less than 30 days old
      if (Date.now() - state.timestamp < THIRTY_DAYS_IN_MS) {
        return state;
      }
    }
  } catch (e) {
    console.warn('Failed to load zoom state from localStorage:', e);
  }
  return null;
}

function clearZoomState(boxId) {
  try {
    const key = getStorageKey(boxId);
    localStorage.removeItem(key);
  } catch (e) {
    console.warn('Failed to clear zoom state from localStorage:', e);
  }
}

function minimize(instance, box, max, min) {
  box.classList.remove("hover-tooltip-popup-fullscreen");
  max.classList.remove("hover-tooltip-popup-hidden");
  min.classList.add("hover-tooltip-popup-hidden");
  panzoom_reset(instance, box)
  setTimeout(() => {
    window.scrollTo(0, panzoomScrollPosition);
  }, 0);
}

function maximize(instance, box, max, min) {
  panzoomScrollPosition =
    window.pageYOffset || document.documentElement.scrollTop;

  box.classList.add("hover-tooltip-popup-fullscreen");
  max.classList.add("hover-tooltip-popup-hidden");
  min.classList.remove("hover-tooltip-popup-hidden");
}


function panzoom_reset(instance, box) {
  // Suppress the debounced save handlers: moveTo/zoomAbs below emit pan/zoom
  // events, and without this flag their debounced callbacks would re-persist an
  // (identity) state right after we clear it, defeating the reset.
  if (box) {
    box.dataset.panzoomSuppressSave = "true";
  }

  // Reset to initial position and default browser zoom level
  instance.moveTo(0, 0);
  instance.zoomAbs(0, 0, DEFAULT_ZOOM_LEVEL);

  // Clear saved zoom state after the reset-triggered events have settled.
  if (box && box.id) {
    setTimeout(() => {
      clearZoomState(box.id);
      delete box.dataset.panzoomSuppressSave;
    }, SAVE_DEBOUNCE_DELAY_MS + 50);
  }
}

function panzoom_zoom_in(instance, box, zoomStep = DEFAULT_ZOOM_STEP) {
  const currentTransform = instance.getTransform();
  // Use symmetric zoom: multiply by (1 + step)
  const deltaAdjustedSpeed = Math.min(0.25, Math.abs(zoomStep * 100 / 128));
  const scaleMultiplier = 1 + deltaAdjustedSpeed;
  const newScale = currentTransform.scale * scaleMultiplier;

  // Get the center of the box for zooming
  const rect = box.getBoundingClientRect();
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;

  instance.zoomAbs(centerX, centerY, newScale);
}

function panzoom_zoom_out(instance, box, zoomStep = DEFAULT_ZOOM_STEP) {
  const currentTransform = instance.getTransform();
  // Use symmetric zoom: divide by (1 + step), which is equivalent to multiply by 1/(1 + step)
  const deltaAdjustedSpeed = Math.min(0.25, Math.abs(zoomStep * 100 / 128));
  const scaleMultiplier = 1 / (1 + deltaAdjustedSpeed);
  const newScale = Math.max(currentTransform.scale * scaleMultiplier, 0.1); // Prevent negative zoom

  // Get the center of the box for zooming
  const rect = box.getBoundingClientRect();
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;

  instance.zoomAbs(centerX, centerY, newScale);
}

function add_buttons(box, instance, zoomStep = DEFAULT_ZOOM_STEP) {
  // Use scoped selectors to ensure we only affect elements within this specific box
  let reset = box.querySelector(".hover-tooltip-popup-reset");
  let max = box.querySelector(".hover-tooltip-popup-max");
  let min = box.querySelector(".hover-tooltip-popup-min");
  let info = box.querySelector(".hover-tooltip-popup-info");
  let zoom_in = box.querySelector(".hover-tooltip-popup-zoom-in");
  let zoom_out = box.querySelector(".hover-tooltip-popup-zoom-out");

  // Debug: Ensure we have the correct box context
  if (!box.id) {
    console.warn("Panzoom box missing ID, this could cause scoping issues");
  }

  reset.addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    panzoom_reset(instance, box); // Always reset to default browser zoom level
  });

  if (zoom_in != undefined) {
    zoom_in.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      panzoom_zoom_in(instance, box, zoomStep);
    });
  }

  if (zoom_out != undefined) {
    zoom_out.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      panzoom_zoom_out(instance, box, zoomStep);
    });
  }

  if (info != undefined) {
    info.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      // Find the info box in this container
      const infoBox = box.querySelector(".hover-tooltip-popup-info-box, .hover-tooltip-popup-info-box-top");

      if (infoBox) {
        // Simple class-based toggle that matches how other buttons work
        if (infoBox.classList.contains("hover-tooltip-popup-hidden")) {
          infoBox.classList.remove("hover-tooltip-popup-hidden");
        } else {
          infoBox.classList.add("hover-tooltip-popup-hidden");
        }
      }
    });
  }
  if (max != undefined) {
    max.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      maximize(instance, box, max, min);
    });
  }
  if (min != undefined) {
    min.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      minimize(instance, box, max, min); // Always reset to default browser zoom level
    });
  }
  // Escape exits fullscreen. Listen on document, not the box: a <div> has no keyboard
  // focus by default (no tabindex), so a keydown bound to the box would never fire unless
  // the user happened to focus something inside it. The handler is gated on this box being
  // in fullscreen, so it is a no-op otherwise and never interferes with other Escape uses.
  if (min != undefined && max != undefined) {
    document.addEventListener("keydown", function (e) {
      if (
        (e.key === "Escape" || e.keyCode === 27) &&
        box.classList.contains("hover-tooltip-popup-fullscreen")
      ) {
        minimize(instance, box, max, min);
      }
    });
  }
}

// Canvas-style navigation (direct manipulation, like an infinite canvas), layered on
// top of panzoom's public API. The library's own mouse/wheel handlers are vetoed (see
// beforeWheel/beforeMouseDown), so we own input:
//
//   - Wheel / trackpad two-finger drag (no ctrl) -> PAN. Browsers report trackpad
//     scrolling as wheel events with deltaX/deltaY and ctrlKey=false.
//   - Ctrl/Cmd + wheel, and trackpad pinch (which the browser synthesizes as a wheel
//     event with ctrlKey=true) -> ZOOM, centered on the cursor.
//   - Right-mouse drag -> PAN (the box sets oncontextmenu="return false", so no menu).
//
// Left click is left untouched, so clicking diagram nodes and hovering/clicking inside
// tooltips keeps working.
function setupCanvasNavigation(elem, box, instance, zoomStep) {
  // Wheel-zoom speed must feel consistent whether the input is a chunky mouse notch
  // (large deltaY, few events) or a fine trackpad pinch (tiny deltaY, many events).
  // We normalize deltaY across deltaMode to pixels, express it as a fraction of one
  // typical mouse notch, then clamp the per-event zoom into [MIN, MAX]:
  //   - MAX caps a single mouse notch so it isn't jarringly fast (Linux mice).
  //   - MIN floors tiny trackpad steps so a pinch isn't sluggish (macOS trackpads).
  // The configured zoom_step scales the curve (default 0.2 == 1x).
  const WHEEL_PX_PER_NOTCH = 120; // a typical mouse wheel notch in pixel mode
  const WHEEL_MAX_STEP = 0.12; // largest zoom fraction per wheel event
  const WHEEL_MIN_STEP = 0.012; // smallest zoom fraction per wheel event (tames macOS pinch)
  const WHEEL_LINE_PX = 16; // approx px per line for deltaMode === 1

  function wheelScaleMultiplier(e) {
    let px = e.deltaY;
    if (e.deltaMode === 1) {
      px *= WHEEL_LINE_PX; // lines -> px
    } else if (e.deltaMode === 2) {
      px *= box.clientHeight || 800; // pages -> px
    }
    const sign = Math.sign(px);
    if (sign === 0) {
      return 1;
    }
    const ratio = (Math.abs(px) / WHEEL_PX_PER_NOTCH) * (zoomStep / DEFAULT_ZOOM_STEP);
    const step = Math.min(WHEEL_MAX_STEP, Math.max(WHEEL_MIN_STEP, ratio * WHEEL_MAX_STEP));
    return 1 - sign * step;
  }

  // Wheel: zoom when ctrl/meta is held (or a pinch gesture sets ctrlKey), else pan.
  box.addEventListener(
    "wheel",
    function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.ctrlKey || e.metaKey) {
        const multiplier = wheelScaleMultiplier(e);
        if (multiplier !== 1) {
          instance.zoomTo(e.clientX, e.clientY, multiplier);
        }
      } else {
        // Two-finger trackpad drag (or wheel) pans the diagram.
        instance.moveBy(-e.deltaX, -e.deltaY, false);
      }
    },
    { passive: false },
  );

  // Right-mouse drag pans, with two deliberate carve-outs:
  //   - Shift+right-click is reserved for the browser's native context menu (Copy,
  //     Inspect, ...). We neither pan nor suppress the menu when Shift is held.
  //   - Panning self-heals: mousemove checks e.buttons, so if a mouseup is ever missed
  //     (the context menu grabbed it, or the release happened off-window) the pan stops
  //     instead of sticking to the cursor.
  let panning = false;
  let lastX = 0;
  let lastY = 0;

  function stopPanning() {
    panning = false;
  }

  box.addEventListener("mousedown", function (e) {
    // Only a plain right-button press starts a canvas pan; left click stays free, and
    // Shift+right-click is left for the browser menu.
    if (e.button !== 2 || e.shiftKey) {
      return;
    }
    e.preventDefault();
    panning = true;
    lastX = e.clientX;
    lastY = e.clientY;
  });

  window.addEventListener("mousemove", function (e) {
    if (!panning) {
      return;
    }
    // Bit 2 of e.buttons is the right button. If it is no longer held, a mouseup was
    // missed — stop panning rather than getting stuck following the cursor.
    if ((e.buttons & 2) === 0) {
      stopPanning();
      return;
    }
    instance.moveBy(e.clientX - lastX, e.clientY - lastY, false);
    lastX = e.clientX;
    lastY = e.clientY;
  });

  window.addEventListener("mouseup", function (e) {
    if (e.button === 2) {
      stopPanning();
    }
  });
  // Releasing outside the window or losing focus must also end a pan.
  window.addEventListener("blur", stopPanning);

  // Suppress the context menu on a plain right-click so a right-drag never opens it,
  // but let Shift+right-click through to the browser's native menu (and make sure we
  // are not left in a panning state when the menu opens).
  box.addEventListener("contextmenu", function (e) {
    if (e.shiftKey) {
      stopPanning();
      return;
    }
    e.preventDefault();
  });
}

// Best-effort macOS detection so the hint can name the right keys/gestures.
function isMacOS() {
  const platform =
    (navigator.userAgentData && navigator.userAgentData.platform) ||
    navigator.platform ||
    navigator.userAgent ||
    "";
  return /mac|iphone|ipad|ipod/i.test(platform);
}

// Set the per-box hint text at runtime. Done here (not at build time) because the
// useful wording depends on the OS (Cmd vs Ctrl, trackpad vs wheel) and the active
// navigation mode, neither of which is known when the static HTML is generated.
function setHintText(box, navigation, key) {
  const hint = box.querySelector(
    ".hover-tooltip-popup-info-box, .hover-tooltip-popup-info-box-top",
  );
  if (!hint) {
    return;
  }
  const mac = isMacOS();
  let text;
  if (navigation === "canvas") {
    const zoomKey = mac ? "⌘" : "Ctrl";
    // In canvas mode left click is free (select nodes / click links); spell out the
    // non-obvious ways to MOVE the diagram, plus how to zoom.
    const moveGesture = mac ? "Two-finger drag or right-drag" : "Scroll or right-drag";
    const zoomGesture = mac ? `pinch or ${zoomKey}+scroll` : `${zoomKey}+scroll`;
    text = `${moveGesture} to move • ${zoomGesture} to zoom`;
  } else {
    const keyLabels = {
      alt: mac ? "⌥ Option" : "Alt",
      ctrl: mac ? "⌃ Control" : "Ctrl",
      shift: "Shift",
    };
    if (key === "none") {
      text = "Drag to move the diagram • scroll to zoom";
    } else {
      const label = keyLabels[key] || "the modifier key";
      text = `Hold ${label} and drag to move • ${label}+scroll to zoom`;
    }
  }
  hint.textContent = text;
}

function activate_zoom_pan() {
  let boxes = document.querySelectorAll(".hover-tooltip-popup-box");

  let meta_tag = document.querySelector('meta[name="hover-tooltip-popup-data"]');

  let panzoomData = {};
  let selectors = [".hover-tooltip-popup-content"]; // Default selector
  let initialZoomLevel = DEFAULT_ZOOM_LEVEL; // Default zoom level
  let zoomStep = DEFAULT_ZOOM_STEP; // Default zoom step
  let buttonsSize = "1.25em"; // Default button size

  let navigation = "canvas"; // Default navigation mode
  try {
    panzoomData = JSON.parse(meta_tag.content);
    selectors = panzoomData.selectors || [];
    initialZoomLevel = panzoomData.initial_zoom_level ?? DEFAULT_ZOOM_LEVEL;
    zoomStep = panzoomData.zoom_step ?? DEFAULT_ZOOM_STEP;
    buttonsSize = panzoomData.buttons_size ?? "1.25em";
    navigation = panzoomData.navigation ?? "canvas";
  } catch (e) {
    console.warn('Failed to parse panzoom data:', e);
  }

  // Apply custom button size to all buttons
  const style = document.createElement('style');
  style.textContent = `
    .hover-tooltip-popup-button {
      width: ${buttonsSize} !important;
      height: ${buttonsSize} !important;
    }
  `;
  document.head.appendChild(style);

  boxes.forEach((box) => {
    let key = box.dataset.key;
    let elem;

    selectors.every((selector) => {
      elem = box.querySelector(selector);

      if (elem != undefined) {
        return false;
      }
      return true;
    });

    if (elem == undefined) {
      return;
    }

    if (
      (elem.nodeName == "DIV" || elem.nodeName == "IMG") &&
      !elem.dataset.zoom
    ) {
      elem.dataset.zoom = true;

      const canvas = navigation === "canvas";

      // panzoom's beforeWheel/beforeMouseDown VETO the built-in handler when they
      // return truthy. In classic mode the configured modifier key ENABLES pan/zoom
      // while held, so we veto only when the required modifier is absent. `none`
      // means always on (never veto). In canvas mode we always veto and drive input
      // ourselves (see setupCanvasNavigation).
      function classicVeto(e) {
        switch (key) {
          case "ctrl":
            return !e.ctrlKey; // veto unless ctrl held
          case "shift":
            return !e.shiftKey;
          case "alt":
            return !e.altKey;
          default: // "none": pan/zoom always active
            return false;
        }
      }

      let instance = panzoom(elem, {
        minZoom: 0.5,
        zoomSpeed: zoomStep,
        beforeWheel: function (e) {
          return canvas ? true : classicVeto(e);
        },
        beforeMouseDown: function (e) {
          return canvas ? true : classicVeto(e);
        },
        zoomDoubleClickSpeed: 1,
      });

      if (canvas) {
        setupCanvasNavigation(elem, box, instance, zoomStep);
      }

      // Intercept keyboard zoom events to use our symmetric zoom functions
      box.addEventListener('keydown', function(e) {
        // Check for zoom keys: + (187, 107) and - (189, 109)
        if (e.keyCode === 187 || e.keyCode === 107) {
          // Plus key - zoom in
          e.preventDefault();
          e.stopPropagation();
          panzoom_zoom_in(instance, box, zoomStep);
          return false;
        } else if (e.keyCode === 189 || e.keyCode === 109) {
          // Minus key - zoom out
          e.preventDefault();
          e.stopPropagation();
          panzoom_zoom_out(instance, box, zoomStep);
          return false;
        }
      }, true); // Use capture phase to intercept before panzoom processes it

      // Load saved zoom state or use initial zoom level
      const savedState = loadZoomState(box.id);
      if (savedState) {
        // Apply saved zoom state
        instance.zoomAbs(0, 0, savedState.scale);
        instance.moveTo(savedState.x, savedState.y);
      } else if (initialZoomLevel !== DEFAULT_ZOOM_LEVEL) {
        // Apply configured initial zoom level
        instance.zoomAbs(0, 0, initialZoomLevel);
      }

      // Save zoom state when it changes
      let zoomSaveTimeout;
      let panSaveTimeout;
      instance.on('zoom', function() {
        // Debounce saving to avoid excessive localStorage writes
        clearTimeout(zoomSaveTimeout);
        zoomSaveTimeout = setTimeout(() => {
          if (box.dataset.panzoomSuppressSave) return;
          const transform = instance.getTransform();
          saveZoomState(box.id, transform);
        }, SAVE_DEBOUNCE_DELAY_MS);
      });

      instance.on('pan', function() {
        // Debounce saving to avoid excessive localStorage writes
        clearTimeout(panSaveTimeout);
        panSaveTimeout = setTimeout(() => {
          if (box.dataset.panzoomSuppressSave) return;
          const transform = instance.getTransform();
          saveZoomState(box.id, transform);
        }, SAVE_DEBOUNCE_DELAY_MS);
      });

      add_buttons(box, instance, zoomStep);
      setHintText(box, navigation, key);
    }
  });

  // Tooltips are independent of pan/zoom: wire them on every poll too, so they
  // work even for diagrams that never got a hover-tooltip-popup-box (e.g. small Mermaid
  // diagrams below the auto-enable threshold).
  activate_tooltips();
}

// === Hover tooltips ========================================================

const TOOLTIP_OFFSET = 12; // px gap between a node and its popover
const TOOLTIP_CLOSE_DELAY = 250; // ms grace period so the cursor can move into the popover
const TOOLTIP_MAX_SCALE = 4; // cap how large the popover grows when the diagram is zoomed in

// Resolve the rendered diagram SVG that a tooltips-data div annotates. The div
// immediately follows its diagram in the DOM; that sibling is either the diagram
// element itself (un-wrapped, e.g. a small Mermaid diagram) or a `.hover-tooltip-popup-box`
// wrapping it. When wrapped, the box also contains the control-button icon SVGs,
// so skip any SVG that lives inside the panzoom chrome (nav/buttons).
function findTooltipSvg(tooltipsDiv) {
  const sibling = tooltipsDiv.previousElementSibling;
  if (!sibling) {
    return null;
  }
  if (sibling.tagName === "svg") {
    return sibling;
  }
  for (const svg of sibling.querySelectorAll("svg")) {
    if (!svg.closest("nav, .hover-tooltip-popup-button")) {
      return svg;
    }
  }
  return null;
}

// Find the SVG node group for a label among a diagram's node groups, by exact text.
function findNodeByText(svg, text) {
  const nodes = svg.querySelectorAll("g.node");
  for (const g of nodes) {
    if (g.textContent.trim() === text) {
      return g;
    }
  }
  return null;
}

// Find the SVG node group for one tooltip entry, by Mermaid node id or, failing
// that, by visible label text. Mermaid node groups carry ids shaped like
// `<type>-<id>-<n>` where <type> is the diagram kind (`flowchart`, `state`, ...),
// optionally prefixed with a per-diagram token, e.g.
// `mermaid-<timestamp>-flowchart-<id>-<n>`. We match the `<type>-<id>-` segment at the
// start of the id or after such a prefix. When no id matches (e.g. diagram kinds that
// don't embed the node id in the group id), fall back to matching the visible label.
function findTooltipTarget(svg, entry) {
  const nodeId = entry.dataset.nodeId;
  if (nodeId) {
    const escaped = (window.CSS && CSS.escape) ? CSS.escape(nodeId) : nodeId;
    const target = svg.querySelector(
      `g[id^="flowchart-${escaped}-"], g[id*="-flowchart-${escaped}-"], ` +
        `g[id^="state-${escaped}-"], g[id*="-state-${escaped}-"]`,
    );
    // Fall back to the label text: a node id like `Processing` is also the label.
    return target || findNodeByText(svg, nodeId);
  }
  const nodeText = entry.dataset.nodeText;
  if (nodeText) {
    return findNodeByText(svg, nodeText);
  }
  return null;
}

// Effective zoom scale applied to a node by the pan/zoom transforms above it.
// pan/zoom applies a CSS matrix to the diagram container, so the product of the
// x-scale (matrix `a`) of every transformed ancestor is the node's on-screen scale.
// Plain translate transforms contribute a factor of 1, so they don't affect it.
function getZoomScale(node) {
  let scale = 1;
  let el = node;
  while (el && el !== document.body) {
    const transform = window.getComputedStyle(el).transform;
    if (transform && transform !== "none" && typeof DOMMatrixReadOnly !== "undefined") {
      try {
        const a = new DOMMatrixReadOnly(transform).a;
        if (a) {
          scale *= a;
        }
      } catch (e) {
        /* unparsable transform; ignore */
      }
    }
    el = el.parentElement;
  }
  // Never shrink below the base size (keeps text readable when zoomed out); cap the
  // growth so a heavily zoomed diagram doesn't produce an unusably huge popover.
  return Math.max(1, Math.min(scale, TOOLTIP_MAX_SCALE));
}

function positionTooltip(popover, node) {
  const rect = node.getBoundingClientRect();
  // Scale the whole popover (text and any image) to track the diagram's zoom.
  const scale = getZoomScale(node);
  popover.style.transformOrigin = "top left";
  popover.style.transform = scale === 1 ? "" : `scale(${scale})`;

  // offsetWidth/Height are the unscaled box; the rendered box is scale times bigger.
  const popWidth = popover.offsetWidth * scale;
  const popHeight = popover.offsetHeight * scale;

  let top = rect.top + rect.height / 2 - popHeight / 2;
  // Default: to the left of the node so the node stays visible.
  let left = rect.left - popWidth - TOOLTIP_OFFSET;

  // Not enough room on the left → flip to the right.
  if (left < 0) {
    left = rect.right + TOOLTIP_OFFSET;
  }
  // Clamp to the viewport so it never renders off-screen.
  if (left + popWidth > window.innerWidth) {
    left = Math.max(0, window.innerWidth - popWidth - TOOLTIP_OFFSET);
  }
  top = Math.max(0, Math.min(top, window.innerHeight - popHeight));

  // transform-origin is top-left, so left/top place the scaled box's top-left corner.
  popover.style.top = `${top}px`;
  popover.style.left = `${left}px`;
}

function attachTooltipHandlers(node, contentHtml) {
  let popover = null;
  let closeTimer = null;

  function cancelClose() {
    if (closeTimer !== null) {
      clearTimeout(closeTimer);
      closeTimer = null;
    }
  }

  function hide() {
    cancelClose();
    if (popover) {
      popover.remove();
      popover = null;
    }
  }

  // Close after a short grace period so the cursor can travel from the node into
  // the popover (and back) without it vanishing. Hovering either the node or the
  // popover cancels a pending close, so the popover stays open as long as the
  // pointer is over either one — letting the user select its text or click links.
  function scheduleClose() {
    cancelClose();
    closeTimer = setTimeout(hide, TOOLTIP_CLOSE_DELAY);
  }

  function show() {
    cancelClose();
    if (popover) {
      return;
    }
    popover = document.createElement("div");
    popover.className = "hover-tooltip-popup-tooltip-popover";
    popover.innerHTML = contentHtml;
    popover.addEventListener("mouseenter", cancelClose);
    popover.addEventListener("mouseleave", scheduleClose);
    // Appended to body (not the node) so it escapes SVG/overflow/transform
    // contexts; position:fixed + getBoundingClientRect keep it accurate under
    // any pan/zoom transform. Recomputed each enter.
    document.body.appendChild(popover);
    positionTooltip(popover, node);
  }

  node.addEventListener("mouseenter", show);
  node.addEventListener("mouseleave", scheduleClose);
}

// Wire one tooltips-data div to its diagram. Returns true once the diagram's
// SVG exists and handlers are attached, false if the SVG is not rendered yet.
function wireTooltips(tooltipsDiv) {
  if (tooltipsDiv.dataset.tooltipsWired) {
    return true;
  }
  const svg = findTooltipSvg(tooltipsDiv);
  if (!svg) {
    return false; // diagram not rendered yet
  }
  tooltipsDiv.dataset.tooltipsWired = "true";

  tooltipsDiv.querySelectorAll("[data-node-id], [data-node-text]").forEach((entry) => {
    const target = findTooltipTarget(svg, entry);
    if (target) {
      attachTooltipHandlers(target, entry.innerHTML);
    }
  });
  return true;
}

function activate_tooltips() {
  document.querySelectorAll(".hover-tooltip-popup-tooltips-data").forEach((tooltipsDiv) => {
    if (wireTooltips(tooltipsDiv) || tooltipsDiv.dataset.tooltipsObserving) {
      return;
    }
    // Diagram (e.g. Mermaid) renders its SVG asynchronously and may not be ready
    // within the activation poll window. Watch the diagram container and wire the
    // tooltips the instant the SVG is injected, then stop observing.
    const sibling = tooltipsDiv.previousElementSibling;
    if (!sibling) {
      return;
    }
    tooltipsDiv.dataset.tooltipsObserving = "true";
    const observer = new MutationObserver(() => {
      if (wireTooltips(tooltipsDiv)) {
        observer.disconnect();
      }
    });
    observer.observe(sibling, { childList: true, subtree: true });
  });
}

// handle themes differently
const pz_theme_meta = document.querySelector('meta[name="hover-tooltip-popup-theme"]');
const pz_theme = pz_theme_meta ? pz_theme_meta.content : "";

function pollActivateZoomPan() {
  const interval = setInterval(activate_zoom_pan, 1000);
  setTimeout(function () {
    clearInterval(interval);
  }, 5000);
}

// Material for MkDocs swaps page content via instant-loading, exposing the
// `document$` observable. Use it when present; otherwise fall back to polling.
if (pz_theme == "material" && typeof document$ !== "undefined") {
  document$.subscribe(pollActivateZoomPan);
} else {
  pollActivateZoomPan();
}
