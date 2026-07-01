import { createCommandController } from "./renderer/commandController.js";
import { createConsoleController } from "./renderer/consoleController.js";
import { createKeywordController } from "./renderer/keywordController.js";
import { createLayoutController } from "./renderer/layoutController.js";
import { createProjectTreeController } from "./renderer/projectTreeController.js";
import { createRuntimeController } from "./renderer/runtimeController.js";
import { createSuiteTreeController } from "./renderer/suiteTreeController.js";
import { createFileController } from "./renderer/fileController.js";
import { createConfigController } from "./renderer/configController.js";
import { createRemoteStatusController } from "./renderer/remoteStatusController.js";
import { createBuildReportController } from "./renderer/buildReportController.js";
import { createExecutionController } from "./renderer/executionController.js";
import { createWorkspaceController } from "./renderer/workspaceController.js";
import { createProjectController } from "./renderer/projectController.js";
import { createSearchController } from "./renderer/searchController.js";
import { createShortcutHelpController } from "./renderer/shortcutHelpController.js";
import { createInitialState } from "./renderer/state.js";
import { errorMessage } from "./renderer/utils.js";

const api = window.pytestDslGui;
const state = createInitialState();

const el = {};
let commandController = null;
let fileController = null;
let configController = null;
let remoteStatusController = null;
let buildReportController = null;

const consoleController = createConsoleController({
  state,
  el,
  api,
  errorMessage,
  renderCommandBar: () => commandController && commandController.renderCommandBar(),
  renderCommandPreview: () => commandController && commandController.renderCommandPreview(),
});

const {
  appendLog,
  appendProcessOutput,
  applyConsoleViewState,
  clearConsole,
  consoleScopeForMode,
  copyConsoleOutput,
  exportConsoleLog,
  finishConsoleForExecution,
  normalizeConsoleScope,
  openConsolePanel,
  resetAllConsoleState,
  resetConsoleForExecution,
  setConsoleScope,
  toggleConsoleExpanded,
  toggleConsoleOpen,
  toggleConsoleWrap,
} = consoleController;

commandController = createCommandController({
  state,
  el,
  consoleScopeForMode,
  currentCommand,
  normalizeConsoleScope,
});

const {
  commandContextForMode,
  lockGeneratedCommand,
  normalizeCommandText,
  previewCommand,
  releaseExecutionCommand,
  renderCommandBar,
  renderCommandPreview,
  resetCommandPreview,
  setExecutionCommand,
  updateCommandPreview,
} = commandController;

const layoutController = createLayoutController();
const { bindPanelResizers, initializeLayoutSizing } = layoutController;

const shortcutHelpController = createShortcutHelpController({ el });

const {
  closeShortcutHelp,
  handleShortcutHelpBackdropClick,
  handleShortcutHelpKeydown,
  openShortcutHelp,
} = shortcutHelpController;

const runtimeController = createRuntimeController({
  state,
  el,
  api,
  appendLog,
  errorMessage,
  renderMetadata: (...args) => projectController.renderMetadata(...args),
  showActionFeedback,
  onRuntimeStatusChange: () => {
    if (fileController) fileController.updateFileActionState();
    if (buildReportController) buildReportController.updateBuildSummary();
  },
});

const { changeRuntime, renderRuntimeStatus, showRuntimeRequirementDialog } = runtimeController;

const projectTreeController = createProjectTreeController({
  state,
  el,
  api,
  appendLog,
  fileIcon: (...args) => fileController.fileIcon(...args),
  fileKind: (...args) => fileController.fileKind(...args),
  folderIcon: (...args) => fileController.folderIcon(...args),
  refreshProject: (...args) => projectController.refreshProject(...args),
  selectFile: (...args) => fileController.selectFile(...args),
});

const {
  closeEntryDialog,
  closeTreeContextMenu,
  clearTreeDragState,
  collapseTreeDirsBelowRoot,
  handleEntryDialogSubmit,
  handleFileTreeClick,
  handleFileTreeContextMenu,
  handleProjectTreeScroll,
  handleTreeContextMenuClick,
  handleTreeDragEnd,
  handleTreeDragLeave,
  handleTreeDragOver,
  handleTreeDragStart,
  handleTreeDrop,
  renderFileTree,
  scheduleFileTreeRender,
  setAllTreeGroupsCollapsed,
} = projectTreeController;

const suiteTreeController = createSuiteTreeController({
  state,
  el,
  currentCommand,
  previewCommand,
  selectedConfigSources: (...args) => configController.selectedConfigSources(...args),
  updateBuildSummary: (...args) => buildReportController.updateBuildSummary(...args),
  updateDebugActionState: () => {
    if (fileController) fileController.updateFileActionState();
  },
});

const {
  activeBuildCommandId,
  buildCommandLabel,
  buildPytestArgsLabel,
  buildResultsDirForBuild,
  computeSelectedFiles,
  currentSelectedSuiteIds,
  ensureBuildCaseTreeRendered,
  ensureBuildCaseTreeRootExpanded,
  handleSuiteTreeChange,
  handleSuiteTreeClick,
  invalidateBuildCaseTreeRender,
  renderSuiteOptions,
  scheduleBuildCaseTreeRender,
  setAllBuildCaseGroupsExpanded,
  suiteBuildScopeLabel,
  suiteCommandLabel,
} = suiteTreeController;

fileController = createFileController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  currentCommand,
  previewCommand,
  resetCommandPreview,
  renderFileTree,
  renderMetadata: (...args) => projectController.renderMetadata(...args),
  renderRemoteStatus: (...args) => remoteStatusController.renderRemoteStatus(...args),
  syncEditorCompletionContext: (...args) => configController.syncEditorCompletionContext(...args),
  loadEditorCompletionKeywords: (...args) => configController.loadEditorCompletionKeywords(...args),
  resetEditorCompletionKeywords: (...args) => configController.resetEditorCompletionKeywords(...args),
  selectedConfigErrors: (...args) => configController.selectedConfigErrors(...args),
  selectedMergedConfig: (...args) => configController.selectedMergedConfig(...args),
  updateBuildActionState: (...args) => buildReportController.updateBuildActionState(...args),
  currentSelectedSuiteIds,
  closeKeywordPanel: (...args) => keywordController.closeKeywordPanel(...args),
  debugFromLine: (...args) => debugFromLine(...args),
  handleDefinitionRequest: (...args) => handleDefinitionRequest(...args),
});

const {
  clearEditor,
  detectLanguage,
  isExecutableFile,
  isRunnableWholeFile,
  openExternalReadonlySource,
  saveCurrentFile,
  reloadOpenFiles,
  selectFile,
  setDirty,
  switchToTab,
  closeTab,
  updateFileActionState,
  renderActiveFile,
  getEditableFiles,
} = fileController;

const keywordController = createKeywordController({
  state,
  el,
  api,
  appendLog,
  detectLanguage,
  isExecutableFile,
  renderActiveFile,
  renderFileTree,
  selectFile,
  setDirty: (...args) => fileController.setDirty(...args),
  syncEditorCompletionContext: (...args) => configController.syncEditorCompletionContext(...args),
  selectedConfigVariableDefinitions: (...args) => configController.selectedConfigVariableDefinitions(...args),
  openExternalReadonlySource,
  openDefinitionWindow: (...args) => api.openDefinitionWindow(...args),
});

const {
  closeKeywordPanel,
  handleDefinitionRequest,
  handleKeywordListClick,
  handleKeywordSearchInput,
  handleRefreshDefinitions,
  goToVariableDefinition,
  resetKeywordBrowser,
  toggleKeywordPanel,
} = keywordController;

configController = createConfigController({
  state,
  el,
  api,
  appendLog,
  currentCommand,
  previewCommand,
  detectLanguage,
  renderActiveFile,
  refreshRemoteStatuses: (...args) => remoteStatusController.refreshRemoteStatuses(...args),
  renderProject: (...args) => projectController.renderProject(...args),
  updateBuildSummary: (...args) => buildReportController.updateBuildSummary(...args),
});

const {
  initializeConfigSelection,
  renderConfig,
  resetEditorCompletionKeywords,
  selectedConfigSources,
  selectedMergedConfig,
  syncEditorCompletionContext,
} = configController;

remoteStatusController = createRemoteStatusController({
  state,
  el,
  api,
  appendLog,
  currentCommand,
  previewCommand,
  selectedMergedConfig,
  initializeConfigSelection,
  renderConfig,
  renderActiveFile,
  renderProject: (...args) => projectController.renderProject(...args),
  renderDeductions: (...args) => projectController.renderDeductions(...args),
});

const {
  refreshRemoteStatuses,
  renderRemoteStatus,
  startDynamicRemoteMonitoring,
  stopDynamicRemoteMonitoring,
} = remoteStatusController;

buildReportController = createBuildReportController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  currentSelectedSuiteIds,
  suiteBuildScopeLabel,
  buildCommandLabel,
  buildResultsDirForBuild,
  buildPytestArgsLabel,
  activeBuildCommandId,
  selectedConfigSources,
});

const {
  downloadCurrentBuildLogs,
  downloadCurrentBuildReport,
  openCurrentBuildReport,
  recordBuildHistory,
  renderBuildHistory,
  resetBuildReport,
  setBuildReportUrl,
  syncBuildReportFrameVisibility,
  updateBuildActionState,
  updateBuildSummary,
  buildStatusLabel,
} = buildReportController;

const executionController = createExecutionController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  currentCommand,
  consoleScopeForMode,
  appendProcessOutput,
  resetConsoleForExecution,
  finishConsoleForExecution,
  setConsoleScope,
  openConsolePanel,
  setExecutionCommand,
  releaseExecutionCommand,
  updateCommandPreview,
  previewCommand,
  commandContextForMode,
  currentSelectedSuiteIds,
  computeSelectedFiles,
  suiteCommandLabel,
  buildCommandLabel,
  showRuntimeRequirementDialog,
  setBuildReportUrl,
  resetBuildReport,
  buildStatusLabel,
  recordBuildHistory,
  updateBuildSummary,
  updateBuildActionState,
  updateFileActionState,
  isExecutableFile,
  isRunnableWholeFile,
  selectedConfigSources,
});

const {
  handleBuildEvent,
  handleExecutionEvent,
  runBuildExecution,
  runExecutionTask,
  runSuiteExecution,
  setRunningState,
  stopCurrentTask,
  currentDebugRunOptions,
  sendDebugCommand,
  debugFromLine,
} = executionController;

const workspaceController = createWorkspaceController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  currentCommand,
  previewCommand,
  normalizeCommandText,
  lockGeneratedCommand,
  setConsoleScope,
  syncBuildReportFrameVisibility,
  updateBuildSummary,
  ensureBuildCaseTreeRootExpanded,
  ensureBuildCaseTreeRendered,
  setAllBuildCaseGroupsExpanded,
  buildCommandLabel,
  scheduleBuildCaseTreeRender,
  saveCurrentFile,
  closeKeywordPanel,
  closeTreeContextMenu,
  setAllTreeGroupsCollapsed,
});

const {
  closeConfigPicker,
  closeSuitePicker,
  closeTopPickers,
  closeTransientPanelsForOutsideClick,
  handleBuildCaseTreeScroll,
  handleEditorSaveShortcut,
  switchWorkspaceView,
  updateTreePaneForActiveView,
  generateCurrentCommand,
  copyGeneratedCommand,
} = workspaceController;

const projectController = createProjectController({
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
});

const {
  openProject,
  refreshProject,
  setEmptyProjectState,
  renderMetadata,
  renderProject,
  renderDeductions,
} = projectController;

const searchController = createSearchController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  switchWorkspaceView,
  updateTreePaneForActiveView,
  selectFile,
  reloadOpenFiles,
});

const {
  handleProjectSearchInput,
  handleProjectSearchKeydown,
  handleProjectReplaceInput,
  handleProjectSearchResultsClick,
  handleProjectSearchResultsScroll,
  handleProjectSearchShortcut,
  replaceAllProjectMatches,
  renderProjectSearchPanel,
  toggleProjectReplace,
  toggleProjectSearchOption,
  toggleProjectSearchPanel,
} = searchController;

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  initializeLayoutSizing();
  bindEvents();
  applyConsoleViewState();
  // Editor instances are now created lazily when files are opened.
  // No initial empty editor — the user starts with a clean slate.
  syncEditorCompletionContext();
  setEmptyProjectState();
  renderProjectSearchPanel();
  appendLog("info", "Electron GUI initialized");
  appendLog("info", "请选择要打开的 pytest-dsl 项目");
});

function cacheElements() {
  [
    "projectName",
    "projectRoot",
    "topbar",
    "suitePicker",
    "suiteTrigger",
    "suiteSummary",
    "suiteMenu",
    "suiteList",
    "configPicker",
    "configTrigger",
    "configSummary",
    "remoteStatusSummary",
    "remoteStatusPopover",
    "remoteServiceRows",
    "openProjectBtn",
    "refreshBtn",
    "runAllBtn",
    "debugNavBtn",
    "buildNavBtn",
    "treeRefreshBtn",
    "collapseAllBtn",
    "treePaneHead",
    "branchName",
    "treePaneTitle",
    "fileFilter",
    "fileTree",
    "buildCaseTree",
    "treeContextMenu",
    "projectSearchOpenBtn",
    "projectSearchCloseBtn",
    "projectSearchPanel",
    "projectSearchInput",
    "projectReplaceInput",
    "projectReplaceRow",
    "projectSearchCaseBtn",
    "projectSearchWordBtn",
    "projectSearchRegexBtn",
    "projectSearchRunBtn",
    "projectReplaceToggleBtn",
    "projectReplaceAllBtn",
    "projectSearchResults",
    "projectSearchSummary",
    "dirtyDot",
    "editorTabs",
    "activeTab",
    "fileTitle",
    "filePath",
    "mainStage",
    "debugWorkspace",
    "buildPanel",
    "buildRunBtn",
    "buildStopBtn",
    "buildOpenReportBtn",
    "buildDownloadReportBtn",
    "buildDownloadLogsBtn",
    "buildToggleConsoleBtn",
    "buildStatus",
    "buildScope",
    "buildConfigSummary",
    "buildPytestArgs",
    "buildAllureStatus",
    "buildCommand",
    "buildResultsDir",
    "buildReportUrl",
    "buildReportFrame",
    "buildReportEmpty",
    "buildHistoryList",
    "editActionGroup",
    "executionActionGroup",
    "debugSessionGroup",
    "saveBtn",
    "syntaxBtn",
    "runBtn",
    "debugStepsBtn",
    "nextStepBtn",
    "continueDebugBtn",
    "stopBtn",
    "keywordBtn",
    "commandBtn",
    "keywordRefreshBtn",
    "commandBar",
    "generatedCommandStatus",
    "generatedCommandText",
    "copyCommandBtn",
    "regenerateCommandBtn",
    "keywordPanel",
    "keywordSearch",
    "keywordStatus",
    "keywordList",
    "codeEditor",
    "editorMeta",
    "problemCount",
    "variableCount",
    "commandContext",
    "commandPreview",
    "bottomConsole",
    "consoleToggleBtn",
    "consoleStatusToggleBtn",
    "consoleActions",
    "copyConsoleBtn",
    "exportConsoleBtn",
    "wrapConsoleBtn",
    "expandConsoleBtn",
    "clearConsoleBtn",
    "consoleBody",
    "configCount",
    "configList",
    "configMerged",
    "metadataList",
    "deductionList",
    "shortcutHelpBtn",
    "shortcutHelpDialog",
    "shortcutHelpCloseBtn",
    "shortcutHelpList",
    "workspaceStatus",
    "actionStatus",
    "gitStatus",
    "remoteStatusBar",
    "entryDialog",
    "entryDialogForm",
    "entryDialogTitle",
    "entryDialogLabel",
    "entryDialogInput",
    "entryDialogError",
    "entryDialogCancel",
    "runtimeConfig",
    "runtimePythonStatus",
    "runtimePythonPath",
    "runtimePythonSelectDirBtn",
    "runtimePythonAutoBtn",
    "runtimeAllureStatus",
    "runtimeAllurePath",
    "runtimeAllureSelectBtn",
    "runtimeAllureAutoBtn",
  ].forEach((id) => {
    el[id] = document.getElementById(id);
  });
}

function bindEvents() {
  bindPanelResizers();
  el.openProjectBtn.addEventListener("click", openProject);
  el.shortcutHelpBtn.addEventListener("click", openShortcutHelp);
  el.shortcutHelpCloseBtn.addEventListener("click", closeShortcutHelp);
  el.shortcutHelpDialog.addEventListener("click", handleShortcutHelpBackdropClick);
  el.shortcutHelpDialog.addEventListener("keydown", handleShortcutHelpKeydown);
  el.refreshBtn.addEventListener("click", refreshProject);
  el.saveBtn.addEventListener("click", saveCurrentFile);
  el.syntaxBtn.addEventListener("click", () => runExecutionTask("syntax"));
  el.runBtn.addEventListener("click", () => runExecutionTask("run"));
  el.debugStepsBtn.addEventListener("click", () =>
    runExecutionTask("debug", currentDebugRunOptions()),
  );
  el.debugNavBtn.addEventListener("click", () => switchWorkspaceView("debug"));
  el.buildNavBtn.addEventListener("click", () => switchWorkspaceView("build"));
  el.buildRunBtn.addEventListener("click", runBuildExecution);
  el.buildStopBtn.addEventListener("click", stopCurrentTask);
  el.buildOpenReportBtn.addEventListener("click", openCurrentBuildReport);
  el.buildDownloadReportBtn.addEventListener("click", downloadCurrentBuildReport);
  el.buildDownloadLogsBtn.addEventListener("click", downloadCurrentBuildLogs);
  el.buildToggleConsoleBtn.addEventListener("click", toggleConsoleOpen);
  el.nextStepBtn.addEventListener("click", () => sendDebugCommand("next"));
  el.continueDebugBtn.addEventListener("click", () => sendDebugCommand("continue"));
  el.stopBtn.addEventListener("click", stopCurrentTask);
  el.runAllBtn.addEventListener("click", runSuiteExecution);
  el.consoleToggleBtn.addEventListener("click", toggleConsoleOpen);
  el.consoleStatusToggleBtn.addEventListener("click", toggleConsoleOpen);
  el.copyConsoleBtn.addEventListener("click", copyConsoleOutput);
  el.exportConsoleBtn.addEventListener("click", exportConsoleLog);
  el.wrapConsoleBtn.addEventListener("click", toggleConsoleWrap);
  el.expandConsoleBtn.addEventListener("click", toggleConsoleExpanded);
  el.clearConsoleBtn.addEventListener("click", () => clearConsole());
  el.treeRefreshBtn.addEventListener("click", () =>
    refreshProject({ logMessage: "Refreshed project tree" }),
  );
  el.fileTree.addEventListener("contextmenu", handleFileTreeContextMenu);
  el.fileTree.addEventListener("click", handleFileTreeClick);
  el.fileTree.addEventListener("scroll", handleProjectTreeScroll);
  el.fileTree.addEventListener("dragstart", handleTreeDragStart);
  el.fileTree.addEventListener("dragend", handleTreeDragEnd);
  el.fileTree.addEventListener("dragover", handleTreeDragOver);
  el.fileTree.addEventListener("dragleave", handleTreeDragLeave);
  el.fileTree.addEventListener("drop", handleTreeDrop);
  el.suiteList.addEventListener("change", handleSuiteTreeChange);
  el.suiteList.addEventListener("click", handleSuiteTreeClick);
  el.buildCaseTree.addEventListener("change", handleSuiteTreeChange);
  el.buildCaseTree.addEventListener("click", handleSuiteTreeClick);
  el.buildCaseTree.addEventListener("scroll", handleBuildCaseTreeScroll);
  el.keywordList.addEventListener("click", handleKeywordListClick);
  el.treeContextMenu.addEventListener("click", handleTreeContextMenuClick);
  el.entryDialogForm.addEventListener("submit", handleEntryDialogSubmit);
  el.entryDialogCancel.addEventListener("click", () => closeEntryDialog(null));
  el.entryDialog.addEventListener("click", (event) => {
    if (event.target === el.entryDialog) {
      closeEntryDialog(null);
    }
  });
  el.entryDialog.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeEntryDialog(null);
    }
  });
  document.addEventListener("click", closeTransientPanelsForOutsideClick);
  document.addEventListener("keydown", handleEditorSaveShortcut, true);
  document.addEventListener("keydown", handleProjectSearchShortcut, true);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeTreeContextMenu();
      closeTopPickers();
      closeKeywordPanel();
      closeShortcutHelp({ restoreFocus: false });
    }
  });

  // Tab bar click delegation
  if (el.editorTabs) {
    el.editorTabs.addEventListener("click", (event) => {
      const closeBtn = event.target.closest("[data-tab-close]");
      if (closeBtn && fileController) {
        event.stopPropagation();
        fileController.closeTab(closeBtn.dataset.tabClose);
        return;
      }
      const tabBtn = event.target.closest("[data-tab-key]");
      if (tabBtn && fileController) {
        event.stopPropagation();
        fileController.switchToTab(tabBtn.dataset.tabKey);
      }
    });
  }

  // Keyboard shortcuts for tab navigation
  document.addEventListener("keydown", (event) => {
    const isMeta = event.ctrlKey || event.metaKey;
    // Ctrl+W / Cmd+W: close active tab
    if (isMeta && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "w") {
      if (fileController && state.activeFileKey) {
        event.preventDefault();
        fileController.closeTab(state.activeFileKey);
      }
      return;
    }
    // Ctrl+Tab: next tab
    if (isMeta && !event.altKey && !event.shiftKey && event.key === "Tab") {
      if (fileController && state.openFiles.length > 1) {
        event.preventDefault();
        const idx = state.openFiles.findIndex((f) => f.key === state.activeFileKey);
        const next = state.openFiles[(idx + 1) % state.openFiles.length];
        fileController.switchToTab(next.key);
      }
      return;
    }
    // Ctrl+Shift+Tab: previous tab
    if (isMeta && !event.altKey && event.shiftKey && event.key === "Tab") {
      if (fileController && state.openFiles.length > 1) {
        event.preventDefault();
        const idx = state.openFiles.findIndex((f) => f.key === state.activeFileKey);
        const prev = state.openFiles[(idx - 1 + state.openFiles.length) % state.openFiles.length];
        fileController.switchToTab(prev.key);
      }
      return;
    }
    // Ctrl+1-9: switch to tab by index
    if (isMeta && !event.altKey && !event.shiftKey) {
      const digit = event.key.match(/^(\d)$/);
      if (digit && fileController) {
        const index = parseInt(digit[1], 10) - 1;
        if (index >= 0 && index < state.openFiles.length) {
          event.preventDefault();
          fileController.switchToTab(state.openFiles[index].key);
        }
      }
    }
  }, true);
  el.suiteTrigger.addEventListener("click", () => {
    closeConfigPicker();
    closeKeywordPanel();
    el.suitePicker.classList.toggle("is-open");
    el.suiteTrigger.setAttribute(
      "aria-expanded",
      String(el.suitePicker.classList.contains("is-open")),
    );
  });
  el.collapseAllBtn.addEventListener("click", () => {
    if (state.activeView === "build") {
      setAllBuildCaseGroupsExpanded(false);
    } else {
      setAllTreeGroupsCollapsed(true);
    }
  });
  el.keywordBtn.addEventListener("click", () =>
    toggleKeywordPanel(),
  );
  el.keywordRefreshBtn.addEventListener("click", () =>
    handleRefreshDefinitions(),
  );
  el.commandBtn.addEventListener("click", () =>
    generateCurrentCommand(),
  );
  el.regenerateCommandBtn.addEventListener("click", () =>
    generateCurrentCommand(),
  );
  el.copyCommandBtn.addEventListener("click", () =>
    copyGeneratedCommand(),
  );
  el.keywordSearch.addEventListener("input", handleKeywordSearchInput);
  el.projectSearchOpenBtn.addEventListener("click", toggleProjectSearchPanel);
  el.projectSearchCloseBtn.addEventListener("click", toggleProjectSearchPanel);
  el.projectSearchInput.addEventListener("input", handleProjectSearchInput);
  el.projectSearchInput.addEventListener("keydown", handleProjectSearchKeydown);
  el.projectReplaceInput.addEventListener("input", handleProjectReplaceInput);
  el.projectReplaceInput.addEventListener("keydown", handleProjectSearchKeydown);
  el.projectSearchRunBtn.addEventListener("click", () => runProjectSearch({ force: true }));
  el.projectSearchCaseBtn.addEventListener("click", () => toggleProjectSearchOption("caseSensitive"));
  el.projectSearchWordBtn.addEventListener("click", () => toggleProjectSearchOption("wholeWord"));
  el.projectSearchRegexBtn.addEventListener("click", () => toggleProjectSearchOption("regexp"));
  el.projectReplaceToggleBtn.addEventListener("click", toggleProjectReplace);
  el.projectReplaceAllBtn.addEventListener("click", replaceAllProjectMatches);
  el.projectSearchResults.addEventListener("click", handleProjectSearchResultsClick);
  el.projectSearchResults.addEventListener("scroll", handleProjectSearchResultsScroll);
  el.configTrigger.addEventListener("click", () => {
    closeSuitePicker();
    closeKeywordPanel();
    el.configPicker.classList.toggle("is-open");
    el.configTrigger.setAttribute(
      "aria-expanded",
      String(el.configPicker.classList.contains("is-open")),
    );
  });
  el.fileFilter.addEventListener("input", () => {
    const value = el.fileFilter.value.trim().toLowerCase();
    if (state.activeView === "build") {
      state.buildCaseFilter = value;
      scheduleBuildCaseTreeRender();
      return;
    }
    state.filter = value;
    scheduleFileTreeRender();
  });
  if (typeof api.onExecutionEvent === "function") {
    api.onExecutionEvent(handleExecutionEvent);
  }
  if (typeof api.onBuildEvent === "function") {
    api.onBuildEvent(handleBuildEvent);
  }
  if (el.runtimePythonSelectDirBtn) {
    el.runtimePythonSelectDirBtn.addEventListener("click", () => changeRuntime("python", false, "python-directory"));
  }
  if (el.runtimePythonAutoBtn) {
    el.runtimePythonAutoBtn.addEventListener("click", () => changeRuntime("python", true));
  }
  if (el.runtimeAllureSelectBtn) {
    el.runtimeAllureSelectBtn.addEventListener("click", () => changeRuntime("allure", false));
  }
  if (el.runtimeAllureAutoBtn) {
    el.runtimeAllureAutoBtn.addEventListener("click", () => changeRuntime("allure", true));
  }
}

function showActionFeedback(message, level = "info") {
  if (!el.actionStatus) {
    return;
  }
  el.actionStatus.textContent = message;
  el.actionStatus.title = message;
  el.actionStatus.classList.remove("is-info", "is-pass", "is-warn", "is-error");
  el.actionStatus.classList.add(`is-${level}`);
}
function currentCommand() {
  if (!state.snapshot) {
    return "pytest-dsl";
  }
  if (state.activeView === "build") {
    return buildCommandLabel(activeBuildCommandId());
  }
  if (!state.currentFile || !isExecutableFile(state.currentFile)) {
    return suiteCommandLabel(currentSelectedSuiteIds("debug"), selectedConfigSources().map((source) => source.relativePath), "debug");
  }
  const selection = CM6.getSelection();
  const sourceLabel = executionController.executionSourceLabel(state.currentFile, selection, null);
  return executionController.executionCommandLabel("run", sourceLabel, selectedConfigSources().map((source) => source.relativePath));
}
