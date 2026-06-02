const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const html = fs.readFileSync(
  path.resolve(__dirname, "../src/index.html"),
  "utf8",
);
const renderer = fs.readFileSync(
  path.resolve(__dirname, "../src/renderer.js"),
  "utf8",
);
const main = fs.readFileSync(
  path.resolve(__dirname, "../main.js"),
  "utf8",
);
const preload = fs.readFileSync(
  path.resolve(__dirname, "../preload.js"),
  "utf8",
);
const editorBridge = fs.readFileSync(
  path.resolve(__dirname, "../src/editor-bridge.js"),
  "utf8",
);
const css = fs.readFileSync(
  path.resolve(__dirname, "../src/styles.css"),
  "utf8",
);

test("renderer keeps the demo-aligned workbench shell", () => {
  [
    "suiteDirectory",
    "configPicker",
    "configTrigger",
    "configSummary",
    "remoteStatusSummary",
    "remoteServiceRows",
    "remoteStatusBar",
    "runAllBtn",
    "debugStepsBtn",
    "nextStepBtn",
    "continueDebugBtn",
    "bottomConsole",
    "consoleBody",
    "commandPreview",
    "configDiagnostics",
    "configMerged",
    "metadataList",
    "deductionList",
  ].forEach((id) => {
    assert.match(html, new RegExp(`id="${id}"`), `missing #${id}`);
  });

  assert.match(html, /运行输出/);
  assert.match(html, /配置诊断/);
  assert.doesNotMatch(html, /id="outputPanel"/);
  assert.doesNotMatch(html, /运行上下文/);
  assert.doesNotMatch(html, /ACP Agent/);
  assert.doesNotMatch(html, /class="agent-chatbox"/);
  assert.doesNotMatch(html, /class="agent-chip"/);
});

test("renderer removes fake window dots and exposes project tree controls", () => {
  assert.doesNotMatch(html, /class="window-dots"/);
  assert.match(html, /id="openProjectBtn"/);
  assert.match(html, /id="expandAllBtn"/);
  assert.match(html, /id="collapseAllBtn"/);
  assert.match(html, /打开项目/);
});

test("renderer starts empty so the GUI can open external projects", () => {
  assert.doesNotMatch(renderer, /loadDefaultProject\(\);/);
  assert.match(renderer, /setEmptyProjectState\(\);/);
});

test("config picker supports multi-select and remote status UI", () => {
  assert.match(html, /远程关键字服务/);
  assert.match(renderer, /type="checkbox"/);
  assert.match(renderer, /selectedConfigPaths/);
  assert.match(renderer, /handleConfigSelectionChange/);
  assert.match(renderer, /checkRemoteServers/);
  assert.match(renderer, /extractRemoteServers/);
  assert.match(css, /\.config-option/);
  assert.match(css, /\.remote-service-row/);
});

test("renderer dynamically monitors remote services and config changes", () => {
  assert.match(renderer, /REMOTE_MONITOR_INTERVAL_MS\s*=\s*5000/);
  assert.match(renderer, /startDynamicRemoteMonitoring/);
  assert.match(renderer, /refreshProjectConfigIfChanged/);
  assert.match(renderer, /scanProjectConfig/);
  assert.match(renderer, /setInterval\(\s*runDynamicRemoteMonitorTick,\s*REMOTE_MONITOR_INTERVAL_MS\s*\)/);
  assert.doesNotMatch(renderer, /setInterval\(\s*refreshProject/);
});

test("renderer exposes tree icons and a CodeMirror 6 editor", () => {
  assert.match(html, /id="codeEditor"/);
  assert.match(html, /editor-bundle\.js/);
  assert.match(html, /placeholder="筛选文件"/);
  assert.doesNotMatch(html, /id="editorHighlight"/);
  assert.doesNotMatch(html, /contenteditable="true"/);
  assert.match(renderer, /CM6\.createEditor/);
  assert.match(renderer, /CM6\.getContent/);
  assert.match(renderer, /CM6\.setLanguage/);
  assert.match(renderer, /onContentChange/);
  assert.match(renderer, /fileIcon/);
  assert.match(renderer, /folderIcon/);
  assert.match(renderer, /editableFiles/);
  assert.match(renderer, /language === "resource"/);
  assert.match(renderer, /language === "markdown"/);
  assert.match(css, /\.fileIcon\.markdown/);
  assert.match(css, /\.tok-heading/);
  assert.match(css, /\.tok-link/);
  assert.doesNotMatch(css, /resize:\s*none/);
});

test("file tree renders root files inline and uses folder open/closed icons", () => {
  assert.match(renderer, /renderFileRow/);
  assert.match(renderer, /renderDirectoryGroup/);
  assert.match(renderer, /group\.name !== "\."/);
  assert.match(renderer, /folderIcon\("open"\)/);
  assert.match(renderer, /folderIcon\("closed"\)/);
  assert.match(css, /\.tree-group\.is-collapsed\s+\.folder-open/);
  assert.match(css, /\.tree-group:not\(\.is-collapsed\)\s+\.folder-closed/);
  assert.doesNotMatch(css, /transform:\s*rotate\(-90deg\)/);
});

test("editor chrome is compact so code keeps vertical space", () => {
  assert.match(html, /class="param-head"[\s\S]*class="sub-tabs"[\s\S]*class="inline-actions"/);
  assert.match(css, /\.workspace-panel\s*\{[\s\S]*grid-template-rows:\s*34px minmax\(0,\s*1fr\)/);
  assert.match(css, /\.main-stage\s*\{[\s\S]*grid-template-rows:\s*minmax\(260px,\s*1fr\) 6px var\(--console-height\)/);
  assert.match(css, /\.editor-stack\s*\{[\s\S]*grid-template-rows:\s*auto minmax\(0,\s*1fr\)/);
  assert.match(css, /\.notice\s*\{[\s\S]*display:\s*none/);
  assert.match(css, /\.request-head\s*\{[\s\S]*padding:\s*8px 14px/);
  assert.match(css, /\.param-head\s*\{[\s\S]*min-height:\s*36px/);
});

test("layout exposes resizable file tree and bottom console", () => {
  assert.match(html, /data-resizer="nav"/);
  assert.match(html, /data-resizer="console"/);
  assert.match(html, /aria-orientation="horizontal"/);
  assert.match(css, /grid-template-columns:\s*var\(--nav-width\)\s+6px\s+minmax\(0,\s*1fr\)/);
  assert.match(css, /\.shell\s*\{[^}]*padding-right:\s*12px/);
  assert.doesNotMatch(css, /--output-width/);
  assert.match(css, /\.panel-resizer/);
  assert.match(css, /\.panel-resizer\.is-horizontal/);
  assert.match(renderer, /initializeLayoutSizing/);
  assert.match(renderer, /bindPanelResizers/);
  assert.match(renderer, /setLayoutSize/);
  assert.match(renderer, /--console-height/);
});

test("request header keeps execution controls visible in constrained workspaces", () => {
  assert.match(css, /\.request-head\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
  assert.match(css, /\.head-actions\s*\{[\s\S]*justify-content:\s*flex-start/);
  assert.match(css, /\.head-actions\s*\{[\s\S]*overflow:\s*visible/);
  assert.doesNotMatch(css, /\.request-head\s*\{[\s\S]*grid-template-columns:\s*minmax\(240px,\s*1fr\) minmax\(0,\s*auto\)/);
});

test("file toolbar separates edit, execution, and debug session controls", () => {
  assert.match(html, /id="editActionGroup"/);
  assert.match(html, /id="executionActionGroup"/);
  assert.match(html, /id="debugSessionGroup"/);
  assert.match(css, /\.action-group/);
  assert.match(renderer, /isExecutableFile/);
  assert.match(renderer, /isRunnableWholeFile/);
  assert.match(renderer, /debugStartLine/);
});

test("renderer limits execution controls to DSL and resource files", () => {
  assert.match(renderer, /function isExecutableFile/);
  assert.match(renderer, /language === "dsl" \|\| language === "resource"/);
  assert.match(renderer, /CM6\.getSelection\(\)/);
  assert.match(renderer, /executionActionGroup\.hidden/);
  assert.match(renderer, /debugSessionGroup\.hidden/);
  assert.doesNotMatch(renderer, /当前文件不是 DSL 文件/);
});

test("workspace title removes the redundant DSL badge", () => {
  assert.doesNotMatch(html, /<span class="pill violet">DSL<\/span>/);
  assert.match(css, /\.tree-row\s*\{/);
  assert.match(css, /grid-template-columns:\s*34px minmax\(0,\s*1fr\) auto/);
});

test("renderer wires syntax, run, debug, and stop to real execution IPC", () => {
  assert.match(main, /execution:start/);
  assert.match(main, /execution:stop/);
  assert.match(main, /execution:command/);
  assert.match(main, /execution:event/);
  assert.match(preload, /startExecution/);
  assert.match(preload, /stopExecution/);
  assert.match(preload, /sendExecutionCommand/);
  assert.match(preload, /onExecutionEvent/);
  assert.match(renderer, /runExecutionTask/);
  assert.match(renderer, /sendDebugCommand/);
  assert.match(renderer, /debugFromLine/);
  assert.match(renderer, /debugScope/);
  assert.match(renderer, /onGutterClick/);
  assert.match(renderer, /CM6\.getSelection/);
  assert.match(renderer, /setRunningState/);
  assert.match(renderer, /currentDebugLine/);
  assert.match(renderer, /api\.startExecution/);
  assert.match(renderer, /api\.stopExecution/);
  assert.match(renderer, /api\.sendExecutionCommand/);
  assert.doesNotMatch(renderer, /previewSyntaxCheck/);
  assert.doesNotMatch(renderer, /previewRunFile/);
  assert.doesNotMatch(renderer, /previewDebugSteps/);
  assert.match(css, /\.cm-line\.is-debug-selected/);
  assert.match(css, /\.cm-line\.is-debug-current/);
});

test("editor keyword browser uses pytest-dsl keyword data and inserts snippets", () => {
  assert.match(html, /id="keywordPanel"/);
  assert.match(html, /id="keywordSearch"/);
  assert.match(html, /id="keywordList"/);
  assert.match(html, /id="keywordStatus"/);
  assert.doesNotMatch(html, /id="formatBtn"/);
  assert.doesNotMatch(html, />\s*格式化\s*</);

  assert.match(main, /keyword:list/);
  assert.match(main, /clipboard:write/);
  assert.match(preload, /listKeywords/);
  assert.match(preload, /copyText/);
  assert.match(renderer, /toggleKeywordPanel/);
  assert.match(renderer, /loadKeywords/);
  assert.match(renderer, /renderKeywordList/);
  assert.match(renderer, /insertKeyword/);
  assert.match(renderer, /buildKeywordSnippet/);
  assert.match(renderer, /api\.listKeywords/);
  assert.match(renderer, /CM6\.insertText/);
  assert.match(editorBridge, /insertText/);
  assert.match(css, /\.keyword-panel/);
  assert.match(css, /\.keyword-row/);
  assert.doesNotMatch(renderer, /Keyword panel shell is not implemented/);
  assert.doesNotMatch(renderer, /Format preview/);
});

test("generate command action updates and copies the current command", () => {
  assert.match(renderer, /generateCurrentCommand/);
  assert.match(renderer, /api\.copyText/);
  assert.match(renderer, /Generated command:/);
  assert.match(renderer, /Command copied to clipboard/);
});

test("editor exposes go-to-definition for DSL keyword calls", () => {
  assert.match(main, /keyword:definition/);
  assert.match(main, /source:read/);
  assert.match(preload, /findKeywordDefinitions/);
  assert.match(preload, /readSourceFile/);

  assert.match(editorBridge, /getKeywordUnderCursor/);
  assert.match(editorBridge, /onDefinitionRequest/);
  assert.match(editorBridge, /EditorView\.domEventHandlers/);
  assert.match(editorBridge, /Mod-Click/);
  assert.match(editorBridge, /F12/);

  assert.match(renderer, /handleDefinitionRequest/);
  assert.match(renderer, /goToKeywordDefinition/);
  assert.match(renderer, /openDefinitionTarget/);
  assert.match(renderer, /openExternalReadonlySource/);
  assert.match(renderer, /api\.findKeywordDefinitions/);
  assert.match(renderer, /api\.readSourceFile/);
  assert.match(renderer, /CM6\.scrollToLine/);
  assert.match(renderer, /readonlySource/);
});
