export function createConsoleBuffer() {
  return {
    lines: [],
    commandOutputChunks: [],
    droppedLineCount: 0,
  };
}

export function createConsoleView() {
  return {
    wrap: true,
    open: false,
    expanded: false,
  };
}

export function createCommandPreview(command = "pytest-dsl") {
  return {
    command,
    context: "preview",
    persistent: false,
    taskId: null,
  };
}

export function createCommandBar(command = "pytest-dsl") {
  return {
    command,
    context: "preview",
    locked: false,
    taskId: null,
  };
}

export function emptyRemoteStatus() {
  return {
    servers: [],
    counts: { online: 0, offline: 0, unchecked: 0 },
    checkedAt: null,
    loading: false,
  };
}

export function createInitialState() {
  return {
    snapshot: null,
    currentFile: null,
    dirty: false,
    filter: "",
    buildCaseFilter: "",
    selectedConfigPaths: [],
    selectedSuiteIds: [],
    selectedFileOverrides: {},
    selectedBuildSuiteIds: [],
    selectedBuildFileOverrides: {},
    expandedSuiteNodes: new Set(),
    suiteSelectionTouched: false,
    buildSelectionTouched: false,
    selectedTreePath: "",
    selectedTreeKind: "directory",
    activeView: "debug",
    buildCaseTreeSignature: null,
    collapsedTreeDirs: new Set(),
    configSignature: null,
    remoteStatus: emptyRemoteStatus(),
    remoteProbeSeq: 0,
    remoteMonitorTimer: null,
    remoteMonitorRunning: false,
    currentTaskId: null,
    currentTaskMode: null,
    currentBuildId: null,
    currentBuildStatus: "",
    currentBuildReportUrl: "",
    currentBuildReportText: "",
    currentBuildResultsDir: "",
    runtimeStatus: {
      config: { pythonExecutable: null, allureExecutable: null },
      python: null,
      allure: null,
    },
    buildReportReloadTimer: null,
    buildReportReloadSeq: 0,
    buildReportRevealRaf: null,
    buildReportRevealTimer: null,
    buildHistory: [],
    currentDebugLine: null,
    debugStartLine: null,
    debugPaused: false,
    debugSelection: null,
    readonlySource: null,
    keywordPanelOpen: false,
    keywordSearchTimer: null,
    keywordLoadSeq: 0,
    keywordLoading: false,
    keywords: [],
    completionKeywords: [],
    completionKeywordProjectRoot: null,
    completionKeywordsLoaded: false,
    completionKeywordLoadPromise: null,
    consoleBuffers: {
      debug: createConsoleBuffer(),
      build: createConsoleBuffer(),
    },
    console: {
      activeScope: "debug",
      debug: createConsoleView(),
      build: createConsoleView(),
    },
    commandPreviews: {
      debug: createCommandPreview(),
      build: createCommandPreview(),
    },
    commandBar: createCommandBar(),
    consoleRenderScheduled: false,
    consoleRenderRaf: null,
    consoleRenderTimer: null,
    fileTreeRenderScheduled: false,
    fileTreeRenderRaf: null,
    fileTreeRenderTimer: null,
    buildCaseTreeRenderScheduled: false,
    buildCaseTreeRenderRaf: null,
    buildCaseTreeRenderTimer: null,
    treeContext: null,
    draggedTreeFile: null,
    treeDropTargetPath: null,
    entryDialogResolve: null,
    entryDialogPreviousFocus: null,
  };
}

export const REMOTE_MONITOR_INTERVAL_MS = 5000;
export const MAX_CONSOLE_BUFFER_LINES = 2000;
export const MAX_CONSOLE_RENDER_LINES = 600;
export const TREE_ROW_HEIGHT = 34;
export const TREE_RENDER_OVERSCAN = 12;
export const TREE_FALLBACK_VIEW_ROWS = 80;
export const LAYOUT_STORAGE_KEY = "pytest-dsl-gui-layout";
export const LAYOUT_SIZES = {
  nav: {
    cssVar: "--nav-width",
    defaultValue: 308,
    min: 248,
    max: 560,
    axis: "x",
  },
  console: {
    cssVar: "--console-height",
    defaultValue: 190,
    min: 120,
    max: 380,
    axis: "y",
  },
};

export const REMOTE_STATUS_LABELS = {
  online: "在线",
  offline: "离线",
  unchecked: "未探测",
};

export const COMMAND_CONTEXT_LABELS = {
  preview: "当前命令",
  syntax: "语法检查",
  run: "文件运行",
  debug: "调试",
  suite: "测试套运行",
  build: "构建运行",
};

export const BUILD_STATUS_LABELS = {
  passed: "构建通过",
  failed: "构建失败",
  stopped: "构建已停止",
};

export function isPythonRuntimeAvailable(state) {
  return Boolean(
    state &&
    state.snapshot &&
    state.runtimeStatus &&
    state.runtimeStatus.python &&
    state.runtimeStatus.python.available,
  );
}

export function pythonRuntimeUnavailableMessage(state) {
  const info = state && state.runtimeStatus ? state.runtimeStatus.python : null;
  const detail = info && info.message ? ` ${info.message}` : "";
  return `Python 运行环境不可用，无法调试或构建。${detail}`.trim();
}

export function isAllureRuntimeAvailable(state) {
  return Boolean(
    state &&
    state.snapshot &&
    state.runtimeStatus &&
    state.runtimeStatus.allure &&
    state.runtimeStatus.allure.available,
  );
}

export function allureRuntimeUnavailableMessage(state) {
  const info = state && state.runtimeStatus ? state.runtimeStatus.allure : null;
  const action = info && info.action
    ? ` ${info.action}`
    : " 请执行 npm install -g allure 安装 Allure 3。";
  return `未检测到 Allure 3，构建会继续运行 pytest，但不会展示或下载 Allure 报告。${action}`.trim();
}
