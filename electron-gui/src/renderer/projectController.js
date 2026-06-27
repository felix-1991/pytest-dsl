import { emptyRemoteStatus } from "./state.js";
import { escapeAttr, escapeHtml, errorMessage } from "./utils.js";

export function createProjectController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  getEditableFiles,
  selectFile,
  clearEditor,
  switchWorkspaceView,
  setRunningState,
  resetAllConsoleState,
  resetKeywordBrowser,
  resetEditorCompletionKeywords,
  initializeConfigSelection,
  renderConfig,
  invalidateBuildCaseTreeRender,
  renderSuiteOptions,
  collapseTreeDirsBelowRoot,
  closeEntryDialog,
  clearTreeDragState,
  closeTreeContextMenu,
  renderFileTree,
  resetBuildReport,
  renderBuildHistory,
  updateBuildSummary,
  refreshRemoteStatuses,
  startDynamicRemoteMonitoring,
  stopDynamicRemoteMonitoring,
  renderRemoteStatus,
  renderRuntimeStatus,
}) {
  async function openProject() {
    try {
      const snapshot = await api.openProject();
      if (!snapshot) {
        appendLog("info", "Open project canceled");
        return;
      }
      applySnapshot(snapshot, "Opened project");
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  async function refreshProject(options = {}) {
    if (!state.snapshot) {
      appendLog("warn", "请先打开一个项目");
      return;
    }

    try {
      const snapshot = await api.scanProject(state.snapshot.project.rootPath);
      applySnapshot(
        snapshot,
        options.logMessage || "Refreshed project",
        Object.prototype.hasOwnProperty.call(options, "preferredFile")
          ? options.preferredFile
          : state.currentFile,
      );
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  function applySnapshot(snapshot, logMessage, preferredFile = null) {
    const previousRoot = state.snapshot && state.snapshot.project.rootPath;
    const previousSelected = previousRoot === snapshot.project.rootPath
      ? new Set(state.selectedConfigPaths)
      : null;
    const projectChanged = previousRoot !== snapshot.project.rootPath;

    state.snapshot = snapshot;
    state.currentFile = null;
    state.dirty = false;
    state.configSignature = snapshot.config && snapshot.config.signature
      ? snapshot.config.signature
      : null;
    if (projectChanged) {
      resetKeywordBrowser();
      resetEditorCompletionKeywords();

      // Invalidate cached definition data for the changed project
      if (previousRoot && typeof api.invalidateDefinitionCache === "function") {
        api.invalidateDefinitionCache(previousRoot);
      }
      state.currentBuildId = null;
      state.currentBuildStatus = "";
      state.currentBuildResultsDir = "";
      state.buildHistory = [];
      invalidateBuildCaseTreeRender();
      resetBuildReport();
      state.suiteSelectionTouched = false;
      state.buildSelectionTouched = false;
      state.selectedTreePath = "";
      state.selectedTreeKind = "directory";
      collapseTreeDirsBelowRoot();
      state.selectedFileOverrides = {};
      state.selectedBuildFileOverrides = {};
      state.expandedSuiteNodes.clear();
      closeEntryDialog(null);
    }
    initializeConfigSelection(snapshot, previousSelected);

    renderProject();
    renderFileTree();
    renderConfig();
    refreshRemoteStatuses();
    startDynamicRemoteMonitoring();
    renderMetadata(snapshot.metadata);
    renderDeductions();
    renderRuntimeStatus({
      projectRoot: snapshot.project.rootPath,
      config: snapshot.metadata.runtime || { pythonExecutable: null, allureExecutable: null },
      python: null,
      allure: null,
    });
    refreshRuntimeStatus();
    appendLog("info", `${logMessage}: ${snapshot.project.rootPath}`);

    const editableFiles = getEditableFiles(snapshot);
    const lastOpened = preferredFile || snapshot.metadata.lastOpenedFile;
    const initialFile =
      editableFiles.find((file) => file.relativePath === lastOpened) ||
      editableFiles[0];

    if (initialFile) {
      selectFile(initialFile.relativePath);
    } else {
      clearEditor("项目中没有找到可编辑文本文件");
    }
  }

  function setEmptyProjectState() {
    stopDynamicRemoteMonitoring();
    state.snapshot = null;
    state.currentFile = null;
    state.dirty = false;
    state.selectedConfigPaths = [];
    state.selectedSuiteIds = [];
    state.selectedFileOverrides = {};
    state.selectedBuildSuiteIds = [];
    state.selectedBuildFileOverrides = {};
    state.expandedSuiteNodes.clear();
    state.suiteSelectionTouched = false;
    state.buildSelectionTouched = false;
    state.selectedTreePath = "";
    state.selectedTreeKind = "directory";
    state.activeView = "debug";
    state.buildCaseTreeSignature = null;
    state.filter = "";
    state.buildCaseFilter = "";
    state.collapsedTreeDirs.clear();
    closeTreeContextMenu();
    closeEntryDialog(null);
    clearTreeDragState();
    state.configSignature = null;
    state.remoteStatus = emptyRemoteStatus();
    state.currentTaskId = null;
    state.currentTaskMode = null;
    state.currentBuildId = null;
    state.currentBuildStatus = "";
    state.currentBuildReportUrl = "";
    state.currentBuildReportText = "";
    state.currentBuildResultsDir = "";
    state.buildHistory = [];
    state.currentDebugLine = null;
    state.debugStartLine = null;
    state.debugPaused = false;
    state.debugSelection = null;
    state.readonlySource = null;
    resetAllConsoleState();
    resetKeywordBrowser();
    resetEditorCompletionKeywords();
    el.projectName.textContent = "Pytest DSL Studio";
    el.projectRoot.textContent = "选择一个外部项目开始";
    showActionFeedback("就绪", "info");
    el.branchName.textContent = "local";
    el.gitStatus.textContent = "local";
    el.workspaceStatus.textContent = "未打开项目";
    el.configCount.textContent = "0";
    el.configSummary.textContent = "未加载配置";
    renderRemoteStatus();
    el.suiteSummary.textContent = "打开项目后自动识别";
    el.suiteList.innerHTML = `<p class="empty">打开项目后显示 convention 测试套</p>`;
    el.buildCaseTree.innerHTML = `<p class="empty">打开项目后显示可构建案例</p>`;
    resetBuildReport();
    renderBuildHistory();
    switchWorkspaceView("debug");
    updateBuildSummary();
    el.fileTree.innerHTML = `<p class="empty">点击“打开项目”选择本地 pytest-dsl 项目</p>`;
    el.configList.innerHTML = `<p class="empty">打开项目后显示可加载的 YAML 配置</p>`;
    el.configMerged.textContent = "{}";
    renderMetadata({ lastOpenedFile: null, recentFiles: [], updatedAt: null });
    el.deductionList.innerHTML = `<li>未打开项目</li>`;
    renderRuntimeStatus({
      projectRoot: null,
      config: { pythonExecutable: null, allureExecutable: null },
      python: null,
      allure: null,
    });
    clearEditor("选择一个文件");
    setRunningState(false);
  }

  function renderProject() {
    const snapshot = state.snapshot;
    const editableFiles = getEditableFiles(snapshot);
    el.projectName.textContent = snapshot.project.name;
    el.projectRoot.textContent = snapshot.project.rootPath;
    el.branchName.textContent = snapshot.git.displayName;
    el.gitStatus.textContent = snapshot.git.isGit
      ? `git: ${snapshot.git.displayName}`
      : "local";
    el.workspaceStatus.textContent = `${editableFiles.length} 文件 · ${snapshot.dslFiles.length} DSL · ${state.selectedConfigPaths.length}/${snapshot.config.sources.length} config · score ${snapshot.score.value}`;
    el.configCount.textContent = `${state.selectedConfigPaths.length}/${snapshot.config.sources.length}`;
    renderSuiteOptions(snapshot.suites || [], snapshot.suiteTree);
    updateBuildSummary();
  }

  function renderMetadata(metadata) {
    const rows = [
      ["存储", ".pytest-dsl-gui/metadata.json"],
      ["最近文件", metadata.lastOpenedFile || "未记录"],
      ["历史数量", String((metadata.recentFiles || []).length)],
      ["更新时间", metadata.updatedAt || "未写入"],
    ];

    el.metadataList.innerHTML = rows
      .map(
        ([key, value]) => `
    <dt>${escapeHtml(key)}</dt>
    <dd title="${escapeAttr(value)}">${escapeHtml(value)}</dd>
  `,
      )
      .join("");
  }

  function renderDeductions() {
    const deductions = state.snapshot.score.deductions;
    if (deductions.length === 0) {
      el.deductionList.innerHTML = `<li>无扣分项</li>`;
      return;
    }

    el.deductionList.innerHTML = deductions
      .map((item) => `<li>${escapeHtml(item.reason)} · -${item.points}</li>`)
      .join("");
  }

  async function refreshRuntimeStatus() {
    if (!state.snapshot) return;
    const projectRoot = state.snapshot.project.rootPath;
    if (typeof api.getRuntimeStatus !== "function") return;
    try {
      const result = await api.getRuntimeStatus({ projectRoot });
      if (!state.snapshot || state.snapshot.project.rootPath !== projectRoot) return;
      renderRuntimeStatus(result);
    } catch (error) {
      appendLog("error", `Runtime status probe failed: ${error.message}`);
    }
  }

  return {
    openProject,
    refreshProject,
    applySnapshot,
    setEmptyProjectState,
    renderProject,
    renderMetadata,
    renderDeductions,
    refreshRuntimeStatus,
  };
}
