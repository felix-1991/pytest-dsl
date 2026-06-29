import { errorMessage } from "./utils.js";

export function createWorkspaceController({
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
}) {
  function switchWorkspaceView(view) {
    const nextView = view === "build" ? "build" : "debug";
    const isBuildView = nextView === "build";
    if (isBuildView && !confirmDiscardDirtyBeforeBuild()) {
      return;
    }
    state.activeView = nextView;
    el.debugWorkspace.hidden = isBuildView;
    el.buildPanel.hidden = !isBuildView;
    el.topbar.classList.toggle("is-build-view", isBuildView);
    el.suitePicker.hidden = isBuildView;
    el.runAllBtn.hidden = isBuildView;
    if (isBuildView) {
      closeSuitePicker();
    }
    el.debugNavBtn.classList.toggle("is-active", !isBuildView);
    el.buildNavBtn.classList.toggle("is-active", isBuildView);
    updateTreePaneForActiveView();
    setConsoleScope(nextView);
    syncBuildReportFrameVisibility({ defer: isBuildView });
    if (isBuildView) {
      ensureBuildCaseTreeRootExpanded();
      ensureBuildCaseTreeRendered();
      updateBuildSummary();
      previewCommand(buildCommandLabel(), { force: true, scope: "build" });
    } else {
      previewCommand(currentCommand(), { force: true, scope: "debug" });
    }
  }

  function confirmDiscardDirtyBeforeBuild() {
    // Check ALL open tabs, not just the active one
    const dirtyFiles = state.openFiles.filter((f) => f.dirty);
    if (dirtyFiles.length === 0) {
      return true;
    }
    const labels = dirtyFiles.map((f) => `"${f.label}"`).join(", ");
    const confirmed = window.confirm(
      `以下文件有未保存修改: ${labels}。切换到构建页面前请确认。继续切换？`,
    );
    if (!confirmed) {
      showActionFeedback("当前文件有未保存修改，已停留在调试页面", "warn");
    }
    return confirmed;
  }

  function closeSuitePicker() {
    el.suitePicker.classList.remove("is-open");
    el.suiteTrigger.setAttribute("aria-expanded", "false");
  }

  function closeConfigPicker() {
    el.configPicker.classList.remove("is-open");
    el.configTrigger.setAttribute("aria-expanded", "false");
  }

  function closeTopPickers() {
    closeSuitePicker();
    closeConfigPicker();
  }

  function isSaveShortcut(event) {
    if (!event || event.defaultPrevented) {
      return false;
    }
    return (
      event.key.toLowerCase() === "s" &&
      (event.ctrlKey || event.metaKey) &&
      !event.altKey && !event.shiftKey
    );
  }

  async function handleEditorSaveShortcut(event) {
    if (!isSaveShortcut(event)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    await saveCurrentFile({ source: "shortcut" });
  }

  function closeTransientPanelsForOutsideClick(event) {
    if (!el.treeContextMenu.contains(event.target)) {
      closeTreeContextMenu();
    }
    if (!el.suitePicker.contains(event.target)) {
      closeSuitePicker();
    }
    if (!el.configPicker.contains(event.target)) {
      closeConfigPicker();
    }
    if (
      !el.keywordPanel.contains(event.target) &&
      !el.keywordBtn.contains(event.target)
    ) {
      closeKeywordPanel();
    }
  }

  function updateTreePaneForActiveView() {
    const isBuildView = state.activeView === "build";
    el.treePaneTitle.textContent = isBuildView ? "构建案例" : "目录树";
    el.fileTree.hidden = isBuildView;
    el.buildCaseTree.hidden = !isBuildView;
    el.fileFilter.placeholder = isBuildView ? "筛选案例" : "筛选文件";
    const nextFilter = isBuildView ? state.buildCaseFilter : state.filter;
    if (el.fileFilter.value !== nextFilter) {
      el.fileFilter.value = nextFilter;
    }
  }

  function handleBuildCaseTreeScroll() {
    scheduleBuildCaseTreeRender();
  }

  async function generateCurrentCommand() {
    const command = normalizeCommandText(currentCommand());
    previewCommand(command, { force: true });
    lockGeneratedCommand(command);
    appendLog("info", `命令已锁定: ${command}`);
    showActionFeedback("命令已锁定", "info");
    return command;
  }

  async function copyGeneratedCommand() {
    const command = normalizeCommandText(state.commandBar.command || currentCommand());
    if (!command) {
      appendLog("warn", "没有可复制的命令");
      return "";
    }

    if (typeof api.copyText !== "function") {
      appendLog("warn", "当前环境不支持复制命令");
      return command;
    }

    try {
      await api.copyText(command);
      appendLog("pass", "命令已复制");
      showActionFeedback("命令已复制", "pass");
    } catch (error) {
      appendLog("warn", `复制命令失败: ${errorMessage(error)}`);
    }

    return command;
  }

  return {
    switchWorkspaceView,
    confirmDiscardDirtyBeforeBuild,
    closeSuitePicker,
    closeConfigPicker,
    closeTopPickers,
    isSaveShortcut,
    handleEditorSaveShortcut,
    closeTransientPanelsForOutsideClick,
    updateTreePaneForActiveView,
    handleBuildCaseTreeScroll,
    generateCurrentCommand,
    copyGeneratedCommand,
  };
}
