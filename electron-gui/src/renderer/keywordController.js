import {
  errorMessage,
  escapeAttr,
  escapeHtml,
} from "./utils.js";

export function createKeywordController({
  state,
  el,
  api,
  appendLog,
  detectLanguage,
  isExecutableFile,
  renderActiveFile,
  renderFileTree,
  selectFile,
  setDirty,
  syncEditorCompletionContext,
}) {
  function handleDefinitionRequest(request) {
    if (!request || !request.keywordName) {
      return;
    }
    goToKeywordDefinition(request.keywordName, {
      showAll: Boolean(request.showAll),
      source: request.source || "editor",
    });
  }

  async function goToKeywordDefinition(keywordName, options = {}) {
    if (!state.snapshot) {
      appendLog("warn", "请先打开一个项目");
      return;
    }
    if (!state.currentFile || state.readonlySource || !isExecutableFile(state.currentFile)) {
      appendLog("warn", "当前文件不支持关键字跳转");
      return;
    }

    try {
      const result = await api.findKeywordDefinitions({
        projectRoot: state.snapshot.project.rootPath,
        keywordName,
      });
      const definitions = Array.isArray(result.definitions) ? result.definitions : [];
      if (definitions.length === 0) {
        appendLog("warn", `未找到关键字定义: ${keywordName}`);
        return;
      }
      const target = chooseDefinitionTarget(definitions, options);
      await openDefinitionTarget(target);
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  function chooseDefinitionTarget(definitions, options = {}) {
    if (definitions.length > 1 && options.showAll) {
      appendLog(
        "info",
        `Definition candidates: ${definitions.map((item) => `${item.sourceType}:${item.path}:${item.line}`).join(" | ")}`,
      );
    }
    return definitions[0];
  }

  async function openDefinitionTarget(definition) {
    if (definition.relativePath) {
      await selectFile(definition.relativePath);
      CM6.scrollToLine(definition.line);
      appendLog("info", `Go to definition: ${definition.name} -> ${definition.relativePath}:${definition.line}`);
      return;
    }

    await openExternalReadonlySource(definition);
  }

  async function openExternalReadonlySource(definition) {
    const result = await api.readSourceFile({
      projectRoot: state.snapshot.project.rootPath,
      path: definition.path,
    });
    state.currentFile = result.path;
    state.readonlySource = {
      ...definition,
      path: result.path,
    };
    state.currentDebugLine = null;
    state.debugStartLine = null;
    state.debugSelection = null;
    state.debugPaused = false;
    CM6.setContent(result.content);
    CM6.setLanguage(result.language || detectLanguage(result.path));
    CM6.setEnabled(false);
    syncEditorCompletionContext();
    setDirty(false);
    renderActiveFile();
    renderFileTree();
    CM6.scrollToLine(definition.line);
    appendLog("info", `Go to readonlySource: ${definition.name} -> ${result.path}:${definition.line}`);
  }

  function resetKeywordBrowser() {
    if (state.keywordSearchTimer) {
      clearTimeout(state.keywordSearchTimer);
      state.keywordSearchTimer = null;
    }
    state.keywordPanelOpen = false;
    state.keywordLoadSeq += 1;
    state.keywordLoading = false;
    state.keywords = [];
    if (el.keywordPanel) {
      el.keywordPanel.hidden = true;
    }
    if (el.keywordSearch) {
      el.keywordSearch.value = "";
    }
    if (el.keywordStatus) {
      el.keywordStatus.textContent = "未加载";
    }
    if (el.keywordList) {
      el.keywordList.innerHTML = "";
    }
  }

  async function handleRefreshDefinitions() {
    if (!state.snapshot) {
      appendLog("warn", "请先打开一个项目");
      return;
    }
    const projectRoot = state.snapshot.project.rootPath;
    try {
      if (typeof api.invalidateDefinitionCache === "function") {
        await api.invalidateDefinitionCache(projectRoot);
      }
      if (state.keywordPanelOpen) {
        loadKeywords(el.keywordSearch ? el.keywordSearch.value.trim() : "");
      }
      appendLog("info", "定义缓存已刷新，关键字索引已更新");
    } catch (error) {
      appendLog("error", `刷新定义缓存失败: ${errorMessage(error)}`);
    }
  }

  function closeKeywordPanel() {
    state.keywordPanelOpen = false;
    if (el.keywordPanel) {
      el.keywordPanel.hidden = true;
    }
  }

  function toggleKeywordPanel() {
    if (!state.snapshot) {
      appendLog("warn", "请先打开一个项目");
      return;
    }

    state.keywordPanelOpen = !state.keywordPanelOpen;
    el.keywordPanel.hidden = !state.keywordPanelOpen;

    if (!state.keywordPanelOpen) {
      return;
    }

    el.keywordSearch.focus();
    loadKeywords(el.keywordSearch.value.trim());
  }

  function handleKeywordSearchInput() {
    if (state.keywordSearchTimer) {
      clearTimeout(state.keywordSearchTimer);
    }
    state.keywordSearchTimer = setTimeout(() => {
      state.keywordSearchTimer = null;
      loadKeywords(el.keywordSearch.value.trim());
    }, 220);
  }

  async function loadKeywords(query = "") {
    if (!state.snapshot || !state.keywordPanelOpen) {
      return;
    }

    const loadSeq = state.keywordLoadSeq + 1;
    state.keywordLoadSeq = loadSeq;
    state.keywordLoading = true;
    el.keywordStatus.textContent = query ? `查找: ${query}` : "加载中";
    el.keywordList.innerHTML = `<p class="empty">加载关键字...</p>`;

    try {
      const result = await api.listKeywords({
        projectRoot: state.snapshot.project.rootPath,
        query,
        limit: 80,
      });
      if (loadSeq !== state.keywordLoadSeq) {
        return;
      }
      state.keywords = Array.isArray(result.keywords) ? result.keywords : [];
      state.keywordLoading = false;
      renderKeywordList(result.summary || {});
    } catch (error) {
      if (loadSeq !== state.keywordLoadSeq) {
        return;
      }
      state.keywordLoading = false;
      state.keywords = [];
      el.keywordStatus.textContent = "加载失败";
      el.keywordList.innerHTML = `<p class="empty">无法加载关键字</p>`;
      appendLog("error", errorMessage(error));
    }
  }

  function renderKeywordList(summary = {}) {
    if (!state.keywordPanelOpen) {
      return;
    }
    const visibleCount = state.keywords.length;
    const totalCount = Number(summary.total_count) || visibleCount;
    el.keywordStatus.textContent = `${visibleCount}/${totalCount} 关键字`;

    if (visibleCount === 0) {
      el.keywordList.innerHTML = `<p class="empty">没有匹配的关键字</p>`;
      return;
    }

    el.keywordList.innerHTML = state.keywords
      .map(renderKeywordRow)
      .join("");
  }

  function handleKeywordListClick(event) {
    const button = event.target && typeof event.target.closest === "function"
      ? event.target.closest(".keyword-row[data-index]")
      : null;
    if (!button || !el.keywordList.contains(button)) {
      return;
    }
    insertKeyword(Number(button.dataset.index));
  }

  function renderKeywordRow(keyword, index) {
    const parameters = (keyword.parameters || [])
      .map((param) => param.name || param.mapping)
      .filter(Boolean)
      .slice(0, 4);
    const parameterText = parameters.length > 0
      ? parameters.join(", ")
      : "无参数";
    const metaParts = [
      keyword.categoryName,
      keyword.source,
      keyword.documentation,
    ].filter(Boolean);

    return `
      <button class="keyword-row" type="button" data-index="${index}">
        <span class="keyword-name">
          <strong>${escapeHtml(keyword.name)}</strong>
          <span title="${escapeAttr(metaParts.join(" · "))}">${escapeHtml(metaParts.join(" · ") || "pytest-dsl 关键字")}</span>
        </span>
        <span class="keyword-param" title="${escapeAttr(parameterText)}">${escapeHtml(parameterText)}</span>
      </button>
    `;
  }

  function insertKeyword(index) {
    const keyword = state.keywords[index];
    if (!keyword) {
      return;
    }
    if (!canInsertKeywordIntoCurrentFile()) {
      appendLog("warn", "打开可编辑的 DSL 或 Resource 文件后可插入关键字");
      return;
    }
    const snippet = buildKeywordSnippet(keyword);
    CM6.insertText(snippet);
    appendLog("info", `Inserted keyword: ${keyword.name}`);
  }

  function canInsertKeywordIntoCurrentFile() {
    return Boolean(
      state.currentFile &&
        !state.readonlySource &&
        isExecutableFile(state.currentFile),
    );
  }

  function buildKeywordSnippet(keyword) {
    const parameters = (keyword.parameters || [])
      .map((param) => param.name || param.mapping)
      .filter(Boolean);
    if (parameters.length === 0) {
      return `[${keyword.name}]`;
    }
    return `[${keyword.name}], ${parameters.map((name) => `${name}: `).join(", ")}`;
  }

  return {
    closeKeywordPanel,
    handleDefinitionRequest,
    handleKeywordListClick,
    handleKeywordSearchInput,
    handleRefreshDefinitions,
    resetKeywordBrowser,
    toggleKeywordPanel,
  };
}
