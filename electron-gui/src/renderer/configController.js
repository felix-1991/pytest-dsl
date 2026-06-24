import { escapeAttr, escapeHtml, errorMessage, isPlainObject } from "./utils.js";

export function createConfigController({
  state,
  el,
  api,
  appendLog,
  currentCommand,
  previewCommand,
  detectLanguage,
  renderActiveFile,
  refreshRemoteStatuses,
  renderProject,
  updateBuildSummary,
}) {
  function renderConfig() {
    const config = state.snapshot.config;
    const selectedSources = selectedConfigSources({ includeErrors: true });
    el.configSummary.textContent =
      selectedSources.length <= 1
        ? selectedSources[0]
          ? selectedSources[0].relativePath
          : "未选择配置"
        : `${selectedSources[0].relativePath} +${selectedSources.length - 1}`;
    el.configCount.textContent = `${selectedSources.length}/${config.sources.length}`;

    if (config.sources.length === 0) {
      el.configList.innerHTML = `<p class="empty">未找到可加载的 YAML 配置</p>`;
    } else {
      el.configList.innerHTML = config.sources
        .map(
          (source) => `
      <label class="config-option${source.ok ? "" : " is-error"}${source.defaultSelected ? " is-default" : ""}">
        <input
          type="checkbox"
          value="${escapeAttr(source.relativePath)}"
          ${state.selectedConfigPaths.includes(source.relativePath) ? "checked" : ""}
          ${source.ok ? "" : "disabled"}
        >
        <span title="${escapeAttr(source.relativePath)}">${escapeHtml(source.relativePath)}</span>
        <small>${source.ok ? `${Object.keys(source.data || {}).length} keys` : escapeHtml(source.error)}</small>
      </label>
    `,
        )
        .join("");
    }

    el.configList.querySelectorAll("input[type='checkbox']").forEach((input) => {
      input.addEventListener("change", handleConfigSelectionChange);
    });

    el.configMerged.textContent = JSON.stringify(selectedMergedConfig(), null, 2);
    updateBuildSummary();
  }

  function initializeConfigSelection(snapshot, previousSelected) {
    const availablePaths = new Set(
      snapshot.config.sources.map((source) => source.relativePath),
    );

    if (previousSelected) {
      state.selectedConfigPaths = Array.from(previousSelected).filter((item) =>
        availablePaths.has(item),
      );
      return;
    }

    const defaults = Array.isArray(snapshot.config.selectedPaths)
      ? snapshot.config.selectedPaths
      : snapshot.config.sources
          .filter((source) => source.defaultSelected)
          .map((source) => source.relativePath);
    const errorDefaults = snapshot.config.sources
      .filter((source) => source.defaultSelected && !source.ok)
      .map((source) => source.relativePath);
    state.selectedConfigPaths = Array.from(new Set([...defaults, ...errorDefaults]))
      .filter((item) => availablePaths.has(item));
  }

  function handleConfigSelectionChange() {
    state.selectedConfigPaths = Array.from(
      el.configList.querySelectorAll("input[type='checkbox']:checked"),
    ).map((input) => input.value);
    syncEditorCompletionContext();
    renderConfig();
    renderProject();
    refreshRemoteStatuses();
    if (state.currentFile) {
      renderActiveFile();
    } else {
      previewCommand(currentCommand(), { force: true });
    }
  }

  function selectedConfigSources(options = {}) {
    if (!state.snapshot) {
      return [];
    }
    const selected = new Set(state.selectedConfigPaths);
    return state.snapshot.config.sources.filter((source) => (
      selected.has(source.relativePath) && (options.includeErrors || source.ok)
    ));
  }

  function selectedConfigErrors() {
    if (!state.snapshot) {
      return [];
    }
    const selected = new Set(state.selectedConfigPaths);
    return state.snapshot.config.errors.filter((error) =>
      selected.has(error.relativePath),
    );
  }

  function selectedMergedConfig() {
    const merged = {};
    selectedConfigSources().forEach((source) => {
      if (isPlainObject(source.data)) {
        Object.assign(merged, source.data);
      }
    });
    return merged;
  }

  function syncEditorCompletionContext() {
    const language = state.currentFile && !state.readonlySource
      ? detectLanguage(state.currentFile)
      : "plain";
    const shouldComplete = language === "dsl" || language === "resource";
    if (typeof CM6.setCompletionContext === "function") {
      CM6.setCompletionContext({
        language,
        keywords: shouldComplete ? state.completionKeywords : [],
        variables: shouldComplete ? flattenConfigVariablePaths(selectedMergedConfig()) : [],
      });
    }
  }

  async function loadEditorCompletionKeywords() {
    if (!state.snapshot || !state.currentFile || state.readonlySource) {
      syncEditorCompletionContext();
      return;
    }
    const language = detectLanguage(state.currentFile);
    if (!(language === "dsl" || language === "resource")) {
      syncEditorCompletionContext();
      return;
    }

    const projectRoot = state.snapshot.project.rootPath;
    if (
      state.completionKeywordsLoaded &&
      state.completionKeywordProjectRoot === projectRoot
    ) {
      syncEditorCompletionContext();
      return;
    }
    if (state.completionKeywordLoadPromise) {
      return state.completionKeywordLoadPromise;
    }

    state.completionKeywordProjectRoot = projectRoot;
    state.completionKeywordLoadPromise = (async () => {
      try {
        const result = await api.listKeywords({
          projectRoot: state.snapshot.project.rootPath,
          query: "",
          limit: 500,
        });
        if (!state.snapshot || state.snapshot.project.rootPath !== projectRoot) {
          return;
        }
        state.completionKeywords = Array.isArray(result.keywords) ? result.keywords : [];
        state.completionKeywordsLoaded = true;
        syncEditorCompletionContext();
      } catch (error) {
        if (state.snapshot && state.snapshot.project.rootPath === projectRoot) {
          state.completionKeywords = [];
          state.completionKeywordsLoaded = true;
          syncEditorCompletionContext();
          appendLog("warn", `关键字补全加载失败: ${errorMessage(error)}`);
        }
      } finally {
        if (state.completionKeywordProjectRoot === projectRoot) {
          state.completionKeywordLoadPromise = null;
        }
      }
    })();

    return state.completionKeywordLoadPromise;
  }

  function resetEditorCompletionKeywords() {
    state.completionKeywords = [];
    state.completionKeywordProjectRoot = null;
    state.completionKeywordsLoaded = false;
    state.completionKeywordLoadPromise = null;
    syncEditorCompletionContext();
  }

  function flattenConfigVariablePaths(value, prefix = "", result = []) {
    if (isPlainObject(value)) {
      Object.keys(value)
        .sort((left, right) => left.localeCompare(right, "zh-CN"))
        .forEach((key) => {
          const path = prefix ? `${prefix}.${key}` : key;
          flattenConfigVariablePaths(value[key], path, result);
        });
      if (prefix) {
        result.push(prefix);
      }
      return result;
    }

    if (prefix) {
      result.push(prefix);
    }
    return Array.from(new Set(result));
  }

  return {
    renderConfig,
    initializeConfigSelection,
    handleConfigSelectionChange,
    selectedConfigSources,
    selectedConfigErrors,
    selectedMergedConfig,
    syncEditorCompletionContext,
    loadEditorCompletionKeywords,
    resetEditorCompletionKeywords,
    flattenConfigVariablePaths,
  };
}
