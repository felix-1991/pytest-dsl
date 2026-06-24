import {
  TREE_FALLBACK_VIEW_ROWS,
  TREE_RENDER_OVERSCAN,
  TREE_ROW_HEIGHT,
} from "./state.js";

export function virtualTreeWindow(container, totalRows) {
  const viewportHeight = container && container.clientHeight
    ? container.clientHeight
    : TREE_ROW_HEIGHT * TREE_FALLBACK_VIEW_ROWS;
  const scrollTop = container && container.scrollTop ? container.scrollTop : 0;
  const start = Math.max(
    0,
    Math.floor(scrollTop / TREE_ROW_HEIGHT) - TREE_RENDER_OVERSCAN,
  );
  const end = Math.min(
    totalRows,
    Math.ceil((scrollTop + viewportHeight) / TREE_ROW_HEIGHT) + TREE_RENDER_OVERSCAN,
  );
  return {
    start,
    end,
    topSpacer: start * TREE_ROW_HEIGHT,
    bottomSpacer: Math.max(0, totalRows - end) * TREE_ROW_HEIGHT,
  };
}

export function renderVirtualTreeRows(container, rows, renderRow) {
  const window = virtualTreeWindow(container, rows.length);
  const visibleRows = rows.slice(window.start, window.end);
  container.innerHTML = `
    <div class="tree-virtual-spacer" style="--tree-spacer-height: ${window.topSpacer}px"></div>
    <div class="tree-virtual-window">
      ${visibleRows.map(renderRow).join("")}
    </div>
    <div class="tree-virtual-spacer" style="--tree-spacer-height: ${window.bottomSpacer}px"></div>
  `;
}
