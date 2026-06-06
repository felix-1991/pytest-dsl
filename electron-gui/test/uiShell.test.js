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
    "suitePicker",
    "suiteTrigger",
    "suiteSummary",
    "suiteList",
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
    "clearConsoleBtn",
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

test("suite runner uses multi-select suite controls", () => {
  assert.match(html, /id="suitePicker"/);
  assert.match(html, /id="suiteTrigger"/);
  assert.match(html, /id="suiteSummary"/);
  assert.match(html, /id="suiteList"/);
  assert.doesNotMatch(html, /multiple/);
  assert.doesNotMatch(html, /id="suiteDirectory"/);
  assert.match(renderer, /selectedSuiteIds/);
  assert.match(renderer, /renderSuiteOptions\(snapshot\.suites[\s\S]*snapshot\.suiteTree/);
  assert.match(renderer, /renderSuiteTreeNode/);
  assert.match(renderer, /handleSuiteSelectionChange/);
  assert.match(renderer, /suiteSelectionTouched/);
  assert.match(renderer, /data-suite-checkbox/);
  assert.match(renderer, /data-suite-ids/);
  assert.match(renderer, /collectSuiteNodeSuiteIds/);
  assert.match(renderer, /syncSuiteTreeCheckboxStates/);
  assert.match(renderer, /suiteIdsFromSuiteInput/);
  assert.match(renderer, /normalizeSelectedSuiteIds/);
  assert.match(renderer, /indeterminate/);
  assert.doesNotMatch(renderer, /return selected\.length > 0 \? selected : availableIds/);
  assert.match(renderer, /runSuiteExecution/);
  assert.match(renderer, /mode:\s*"suite"/);
  assert.match(css, /\.suite-node/);
  assert.match(css, /\.suite-option\.is-partial/);
});

test("renderer removes fake window dots and exposes project tree controls", () => {
  assert.doesNotMatch(html, /class="window-dots"/);
  assert.match(html, /id="openProjectBtn"/);
  assert.match(html, /id="treeRefreshBtn"/);
  assert.doesNotMatch(html, /id="createFileBtn"/);
  assert.doesNotMatch(html, /id="createFolderBtn"/);
  assert.match(html, /id="expandAllBtn"/);
  assert.match(html, /id="collapseAllBtn"/);
  assert.match(html, /id="treeContextMenu"/);
  assert.match(html, /id="entryDialog"/);
  assert.match(html, /id="entryDialogInput"/);
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

test("file tree renders root files inline and uses a single stateful folder icon", () => {
  assert.match(renderer, /renderFileRow/);
  assert.match(renderer, /renderProjectTreeNode/);
  assert.match(renderer, /filterProjectTree/);
  assert.match(renderer, /folderIcon\(collapsed \? "closed" : "open"\)/);
  assert.doesNotMatch(renderer, /class="folder-open"/);
  assert.doesNotMatch(renderer, /class="folder-closed"/);
  assert.match(renderer, /handleCreateFile/);
  assert.match(renderer, /handleCreateFolder/);
  assert.match(renderer, /requestEntryName/);
  assert.match(renderer, /handleEntryDialogSubmit/);
  assert.doesNotMatch(renderer, /window\.prompt/);
  assert.match(renderer, /handleRenameEntry/);
  assert.match(renderer, /handleDeleteEntry/);
  assert.match(renderer, /handleMoveEntry/);
  assert.match(main, /file:create/);
  assert.match(main, /file:rename/);
  assert.match(main, /file:delete/);
  assert.match(main, /file:move/);
  assert.match(preload, /createEntry/);
  assert.match(preload, /renameEntry/);
  assert.match(preload, /deleteEntry/);
  assert.match(preload, /moveEntry/);
  assert.doesNotMatch(css, /\.tree-group\.is-collapsed\s+\.folder-open/);
  assert.doesNotMatch(css, /\.tree-group:not\(\.is-collapsed\)\s+\.folder-closed/);
  assert.doesNotMatch(renderer, /class="tree-node-actions"/);
  assert.match(renderer, /contextmenu/);
  assert.match(renderer, /openTreeContextMenu/);
  assert.match(renderer, /treeContextMenu\.dataset\.contextKind/);
  assert.match(renderer, /treeContextMenu\.dataset\.contextPath/);
  assert.match(renderer, /event\.stopPropagation\(\)/);
  assert.match(renderer, /data-tree-row/);
  assert.match(renderer, /draggable="true"/);
  assert.match(renderer, /handleTreeDragStart/);
  assert.match(renderer, /handleTreeDrop/);
  assert.match(renderer, /data-drop-target/);
  assert.match(css, /\.tree-context-menu/);
  assert.match(css, /\.context-menu-item/);
  assert.match(css, /\.tree-row\.is-drop-target/);
  assert.match(css, /\.modal-backdrop/);
  assert.match(css, /\.entry-dialog/);
  assert.doesNotMatch(css, /\.tree-node-actions/);
  assert.doesNotMatch(css, /transform:\s*rotate\(-90deg\)/);
});

test("editor chrome is compact so code keeps vertical space", () => {
  assert.match(html, /class="param-head"[\s\S]*class="sub-tabs"/);
  assert.match(html, /class="head-actions"[\s\S]*class="inline-actions"/);
  assert.match(css, /\.workspace-panel\s*\{[\s\S]*grid-template-rows:\s*34px minmax\(0,\s*1fr\)/);
  assert.match(css, /\.main-stage\s*\{[\s\S]*grid-template-rows:\s*minmax\(260px,\s*1fr\) 6px var\(--console-height\)/);
  assert.match(css, /\.editor-stack\s*\{[\s\S]*grid-template-rows:\s*auto minmax\(0,\s*1fr\)/);
  assert.match(css, /\.workarea\s*\{[\s\S]*height:\s*100%/);
  assert.match(css, /\.editor-stack\s*\{[\s\S]*height:\s*100%/);
  assert.match(css, /\.editor-stack\s*\{[\s\S]*overflow:\s*hidden/);
  assert.match(css, /\.code-editor\s*\{[\s\S]*min-height:\s*280px/);
  assert.match(css, /\.code-editor \.cm-scroller\s*\{[\s\S]*height:\s*100%/);
  assert.match(css, /\.code-editor \.cm-content\s*\{[\s\S]*min-height:\s*100%/);
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

test("editor tools stay in the normal toolbar and execution tools are file-aware", () => {
  assert.match(
    html,
    /class="head-actions"[\s\S]*id="executionActionGroup"[\s\S]*id="keywordBtn"[\s\S]*id="commandBtn"[\s\S]*id="editorMeta"/,
  );
  assert.doesNotMatch(html, /class="param-head"[\s\S]*id="keywordBtn"/);
  assert.doesNotMatch(
    html,
    /id="executionActionGroup"[\s\S]{0,120}\s+hidden\b/,
  );
  assert.match(renderer, /executionActionGroup\.hidden = !executable/);
  assert.match(renderer, /commandBtn\.disabled = false/);
  assert.doesNotMatch(html, /id="editorToolGroup"/);
});

test("console output can be cleared manually and resets before each execution", () => {
  assert.match(html, /id="clearConsoleBtn"/);
  assert.match(html, /title="清空运行输出"/);
  assert.match(renderer, /consoleLines:\s*\[\]/);
  assert.match(renderer, /commandOutputChunks:\s*\[\]/);
  assert.match(renderer, /clearConsoleBtn/);
  assert.match(renderer, /clearConsoleBtn\.addEventListener\("click",\s*\(\) =>\s*clearConsole\(\)/);
  assert.match(renderer, /function clearConsole\(\)\s*\{[\s\S]*consoleBody\.textContent = ""/);
  assert.match(renderer, /state\.consoleLines = \[\]/);
  assert.match(renderer, /state\.commandOutputChunks = \[\]/);
  assert.match(renderer, /function resetConsoleForExecution\(\)\s*\{[\s\S]*clearConsole\(\)/);
  assert.match(renderer, /resetConsoleForExecution\(\);[\s\S]*appendLog\("info", `\$\{executionModeLabel\(mode\)\} started:/);
  assert.match(renderer, /resetConsoleForExecution\(\);[\s\S]*appendLog\("info", `测试套运行 started:/);
});

test("console supports long output reading and copying", () => {
  [
    "copyConsoleBtn",
    "wrapConsoleBtn",
    "expandConsoleBtn",
  ].forEach((id) => {
    assert.match(html, new RegExp(`id="${id}"`), `missing #${id}`);
    assert.match(renderer, new RegExp(`${id}`), `renderer missing ${id}`);
  });
  assert.match(renderer, /copyConsoleOutput/);
  assert.match(renderer, /toggleConsoleWrap/);
  assert.match(renderer, /toggleConsoleExpanded/);
  assert.match(renderer, /state\.commandOutputChunks\.join\(""\)/);
  assert.doesNotMatch(renderer, /copyConsoleOutput\(\)[\s\S]*state\.consoleLines\.join\("\\n"\)/);
  assert.match(renderer, /console\.wrap/);
  assert.match(renderer, /console\.expanded/);
  assert.match(css, /\.console-body\s*\{[\s\S]*user-select:\s*text/);
  assert.match(css, /\.console\.is-unwrapped\s+\.log-message/);
  assert.match(css, /\.main-stage\.is-console-expanded/);
});

test("console header keeps its label stable when command preview is long", () => {
  assert.match(css, /\.console-head\s*\{[\s\S]*min-width:\s*0/);
  assert.match(css, /\.console-head\s*\{[\s\S]*justify-content:\s*flex-start/);
  assert.match(css, /\.console-tab\s*\{[\s\S]*flex:\s*0 0 auto/);
  assert.match(css, /\.console-tab\s*\{[\s\S]*white-space:\s*nowrap/);
  assert.match(html, /id="commandContext"/);
  assert.match(renderer, /preview:\s*"当前命令"/);
  assert.doesNotMatch(renderer, /preview:\s*"预览"/);
  assert.match(css, /\.command-context\s*\{[\s\S]*flex:\s*0 0 auto/);
  assert.doesNotMatch(css, /\.command-context\s*\{[^}]*border:/);
  assert.doesNotMatch(css, /\.command-context\s*\{[^}]*background:/);
  assert.match(css, /#commandPreview\s*\{[\s\S]*flex:\s*1 1 0%/);
  assert.match(css, /#commandPreview\s*\{[\s\S]*min-width:\s*0/);
  assert.match(css, /\.console-tool-btn\s*\{[\s\S]*flex:\s*0 0 auto/);
});

test("console command preview preserves the last actual execution context", () => {
  assert.match(renderer, /commandPreview:\s*\{/);
  assert.match(renderer, /function previewCommand\(/);
  assert.match(renderer, /function setExecutionCommand\(/);
  assert.match(renderer, /function releaseExecutionCommand\(/);
  assert.match(renderer, /updateCommandPreview\(event\.command \|\| currentCommand\(\),\s*\{[\s\S]*taskId:\s*event\.taskId/);
  assert.match(renderer, /releaseExecutionCommand\(event\.taskId\)/);
  assert.doesNotMatch(renderer, /if \(!isRunning\) \{\s*updateCommandPreview\(currentCommand\(\)\);\s*\}/);
});

test("editor keyword tools stay available outside active debug sessions", () => {
  assert.match(html, /class="head-actions"[\s\S]*id="keywordBtn"[\s\S]*id="commandBtn"/);
  assert.doesNotMatch(renderer, /keywordBtn\.disabled = !executable/);
  assert.match(renderer, /keywordBtn\.disabled = !hasFile \|\| readonlySource \|\| !isExecutableFile\(state\.currentFile\)/);
  assert.doesNotMatch(renderer, /!state\.currentFile \|\| !isExecutableFile\(state\.currentFile\)[\s\S]*当前文件不支持关键字插入/);
  assert.match(renderer, /renderActiveFile\(\)[\s\S]*updateFileActionState\(\)/);
  assert.match(css, /\.param-head\s*\{[\s\S]*grid-template-columns:/);
  assert.match(css, /\.inline-actions\s*\{[\s\S]*overflow:\s*visible/);
});

test("renderer limits execution controls to DSL and resource files", () => {
  assert.match(renderer, /function isExecutableFile/);
  assert.match(renderer, /language === "dsl" \|\| language === "resource"/);
  assert.match(renderer, /CM6\.getSelection\(\)/);
  assert.match(renderer, /executionActionGroup\.hidden = !executable/);
  assert.match(renderer, /debugSessionGroup\.hidden/);
  assert.doesNotMatch(renderer, /当前文件不是 DSL 文件/);
});

test("workspace title removes the redundant DSL badge", () => {
  assert.doesNotMatch(html, /<span class="pill violet">DSL<\/span>/);
  assert.match(css, /\.tree-row\s*\{/);
  assert.match(css, /grid-template-columns:\s*24px minmax\(0,\s*1fr\) auto/);
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
