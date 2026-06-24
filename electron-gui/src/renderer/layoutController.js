import {
  LAYOUT_SIZES,
  LAYOUT_STORAGE_KEY,
} from "./state.js";
import { clamp } from "./utils.js";

export function createLayoutController() {
  function initializeLayoutSizing() {
    const saved = readLayoutSizing();
    Object.keys(LAYOUT_SIZES).forEach((kind) => {
      setLayoutSize(kind, saved[kind] || LAYOUT_SIZES[kind].defaultValue, {
        persist: false,
      });
    });
  }

  function bindPanelResizers() {
    document.querySelectorAll("[data-resizer]").forEach((resizer) => {
      const kind = resizer.dataset.resizer;
      if (!LAYOUT_SIZES[kind]) {
        return;
      }
      resizer.addEventListener("pointerdown", (event) =>
        startPanelResize(kind, event),
      );
      resizer.addEventListener("keydown", (event) =>
        handleResizerKeydown(kind, event),
      );
    });
  }

  function startPanelResize(kind, event) {
    if (event.button !== 0) {
      return;
    }
    event.preventDefault();
    const resizer = event.currentTarget;
    if (resizer && typeof resizer.setPointerCapture === "function") {
      resizer.setPointerCapture(event.pointerId);
    }
    const config = LAYOUT_SIZES[kind];
    const startPosition = config.axis === "y" ? event.clientY : event.clientX;
    const startSize = getLayoutSize(kind);
    let pendingSize = startSize;
    let animationFrame = null;
    document.body.classList.add(
      config.axis === "y" ? "is-resizing-console" : "is-resizing-layout",
    );

    const flushResize = () => {
      animationFrame = null;
      setLayoutSize(kind, pendingSize, { persist: false });
    };

    const handlePointerMove = (moveEvent) => {
      const currentPosition = config.axis === "y"
        ? moveEvent.clientY
        : moveEvent.clientX;
      const delta = currentPosition - startPosition;
      const nextSize = config.axis === "y"
        ? startSize - delta
        : startSize + delta;
      pendingSize = nextSize;
      if (animationFrame === null) {
        animationFrame = requestAnimationFrame(flushResize);
      }
    };

    const stopResize = (event) => {
      if (animationFrame !== null) {
        cancelAnimationFrame(animationFrame);
        flushResize();
      }
      persistLayoutSizing();
      if (
        resizer &&
        typeof resizer.releasePointerCapture === "function" &&
        typeof resizer.hasPointerCapture === "function" &&
        event &&
        resizer.hasPointerCapture(event.pointerId)
      ) {
        resizer.releasePointerCapture(event.pointerId);
      }
      document.body.classList.remove("is-resizing-layout", "is-resizing-console");
      document.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointercancel", stopResize);
    };

    document.addEventListener("pointermove", handlePointerMove);
    document.addEventListener("pointerup", stopResize, { once: true });
    document.addEventListener("pointercancel", stopResize, { once: true });
  }

  function handleResizerKeydown(kind, event) {
    const config = LAYOUT_SIZES[kind];
    const keys = config && config.axis === "y"
      ? ["ArrowUp", "ArrowDown"]
      : ["ArrowLeft", "ArrowRight"];
    if (!keys.includes(event.key)) {
      return;
    }
    event.preventDefault();
    const step = event.shiftKey ? 40 : 16;
    const direction = event.key === "ArrowRight" || event.key === "ArrowUp"
      ? 1
      : -1;
    setLayoutSize(kind, getLayoutSize(kind) + direction * step);
  }

  function setLayoutSize(kind, size, options = {}) {
    const config = LAYOUT_SIZES[kind];
    if (!config) {
      return;
    }
    const clamped = clamp(Math.round(Number(size) || config.defaultValue), config.min, config.max);
    document.documentElement.style.setProperty(config.cssVar, `${clamped}px`);

    const resizer = document.querySelector(`[data-resizer="${kind}"]`);
    if (resizer) {
      resizer.setAttribute("aria-valuemin", String(config.min));
      resizer.setAttribute("aria-valuemax", String(config.max));
      resizer.setAttribute("aria-valuenow", String(clamped));
    }

    if (options.persist !== false) {
      persistLayoutSizing();
    }
  }

  function getLayoutSize(kind) {
    const config = LAYOUT_SIZES[kind];
    if (!config) {
      return 0;
    }
    const rawValue = getComputedStyle(document.documentElement)
      .getPropertyValue(config.cssVar)
      .trim();
    return parseFloat(rawValue) || config.defaultValue;
  }

  function readLayoutSizing() {
    try {
      return JSON.parse(localStorage.getItem(LAYOUT_STORAGE_KEY) || "{}");
    } catch (_error) {
      return {};
    }
  }

  function persistLayoutSizing() {
    try {
      localStorage.setItem(
        LAYOUT_STORAGE_KEY,
        JSON.stringify({
          nav: getLayoutSize("nav"),
          console: getLayoutSize("console"),
        }),
      );
    } catch (_error) {
      // Layout sizing is a convenience preference; failing to persist is harmless.
    }
  }

  return {
    bindPanelResizers,
    getLayoutSize,
    initializeLayoutSizing,
    setLayoutSize,
  };
}
