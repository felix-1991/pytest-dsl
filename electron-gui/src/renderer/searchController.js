import { escapeAttr, escapeHtml, errorMessage } from "./utils.js";

const SEARCH_RESULT_ROW_HEIGHT = 34;
const SEARCH_RESULT_OVERSCAN = 8;
const SEARCH_MAX_MATCHES = 1000;
const SEARCH_BATCH_SIZE = 20;

export function createSearchController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  switchWorkspaceView,
  updateTreePaneForActiveView,
  selectFile,
  reloadOpenFiles,
}) {
  let queuedRenderFrame = null;
  let queuedRenderMessage = "";

  if (typeof api.onProjectSearchEvent === "function") {
    api.onProjectSearchEvent(handleProjectSearchEvent);
  }

  function handleProjectSearchShortcut(event) {
    if (!event || event.defaultPrevented) {
      return;
    }
    const isMeta = event.ctrlKey || event.metaKey;
    if (!isMeta || event.altKey) {
      return;
    }
    const key = event.key.toLowerCase();
    if (event.shiftKey && key === "f") {
      event.preventDefault();
      openProjectSearch({ focus: true });
      return;
    }
    if (event.shiftKey && key === "h") {
      event.preventDefault();
      openProjectSearch({ focus: true, replace: true });
      return;
    }
    if (!event.shiftKey && key === "f") {
      if (state.currentFile && window.CM6 && typeof CM6.openSearch === "function") {
        event.preventDefault();
        CM6.openSearch(false);
      }
      return;
    }
    if (!event.shiftKey && key === "h") {
      if (state.currentFile && window.CM6 && typeof CM6.openSearch === "function") {
        event.preventDefault();
        CM6.openSearch(true);
      }
    }
  }

  function handleProjectSearchInput() {
    state.projectSearch.query = el.projectSearchInput.value;
    clearProjectSearchPreview();
  }

  function handleProjectSearchKeydown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      runProjectSearch({ force: true });
    }
    if (event.key === "Escape") {
      event.preventDefault();
      closeProjectSearch();
    }
  }

  function handleProjectReplaceInput() {
    state.projectSearch.replacement = el.projectReplaceInput.value;
  }

  function openProjectSearch(options = {}) {
    if (state.activeView === "build") {
      switchWorkspaceView("debug");
    }
    state.projectSearch.open = true;
    updateTreePaneForActiveView();
    if (options.replace) {
      state.projectSearch.replaceVisible = true;
    }
    renderProjectSearchPanel();
    const target = options.replace && el.projectReplaceInput
      ? el.projectReplaceInput
      : el.projectSearchInput;
    if (target && options.focus !== false) {
      target.focus();
      target.select();
    }
  }

  function closeProjectSearch() {
    cancelActiveSearch();
    state.projectSearch.loading = false;
    state.projectSearch.open = false;
    updateTreePaneForActiveView();
    renderProjectSearchPanel();
  }

  function toggleProjectSearchPanel() {
    if (state.projectSearch.open) {
      closeProjectSearch();
      return;
    }
    openProjectSearch({ focus: true });
  }

  function toggleProjectReplace() {
    state.projectSearch.replaceVisible = !state.projectSearch.replaceVisible;
    renderProjectSearchPanel();
    const target = state.projectSearch.replaceVisible
      ? el.projectReplaceInput
      : el.projectSearchInput;
    if (target) {
      target.focus();
      target.select();
    }
  }

  function toggleProjectSearchOption(optionName) {
    const options = state.projectSearch.options;
    options[optionName] = !options[optionName];
    clearProjectSearchPreview();
  }

  async function runProjectSearch(options = {}) {
    clearTimeout(state.projectSearch.timer);
    state.projectSearch.timer = null;
    const query = state.projectSearch.query;
    if (!query) {
      cancelActiveSearch();
      state.projectSearch.result = null;
      state.projectSearch.loading = false;
      renderProjectSearchPanel();
      return;
    }
    if (!state.snapshot) {
      cancelActiveSearch();
      state.projectSearch.result = null;
      state.projectSearch.loading = false;
      renderProjectSearchPanel("请先打开项目");
      return;
    }

    const seq = state.projectSearch.seq + 1;
    const searchId = `renderer-search-${seq}-${Date.now()}`;
    state.projectSearch.seq = seq;
    cancelActiveSearch();
    state.projectSearch.activeSearchId = searchId;
    state.projectSearch.loading = true;
    state.projectSearch.error = "";
    state.projectSearch.result = emptyRendererSearchResult(query, searchOptionsForRequest());
    if (el.projectSearchResults) {
      el.projectSearchResults.scrollTop = 0;
    }
    renderProjectSearchPanel();

    try {
      await api.startProjectSearch(state.snapshot.project.rootPath, {
        searchId,
        query,
        options: searchOptionsForRequest(),
      });
    } catch (error) {
      if (state.projectSearch.activeSearchId !== searchId) {
        return;
      }
      state.projectSearch.result = null;
      state.projectSearch.loading = false;
      state.projectSearch.activeSearchId = null;
      renderProjectSearchPanel(errorMessage(error));
    }
  }

  async function replaceAllProjectMatches() {
    const result = state.projectSearch.result;
    if (!state.snapshot || !result || result.totalMatches === 0) {
      showActionFeedback("没有可替换的搜索结果", "warn");
      return;
    }
    const dirtyFiles = state.openFiles.filter((entry) => entry.dirty);
    if (dirtyFiles.length > 0) {
      showActionFeedback("存在未保存文件，请先保存后再进行项目替换", "warn");
      return;
    }
    const confirmed = window.confirm(
      `确认替换 ${result.totalMatches} 处匹配？此操作会直接修改项目文件。`,
    );
    if (!confirmed) {
      return;
    }

    try {
      cancelActiveSearch();
      const replacement = await api.replaceProjectMatches(
        state.snapshot.project.rootPath,
        {
          query: state.projectSearch.query,
          replacement: state.projectSearch.replacement,
          options: searchOptionsForRequest(),
          files: result.files,
        },
      );
      if (replacement.changedFiles.length > 0) {
        await reloadOpenFiles(replacement.changedFiles);
      }
      await runProjectSearch({ force: true });
      const conflictText = replacement.conflicts.length > 0
        ? `，${replacement.conflicts.length} 个文件已跳过`
        : "";
      showActionFeedback(`已替换 ${replacement.replacements} 处${conflictText}`, replacement.conflicts.length > 0 ? "warn" : "pass");
      appendLog("pass", `Project replace: ${replacement.replacements} matches${conflictText}`);
    } catch (error) {
      appendLog("error", errorMessage(error));
      showActionFeedback(`替换失败: ${errorMessage(error)}`, "error");
    }
  }

  async function handleProjectSearchResultsClick(event) {
    const target = event.target.closest("[data-search-result='match']");
    if (!target) {
      return;
    }
    const relativePath = target.dataset.path;
    const line = Number(target.dataset.line) || 1;
    const column = Number(target.dataset.column) || 1;
    switchWorkspaceView("debug");
    await selectFile(relativePath);
    if (window.CM6 && typeof CM6.goToLine === "function") {
      CM6.goToLine(line, column);
    }
  }

  function handleProjectSearchResultsScroll() {
    renderProjectSearchPanel();
  }

  function handleProjectSearchEvent(payload) {
    if (!payload || payload.searchId !== state.projectSearch.activeSearchId) {
      return;
    }
    if (payload.type === "batch") {
      mergeSearchBatch(payload.batch);
      state.projectSearch.loading = true;
      queueProjectSearchRender();
      return;
    }
    if (payload.type === "done") {
      state.projectSearch.result = normalizeSearchResult(payload.summary);
      state.projectSearch.loading = false;
      state.projectSearch.activeSearchId = null;
      queueProjectSearchRender();
      return;
    }
    if (payload.type === "canceled") {
      state.projectSearch.loading = false;
      state.projectSearch.activeSearchId = null;
      queueProjectSearchRender();
      return;
    }
    if (payload.type === "error") {
      state.projectSearch.result = null;
      state.projectSearch.error = payload.message || "搜索失败";
      state.projectSearch.loading = false;
      state.projectSearch.activeSearchId = null;
      queueProjectSearchRender();
    }
  }

  function mergeSearchBatch(batch) {
    const normalized = normalizeSearchResult(batch);
    const current = state.projectSearch.result
      || emptyRendererSearchResult(state.projectSearch.query, searchOptionsForRequest());
    current.scannedFiles += normalized.scannedFiles;
    current.totalMatches += normalized.totalMatches;
    current.truncated = current.truncated || normalized.truncated;
    current.skippedFiles.push(...normalized.skippedFiles);
    current.files.push(...normalized.files);
    current.matchedFiles = current.files.length;
    state.projectSearch.result = current;
  }

  function searchOptionsForRequest() {
    return {
      caseSensitive: state.projectSearch.options.caseSensitive,
      wholeWord: state.projectSearch.options.wholeWord,
      regexp: state.projectSearch.options.regexp,
      maxMatches: SEARCH_MAX_MATCHES,
      maxFileSizeBytes: 2 * 1024 * 1024,
      batchSize: SEARCH_BATCH_SIZE,
    };
  }

  function cancelActiveSearch() {
    const searchId = state.projectSearch.activeSearchId;
    if (!searchId) {
      return;
    }
    state.projectSearch.activeSearchId = null;
    if (typeof api.cancelProjectSearch === "function") {
      api.cancelProjectSearch(searchId).catch(() => {});
    }
  }

  function clearProjectSearchPreview() {
    cancelActiveSearch();
    state.projectSearch.result = null;
    state.projectSearch.error = "";
    state.projectSearch.loading = false;
    renderProjectSearchPanel();
  }

  function queueProjectSearchRender(message = "") {
    if (message) {
      queuedRenderMessage = message;
    }
    if (queuedRenderFrame !== null) {
      return;
    }
    const render = () => {
      queuedRenderFrame = null;
      const nextMessage = queuedRenderMessage;
      queuedRenderMessage = "";
      renderProjectSearchPanel(nextMessage);
    };
    queuedRenderFrame = window.requestAnimationFrame
      ? window.requestAnimationFrame(render)
      : window.setTimeout(render, 16);
  }

  function renderProjectSearchPanel(message = "") {
    if (!el.projectSearchPanel) {
      return;
    }
    el.projectSearchPanel.hidden = !state.projectSearch.open;
    if (el.projectSearchOpenBtn) {
      el.projectSearchOpenBtn.classList.toggle("is-active", state.projectSearch.open);
      el.projectSearchOpenBtn.setAttribute("aria-expanded", String(state.projectSearch.open));
    }
    if (!state.projectSearch.open) {
      return;
    }
    if (el.projectSearchInput && el.projectSearchInput.value !== state.projectSearch.query) {
      el.projectSearchInput.value = state.projectSearch.query;
    }
    if (el.projectReplaceInput && el.projectReplaceInput.value !== state.projectSearch.replacement) {
      el.projectReplaceInput.value = state.projectSearch.replacement;
    }
    if (el.projectReplaceRow) {
      el.projectReplaceRow.hidden = !state.projectSearch.replaceVisible;
    }
    if (el.projectReplaceToggleBtn) {
      el.projectReplaceToggleBtn.classList.toggle("is-active", state.projectSearch.replaceVisible);
      el.projectReplaceToggleBtn.textContent = state.projectSearch.replaceVisible ? "收起" : "替换";
    }
    updateOptionButton(el.projectSearchCaseBtn, state.projectSearch.options.caseSensitive);
    updateOptionButton(el.projectSearchWordBtn, state.projectSearch.options.wholeWord);
    updateOptionButton(el.projectSearchRegexBtn, state.projectSearch.options.regexp);
    const result = state.projectSearch.result;
    const canReplace = (
      state.projectSearch.replaceVisible
      && !state.projectSearch.loading
      && result
      && result.totalMatches > 0
    );
    if (el.projectSearchRunBtn) {
      el.projectSearchRunBtn.disabled = !state.projectSearch.query || state.projectSearch.loading;
    }
    if (el.projectReplaceAllBtn) {
      el.projectReplaceAllBtn.disabled = !canReplace;
    }
    if (el.projectSearchSummary) {
      el.projectSearchSummary.textContent = searchSummaryText(message);
    }
    if (el.projectSearchResults) {
      el.projectSearchResults.innerHTML = renderVirtualSearchRows(message);
    }
  }

  function updateOptionButton(button, active) {
    if (!button) {
      return;
    }
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  }

  function searchSummaryText(message) {
    if (message) {
      return message;
    }
    if (state.projectSearch.error) {
      return state.projectSearch.error;
    }
    const query = state.projectSearch.query;
    if (!query) {
      return "输入内容后点击搜索";
    }
    const result = state.projectSearch.result;
    if (state.projectSearch.loading) {
      const count = result ? result.totalMatches : 0;
      return count > 0 ? `搜索中 · ${count} 个结果` : "搜索中";
    }
    if (!result) {
      return "点击搜索或按 Enter 开始搜索";
    }
    const suffix = result.truncated ? " · 已截断" : "";
    return `${result.totalMatches} 个结果 · ${result.matchedFiles} 个文件${suffix}`;
  }

  function renderVirtualSearchRows(message = "") {
    const empty = emptySearchMessage(message);
    if (empty) {
      return `<p class="empty">${escapeHtml(empty)}</p>`;
    }
    const rows = flattenSearchRows(state.projectSearch.result);
    if (rows.length === 0) {
      return "";
    }
    const viewportHeight = el.projectSearchResults.clientHeight || 360;
    const scrollTop = el.projectSearchResults.scrollTop || 0;
    const start = Math.max(0, Math.floor(scrollTop / SEARCH_RESULT_ROW_HEIGHT) - SEARCH_RESULT_OVERSCAN);
    const end = Math.min(
      rows.length,
      Math.ceil((scrollTop + viewportHeight) / SEARCH_RESULT_ROW_HEIGHT) + SEARCH_RESULT_OVERSCAN,
    );
    const topSpacer = start * SEARCH_RESULT_ROW_HEIGHT;
    const bottomSpacer = Math.max(0, (rows.length - end) * SEARCH_RESULT_ROW_HEIGHT);
    const visibleRows = rows.slice(start, end).map(renderSearchRow).join("");
    return `
      <div class="project-search-virtual-spacer" style="height: ${topSpacer}px"></div>
      ${visibleRows}
      <div class="project-search-virtual-spacer" style="height: ${bottomSpacer}px"></div>
    `;
  }

  function emptySearchMessage(message) {
    if (message) {
      return message;
    }
    if (state.projectSearch.error) {
      return state.projectSearch.error;
    }
    if (!state.projectSearch.query) {
      return "输入内容后点击搜索";
    }
    const result = state.projectSearch.result;
    if (state.projectSearch.loading && (!result || result.totalMatches === 0)) {
      return "搜索中...";
    }
    if (!result) {
      return "点击搜索或按 Enter 开始搜索";
    }
    if (result.totalMatches === 0 && !state.projectSearch.loading) {
      return "没有匹配结果";
    }
    return "";
  }

  function flattenSearchRows(result) {
    const rows = [];
    if (!result) {
      return rows;
    }
    if (result.skippedFiles.length > 0) {
      rows.push({
        type: "note",
        text: `${result.skippedFiles.length} 个大文件已跳过`,
      });
    }
    result.files.forEach((file) => {
      rows.push({ type: "file", file });
      file.matches.forEach((match) => {
        rows.push({ type: "match", file, match });
      });
    });
    return rows;
  }

  function renderSearchRow(row) {
    if (row.type === "note") {
      return `<p class="project-search-note project-search-row">${escapeHtml(row.text)}</p>`;
    }
    if (row.type === "file") {
      return `
        <div class="project-search-file-head project-search-row">
          <strong title="${escapeAttr(row.file.relativePath)}">${escapeHtml(row.file.relativePath)}</strong>
          <span>${row.file.matches.length}</span>
        </div>
      `;
    }
    return renderSearchMatch(row.file, row.match);
  }

  function renderSearchMatch(file, match) {
    return `
      <button
        class="project-search-match project-search-row"
        type="button"
        data-search-result="match"
        data-path="${escapeAttr(file.relativePath)}"
        data-line="${match.line}"
        data-column="${match.column}"
        title="${escapeAttr(file.relativePath)}:${match.line}:${match.column}"
      >
        <span class="project-search-line">${match.line}</span>
        <span class="project-search-preview">${escapeHtml(match.preview)}</span>
      </button>
    `;
  }

  return {
    closeProjectSearch,
    handleProjectReplaceInput,
    handleProjectSearchInput,
    handleProjectSearchKeydown,
    handleProjectSearchResultsClick,
    handleProjectSearchResultsScroll,
    handleProjectSearchShortcut,
    openProjectSearch,
    replaceAllProjectMatches,
    renderProjectSearchPanel,
    runProjectSearch,
    toggleProjectReplace,
    toggleProjectSearchOption,
    toggleProjectSearchPanel,
  };
}

function emptyRendererSearchResult(query, options) {
  return {
    query,
    options,
    scannedFiles: 0,
    matchedFiles: 0,
    totalMatches: 0,
    truncated: false,
    skippedFiles: [],
    files: [],
  };
}

function normalizeSearchResult(result = {}) {
  const files = Array.isArray(result.files) ? result.files : [];
  const skippedFiles = Array.isArray(result.skippedFiles) ? result.skippedFiles : [];
  return {
    query: String(result.query || ""),
    options: result.options || {},
    scannedFiles: Number(result.scannedFiles) || 0,
    matchedFiles: Number(result.matchedFiles) || files.length,
    totalMatches: Number(result.totalMatches) || 0,
    truncated: Boolean(result.truncated),
    skippedFiles,
    files,
  };
}
