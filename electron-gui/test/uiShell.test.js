const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const html = fs.readFileSync(
  path.resolve(__dirname, "../src/index.html"),
  "utf8",
);
const rendererEntry = fs.readFileSync(
  path.resolve(__dirname, "../src/renderer.js"),
  "utf8",
);
const rendererModules = [
  "../src/renderer/buildReportController.js",
  "../src/renderer/commandController.js",
  "../src/renderer/configController.js",
  "../src/renderer/consoleController.js",
  "../src/renderer/executionController.js",
  "../src/renderer/fileController.js",
  "../src/renderer/keywordController.js",
  "../src/renderer/layoutController.js",
  "../src/renderer/projectController.js",
  "../src/renderer/projectTreeController.js",
  "../src/renderer/remoteStatusController.js",
  "../src/renderer/runtimeController.js",
  "../src/renderer/state.js",
  "../src/renderer/suiteTreeController.js",
  "../src/renderer/treeVirtualizer.js",
  "../src/renderer/utils.js",
  "../src/renderer/workspaceController.js",
]
  .map((modulePath) => fs.readFileSync(path.resolve(__dirname, modulePath), "utf8"))
  .join("\n");
const renderer = [rendererEntry, rendererModules].join("\n");
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
const checkAppFiles = fs.readFileSync(
  path.resolve(__dirname, "../scripts/check-app-files.js"),
  "utf8",
);

test("renderer keeps the demo-aligned workbench shell", () => {
  assert.match(html, /<script type="module" src="\.\/renderer\.js"><\/script>/);
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
    "consoleToggleBtn",
    "consoleStatusToggleBtn",
    "clearConsoleBtn",
    "commandPreview",
    "actionStatus",
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

test("app file check validates the split renderer module graph", () => {
  assert.match(checkAppFiles, /require\("esbuild"\)/);
  assert.match(checkAppFiles, /entryPoints:\s*\[path\.join\(root,\s*"src",\s*"renderer\.js"\)\]/);
  assert.match(checkAppFiles, /bundle:\s*true/);
  assert.match(checkAppFiles, /platform:\s*"browser"/);
  assert.match(checkAppFiles, /write:\s*false/);
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

test("build center exposes pytest plus Allure report orchestration", () => {
  [
    "debugNavBtn",
    "buildNavBtn",
    "debugWorkspace",
    "buildPanel",
    "buildCaseTree",
    "buildRunBtn",
    "buildStopBtn",
    "buildOpenReportBtn",
    "buildDownloadReportBtn",
    "buildDownloadLogsBtn",
    "buildStatus",
    "buildConfigSummary",
    "buildPytestArgs",
    "buildAllureStatus",
    "buildCommand",
    "buildReportUrl",
    "buildReportFrame",
    "buildResultsDir",
    "buildHistoryList",
  ].forEach((id) => {
    assert.match(html, new RegExp(`id="${id}"`), `missing #${id}`);
  });

  assert.match(main, /build:start/);
  assert.match(main, /build:stop/);
  assert.match(main, /build:download-report/);
  assert.match(main, /build:download-logs/);
  assert.match(main, /build:event/);
  assert.match(preload, /startBuild/);
  assert.match(preload, /stopBuild/);
  assert.match(preload, /downloadBuildReport/);
  assert.match(preload, /downloadBuildLogs/);
  assert.match(preload, /onBuildEvent/);
  assert.match(renderer, /switchWorkspaceView/);
  assert.match(renderer, /renderBuildCaseTree/);
  assert.match(renderer, /bindSuiteTreeEvents/);
  assert.match(renderer, /runBuildExecution/);
  assert.match(renderer, /handleBuildEvent/);
  assert.match(renderer, /currentBuildReportText/);
  assert.match(renderer, /buildHistory/);
  assert.match(renderer, /recordBuildHistory/);
  assert.match(renderer, /BUILD_STATUS_LABELS/);
  assert.match(renderer, /buildStatusLabel/);
  assert.match(renderer, /activeBuildCommandId/);
  assert.match(renderer, /state\.currentTaskMode === "build"/);
  assert.match(renderer, /api\.startBuild/);
  assert.match(renderer, /api\.stopBuild/);
  assert.match(renderer, /api\.downloadBuildReport/);
  assert.match(renderer, /api\.downloadBuildLogs/);
  assert.match(renderer, /buildReportFrame/);
  assert.match(renderer, /event\.type === "report-unavailable"/);
  assert.match(html, /<iframe[\s\S]*id="buildReportFrame"[\s\S]*hidden/);
  assert.match(css, /\.build-panel/);
  assert.match(css, /\.build-case-tree/);
  assert.match(css, /\.build-history/);
  assert.match(css, /\.report-frame/);
});

test("build view hides debug suite controls and uses the left build tree as scope", () => {
  assert.match(html, /id="topbar"/);
  assert.match(html, /id="buildCaseTree"/);
  assert.match(html, /运行并生成报告/);
  assert.doesNotMatch(html, />\s*运行构建\s*</);
  assert.match(renderer, /el\.topbar\.classList\.toggle\("is-build-view", isBuildView\)/);
  assert.match(renderer, /el\.suitePicker\.hidden = isBuildView/);
  assert.match(renderer, /el\.runAllBtn\.hidden = isBuildView/);
  assert.match(renderer, /el\.fileTree\.hidden = isBuildView/);
  assert.match(renderer, /el\.buildCaseTree\.hidden = !isBuildView/);
  assert.match(renderer, /selectedBuildSuiteIds/);
  assert.match(renderer, /selectedBuildFileOverrides/);
  assert.match(renderer, /data-suite-scope/);
  assert.match(renderer, /currentSelectedSuiteIds\("build"\)/);
});

test("debug and build topbars keep project path readable and controls aligned", () => {
  const readableProjectColumn = String.raw`minmax\(320px,\s*0\.95fr\)`;
  assert.match(
    css,
    new RegExp(
      String.raw`\.topbar\s*\{[\s\S]*grid-template-columns:\s*${readableProjectColumn}\s+minmax\(220px,\s*300px\)\s+minmax\(360px,\s*1\.1fr\)`,
    ),
  );
  assert.match(
    css,
    new RegExp(
      String.raw`\.topbar\.is-build-view\s*\{[\s\S]*grid-template-columns:\s*minmax\(320px,\s*460px\)\s+minmax\(0,\s*1fr\)`,
    ),
  );
  assert.match(css, /\.topbar\s*\{[\s\S]*gap:\s*12px/);
  assert.match(css, /\.topbar\s*\{[\s\S]*min-height:\s*56px/);
  assert.match(css, /\.topbar\.is-build-view \.top-actions\s*\{[\s\S]*grid-column:\s*2/);
  assert.match(css, /\.suite-picker\s*\{[\s\S]*width:\s*100%/);
  assert.match(css, /\.top-actions\s*\{[\s\S]*display:\s*grid/);
  assert.match(css, /\.top-actions\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto\s+auto\s+auto/);
  assert.match(css, /\.top-actions \.config-picker\s*\{[\s\S]*width:\s*100%/);
  assert.match(css, /\.remote-summary\s*\{[\s\S]*flex:\s*0 1 auto/);
  assert.match(css, /\.remote-summary span:last-child\s*\{[\s\S]*text-overflow:\s*ellipsis/);
});

test("switching to build warns before leaving unsaved editor changes", () => {
  assert.match(renderer, /function confirmDiscardDirtyBeforeBuild\(\)/);
  assert.match(renderer, /state\.dirty/);
  assert.match(renderer, /window\.confirm\("当前文件有未保存修改，切换到构建页面前请确认。继续切换？"\)/);
  assert.match(renderer, /if \(isBuildView && !confirmDiscardDirtyBeforeBuild\(\)\) \{\s*return;\s*\}/);
  assert.match(renderer, /showActionFeedback\("当前文件有未保存修改，已停留在调试页面", "warn"\)/);
});

test("build center prioritizes the report and keeps details history and logs on demand", () => {
  assert.doesNotMatch(html, /class="build-summary-item"/);
  assert.doesNotMatch(html, /<aside class="build-history"/);
  assert.doesNotMatch(css, /build-summary-item/);
  assert.match(html, /id="buildDetailsPanel"/);
  assert.match(html, /id="buildHistoryPanel"/);
  assert.match(html, /id="buildToggleConsoleBtn"/);
  assert.match(css, /\.build-status-bar/);
  assert.match(css, /\.build-report-layout/);
  assert.match(css, /\.build-history-panel/);
  assert.match(renderer, /function normalizeAllureReportUrl/);
});

test("build downloads are available after a completed build", () => {
  assert.match(html, /id="buildDownloadReportBtn"/);
  assert.match(html, /id="buildDownloadLogsBtn"/);
  assert.match(html, />\s*下载报告\s*</);
  assert.match(html, />\s*下载日志\s*</);
  assert.match(renderer, /currentBuildStatus:\s*""/);
  assert.match(renderer, /downloadCurrentBuildReport/);
  assert.match(renderer, /downloadCurrentBuildLogs/);
  assert.match(renderer, /buildDownloadReportBtn\.addEventListener\("click", downloadCurrentBuildReport\)/);
  assert.match(renderer, /buildDownloadLogsBtn\.addEventListener\("click", downloadCurrentBuildLogs\)/);
  assert.match(renderer, /state\.currentBuildStatus = "running"/);
  assert.match(renderer, /state\.currentBuildStatus = event\.status \|\| "completed"/);
  assert.match(renderer, /const hasCompletedBuild = Boolean\(state\.snapshot && state\.currentBuildId && state\.currentBuildStatus && state\.currentBuildStatus !== "running"\)/);
  assert.match(renderer, /buildDownloadReportBtn\.disabled = !hasCompletedBuild \|\| isAnyTaskRunning \|\| !state\.currentBuildResultsDir/);
  assert.match(renderer, /buildDownloadLogsBtn\.disabled = !hasCompletedBuild \|\| isAnyTaskRunning/);
});

test("build can run without Allure but report actions explain the missing runtime", () => {
  assert.match(renderer, /function isAllureRuntimeAvailable/);
  assert.match(renderer, /allureRuntimeUnavailableMessage/);
  assert.match(renderer, /未检测到 Allure 3，构建会继续运行 pytest，但不会展示或下载 Allure 报告/);
  assert.match(renderer, /未生成 Allure 报告/);
  assert.match(renderer, /安装 Allure 3 后再下载报告/);
  assert.match(renderer, /buildOpenReportBtn\.disabled = !hasCompletedBuild && !state\.currentBuildReportUrl/);
  assert.match(renderer, /buildDownloadReportBtn\.disabled = !hasCompletedBuild \|\| isAnyTaskRunning \|\| !state\.currentBuildResultsDir/);
});

test("build report iframe reloads even when consecutive builds reuse the same Allure URL", () => {
  assert.match(renderer, /function buildReportFrameUrl\(url\)/);
  assert.match(renderer, /pytestDslBuild=/);
  assert.match(renderer, /encodeURIComponent\(state\.currentBuildId \|\| String\(Date\.now\(\)\)\)/);
  assert.match(renderer, /el\.buildReportFrame\.src = buildReportFrameUrl\(state\.currentBuildReportUrl\)/);
  assert.match(renderer, /el\.buildReportFrame\.src = "about:blank"/);
});

test("build report iframe retries the current report url after report-ready", () => {
  assert.match(renderer, /buildReportReloadTimer:\s*null/);
  assert.match(renderer, /buildReportReloadSeq:\s*0/);
  assert.match(renderer, /function scheduleBuildReportFrameReload\(\)/);
  assert.match(renderer, /clearBuildReportReloadTimer\(\)/);
  assert.match(renderer, /state\.buildReportReloadSeq \+= 1/);
  assert.match(renderer, /el\.buildReportFrame\.src = buildReportFrameUrl\(state\.currentBuildReportUrl, state\.buildReportReloadSeq\)/);
});

test("switching to build does not synchronously render expensive hidden surfaces", () => {
  assert.match(renderer, /function syncBuildReportFrameVisibility\(options = \{\}\)/);
  assert.match(renderer, /syncBuildReportFrameVisibility\(\{ defer: isBuildView \}\)/);
  assert.match(renderer, /function deferBuildReportFrameReveal\(\)/);
  assert.match(renderer, /requestAnimationFrame/);
  assert.match(renderer, /function shouldRenderConsoleBuffer\(\)/);
  assert.match(renderer, /if \(!shouldRenderConsoleBuffer\(\)\) \{\s*el\.consoleBody\.textContent = "";\s*return;\s*\}/);
  assert.match(renderer, /if \(scope === state\.console\.activeScope && shouldRenderConsoleBuffer\(\)\) \{\s*scheduleConsoleBufferRender\(\)/);
});

test("console rendering stays bounded and batched for large output", () => {
  assert.match(renderer, /MAX_CONSOLE_BUFFER_LINES\s*=/);
  assert.match(renderer, /MAX_CONSOLE_RENDER_LINES\s*=/);
  assert.match(renderer, /function appendConsoleEntries\(/);
  assert.match(renderer, /function trimConsoleBuffer\(/);
  assert.match(renderer, /function visibleConsoleEntries\(/);
  assert.match(renderer, /slice\(-MAX_CONSOLE_RENDER_LINES\)/);
  assert.match(renderer, /function scheduleConsoleBufferRender\(/);
  assert.match(renderer, /document\.createDocumentFragment\(\)/);
  assert.match(renderer, /replaceChildren\(fragment\)/);
  assert.match(renderer, /el\.consoleBody\.scrollTop = el\.consoleBody\.scrollHeight/);
  assert.doesNotMatch(renderer, /currentConsoleBuffer\(\)\.lines\.forEach\(appendConsoleRow\)/);
  assert.doesNotMatch(renderer, /function appendConsoleRow[\s\S]*scrollTop = el\.consoleBody\.scrollHeight/);
});

test("process output appends console lines in one batch per event", () => {
  assert.match(renderer, /function appendConsoleEntries\(scope, entries\)/);
  assert.match(renderer, /appendConsoleEntries\(scope, entries\)/);
  assert.doesNotMatch(renderer, /\.forEach\(\(line\) => appendLog\(level, line, \{ scope \}\)\)/);
});

test("console expansion and scope switches defer rendering instead of rebuilding synchronously", () => {
  assert.match(renderer, /function requestConsoleBufferRender\(/);
  assert.match(renderer, /const wasRenderable = shouldRenderConsoleBuffer\(\)/);
  assert.match(renderer, /if \(!wasRenderable && shouldRenderConsoleBuffer\(\)\) \{\s*requestConsoleBufferRender\(\);\s*\}/);
  assert.match(renderer, /function setConsoleScope\(scope\)\s*\{[\s\S]*requestConsoleBufferRender\(\)/);
  assert.doesNotMatch(renderer, /function toggleConsoleExpanded\(\)\s*\{[\s\S]*renderConsoleBuffer\(\);/);
});

test("build case tree rendering is cached across view switches", () => {
  assert.match(renderer, /buildCaseTreeSignature:\s*null/);
  assert.match(renderer, /function invalidateBuildCaseTreeRender\(\)/);
  assert.match(renderer, /function ensureBuildCaseTreeRendered\(\)/);
  assert.match(renderer, /if \(isBuildView\) \{[\s\S]*ensureBuildCaseTreeRendered\(\)/);
  assert.match(renderer, /state\.buildCaseTreeSignature = signature/);
  assert.doesNotMatch(renderer, /if \(isBuildView\) \{\s*ensureBuildCaseTreeExpanded\(\);\s*renderBuildCaseTree\(\);/);
});

test("console stays collapsed by default and can be opened when needed", () => {
  assert.match(renderer, /activeScope:\s*"debug"/);
  assert.match(renderer, /function createConsoleView\(\)\s*\{[\s\S]*wrap: true,[\s\S]*open: false,[\s\S]*expanded: false/);
  assert.match(renderer, /debug:\s*createConsoleView\(\)/);
  assert.match(renderer, /build:\s*createConsoleView\(\)/);
  assert.match(renderer, /function toggleConsoleOpen\(\)/);
  assert.match(renderer, /function openConsolePanel\(scope = state\.console\.activeScope\)/);
  assert.match(renderer, /el\.buildToggleConsoleBtn\.addEventListener\("click", toggleConsoleOpen\)/);
  assert.match(renderer, /el\.consoleToggleBtn\.addEventListener\("click", toggleConsoleOpen\)/);
  assert.match(renderer, /el\.consoleStatusToggleBtn\.addEventListener\("click", toggleConsoleOpen\)/);
  assert.match(renderer, /el\.mainStage\.classList\.toggle\("is-console-open", consoleView\.open\)/);
  assert.match(css, /\.main-stage\.is-console-open/);
  assert.match(css, /\.bottom-console\.is-collapsed/);
});

test("console header has an obvious toggle and keeps utility actions secondary", () => {
  assert.match(html, /id="consoleToggleBtn"/);
  assert.match(html, /id="consoleStatusToggleBtn"/);
  assert.match(html, /id="consoleActions"/);
  assert.match(html, /打开控制台/);
  assert.match(css, /\.console-toggle-btn/);
  assert.match(css, /\.console-status-btn/);
  assert.match(css, /\.console-actions/);
  assert.match(css, /\.bottom-console\.is-collapsed\s+\.console-actions\s*\{[\s\S]*display:\s*none/);
  assert.match(renderer, /consoleToggleBtn\.textContent = consoleView\.open \? "收起控制台" : "打开控制台"/);
  assert.match(renderer, /consoleStatusToggleBtn\.textContent = consoleView\.open \? "收起控制台" : "打开控制台"/);
  assert.doesNotMatch(renderer, /expandConsoleBtn\.textContent = !consoleView\.open[\s\S]*"打开日志"/);
});

test("collapsed console gives the editor the full main-stage height", () => {
  assert.match(css, /\.main-stage\s*\{[\s\S]*grid-template-rows:\s*minmax\(0,\s*1fr\) 0 0/);
  assert.match(css, /\.bottom-console\.is-collapsed\s*\{[\s\S]*visibility:\s*hidden/);
  assert.match(css, /\.bottom-console\.is-collapsed\s*\{[\s\S]*overflow:\s*hidden/);
});

test("renderer removes fake window dots and exposes project tree controls", () => {
  assert.doesNotMatch(html, /class="window-dots"/);
  assert.match(html, /id="openProjectBtn"/);
  assert.match(html, /id="treeRefreshBtn"/);
  assert.doesNotMatch(html, /id="createFileBtn"/);
  assert.doesNotMatch(html, /id="createFolderBtn"/);
  assert.doesNotMatch(html, /id="expandAllBtn"/);
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

test("project tree defaults to only the root level expanded to bound flatten cost", () => {
  // The expand-all affordance is removed: large projects should not pay the
  // full flatten + checkbox-sync cost on every interaction.
  assert.doesNotMatch(html, /id="expandAllBtn"/);
  assert.doesNotMatch(renderer, /expandAllBtn\.addEventListener/);
  // On project load the tree collapses everything below the root instead of
  // clearing the collapsed set (which used to expand all directories).
  assert.match(renderer, /function collapseTreeDirsBelowRoot\(\)/);
  assert.match(
    renderer,
    /state\.selectedTreeKind = "directory";\s*\n\s*collapseTreeDirsBelowRoot\(\);/,
  );
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

test("temporary overlay controls close predictably without collapsing persistent search", () => {
  assert.match(renderer, /function closeSuitePicker\(\)/);
  assert.match(renderer, /function closeConfigPicker\(\)/);
  assert.match(renderer, /function closeTopPickers\(\)/);
  assert.match(renderer, /function closeTransientPanelsForOutsideClick\(event\)/);
  assert.match(renderer, /closeTopPickers\(\);[\s\S]*closeKeywordPanel\(\);/);
  assert.match(renderer, /el\.suiteTrigger\.addEventListener\("click"[\s\S]*closeConfigPicker\(\)/);
  assert.match(renderer, /el\.configTrigger\.addEventListener\("click"[\s\S]*closeSuitePicker\(\)/);
  assert.match(renderer, /event\.key === "Escape"[\s\S]*closeTopPickers\(\)/);
  assert.match(renderer, /event\.key === "Escape"[\s\S]*closeKeywordPanel\(\)/);
  assert.doesNotMatch(renderer, /fileFilter[\s\S]{0,160}closeKeywordPanel/);
  assert.doesNotMatch(renderer, /fileFilter[\s\S]{0,160}closeTopPickers/);
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

test("large tree and keyword lists use delegated event handlers", () => {
  assert.match(renderer, /fileTree\.addEventListener\("click", handleFileTreeClick\)/);
  assert.match(renderer, /suiteList\.addEventListener\("change", handleSuiteTreeChange\)/);
  assert.match(renderer, /suiteList\.addEventListener\("click", handleSuiteTreeClick\)/);
  assert.match(renderer, /buildCaseTree\.addEventListener\("change", handleSuiteTreeChange\)/);
  assert.match(renderer, /buildCaseTree\.addEventListener\("click", handleSuiteTreeClick\)/);
  assert.match(renderer, /keywordList\.addEventListener\("click", handleKeywordListClick\)/);
  assert.doesNotMatch(renderer, /fileTree\.querySelectorAll\("\[data-tree-action\]"\)[\s\S]*addEventListener\("click", handleTreeAction\)/);
  assert.doesNotMatch(renderer, /container\.querySelectorAll\("\[data-suite-checkbox\]"\)[\s\S]*addEventListener\("change", handleSuiteSelectionChange\)/);
  assert.doesNotMatch(renderer, /keywordList\.querySelectorAll\("\.keyword-row\[data-index\]"\)[\s\S]*addEventListener\("click"/);
});

test("tree filter input batches expensive tree renders", () => {
  assert.match(renderer, /function scheduleFileTreeRender\(\)/);
  assert.match(renderer, /function scheduleBuildCaseTreeRender\(\)/);
  assert.match(renderer, /state\.buildCaseFilter = value;\s*scheduleBuildCaseTreeRender\(\);/);
  assert.match(renderer, /state\.filter = value;\s*scheduleFileTreeRender\(\);/);
  assert.match(renderer, /requestAnimationFrame/);
  assert.doesNotMatch(renderer, /state\.buildCaseFilter = value;\s*invalidateBuildCaseTreeRender\(\);\s*ensureBuildCaseTreeRendered\(\);/);
  assert.doesNotMatch(renderer, /state\.filter = value;\s*renderFileTree\(\);/);
});

test("debug and build left trees render a bounded viewport for large projects", () => {
  assert.match(renderer, /TREE_ROW_HEIGHT\s*=/);
  assert.match(renderer, /TREE_RENDER_OVERSCAN\s*=/);
  assert.match(renderer, /function virtualTreeWindow\(container, totalRows\)/);
  assert.match(renderer, /function renderVirtualTreeRows\(/);
  assert.match(renderer, /function flattenVisibleProjectTreeRows\(/);
  assert.match(renderer, /function flattenVisibleSuiteTreeRows\(/);
  assert.match(renderer, /const rows = flattenVisibleProjectTreeRows/);
  assert.match(renderer, /const rows = flattenVisibleSuiteTreeRows/);
  assert.match(renderer, /rows\.slice\(window\.start, window\.end\)/);
  assert.match(css, /\.tree-virtual-spacer/);
  assert.doesNotMatch(renderer, /el\.fileTree\.innerHTML = children\s*\.map\(\(node\) => renderProjectTreeNode\(node, 0\)\)/);
  assert.doesNotMatch(renderer, /el\.buildCaseTree\.innerHTML = tree\s*\? renderSuiteTreeNode\(tree, 0, "build"\)/);
});

test("switching to build does not expand every suite node before rendering", () => {
  assert.match(renderer, /function ensureBuildCaseTreeRootExpanded\(\)/);
  assert.match(renderer, /ensureBuildCaseTreeRootExpanded\(\)/);
  assert.doesNotMatch(renderer, /if \(isBuildView\) \{[\s\S]{0,120}ensureBuildCaseTreeExpanded\(\)/);
});

test("suite checkbox syncing is scoped to the active tree", () => {
  assert.match(renderer, /function syncSuiteTreeCheckboxStates\(scope = null\)/);
  assert.match(renderer, /suiteTreeContainers\(scope\)/);
  assert.match(renderer, /syncSuiteTreeCheckboxStates\("debug"\)/);
  assert.match(renderer, /syncSuiteTreeCheckboxStates\("build"\)/);
  assert.match(renderer, /syncSuiteTreeCheckboxStates\(scope\)/);
  assert.doesNotMatch(renderer, /function syncSuiteTreeCheckboxStates\(\)\s*\{[\s\S]*suiteTreeContainers\(\)\.forEach/);
});

test("editor chrome is compact so code keeps vertical space", () => {
  assert.match(html, /class="param-head"[\s\S]*class="sub-tabs"/);
  assert.match(html, /class="head-actions"[\s\S]*class="inline-actions"/);
  assert.match(css, /\.workspace-panel\s*\{[\s\S]*grid-template-rows:\s*34px minmax\(0,\s*1fr\)/);
  assert.match(css, /\.main-stage\s*\{[\s\S]*grid-template-rows:\s*minmax\(260px,\s*1fr\) 6px var\(--console-height\)/);
  assert.match(css, /\.editor-stack\s*\{[\s\S]*grid-template-rows:\s*auto auto auto minmax\(0,\s*1fr\)/);
  assert.match(css, /\.workarea\s*\{[\s\S]*height:\s*100%/);
  assert.match(css, /\.editor-stack\s*\{[\s\S]*height:\s*100%/);
  assert.match(css, /\.editor-stack\s*\{[\s\S]*overflow:\s*hidden/);
  assert.match(css, /\.code-editor\s*\{[\s\S]*grid-row:\s*4/);
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

test("layout resizing stays responsive over the Allure report iframe", () => {
  assert.match(renderer, /setPointerCapture\(event\.pointerId\)/);
  assert.match(renderer, /releasePointerCapture\(event\.pointerId\)/);
  assert.match(renderer, /requestAnimationFrame/);
  assert.match(renderer, /setLayoutSize\(kind, pendingSize, \{ persist: false \}\)/);
  assert.match(renderer, /document\.addEventListener\("pointercancel", stopResize, \{ once: true \}\)/);
  assert.match(css, /body\.is-resizing-layout \.report-frame,\s*body\.is-resizing-console \.report-frame\s*\{[\s\S]*pointer-events:\s*none/);
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
  assert.match(renderer, /commandBtn\.disabled = !showKeywordTools/);
  assert.doesNotMatch(html, /id="editorToolGroup"/);
});

test("save and syntax check report visible status outside the hidden console", () => {
  assert.match(html, /id="actionStatus"/);
  assert.match(renderer, /function showActionFeedback\(message, level = "info"\)/);
  assert.match(renderer, /showActionFeedback\(`已保存 \$\{result\.relativePath\}`,\s*"pass"\)/);
  assert.match(renderer, /showActionFeedback\("语法检查已提交", "info"\)/);
  assert.match(renderer, /showActionFeedback\("语法检查通过", "pass"\)/);
  assert.match(renderer, /showActionFeedback\("语法检查失败", "error"\)/);
  assert.match(css, /\.action-status/);
  assert.match(css, /\.action-status\.is-pass/);
  assert.match(css, /\.action-status\.is-error/);
});

test("editor supports keyboard save with visible shortcut affordance", () => {
  assert.match(
    html,
    /id="saveBtn"[\s\S]*title="保存当前文件 \(Ctrl\/Cmd\+S\)"[\s\S]*aria-keyshortcuts="Control\+S Meta\+S"/,
  );
  assert.match(
    renderer,
    /document\.addEventListener\("keydown", handleEditorSaveShortcut, true\)/,
  );
  assert.match(renderer, /function isSaveShortcut\(event\)/);
  assert.match(renderer, /event\.key\.toLowerCase\(\) === "s"/);
  assert.match(renderer, /\(event\.ctrlKey \|\| event\.metaKey\)/);
  assert.match(renderer, /!event\.altKey && !event\.shiftKey/);
  assert.match(
    renderer,
    /async function handleEditorSaveShortcut\(event\)[\s\S]*if \(!isSaveShortcut\(event\)\) \{[\s\S]*return;[\s\S]*event\.preventDefault\(\);[\s\S]*await saveCurrentFile\(\{ source: "shortcut" \}\)/,
  );
  assert.match(renderer, /async function saveCurrentFile\(options = \{\}\)/);
  assert.match(renderer, /if \(options\.source === "shortcut" && !state\.dirty\)/);
});

test("console output can be cleared manually and resets before each execution", () => {
  assert.match(html, /id="clearConsoleBtn"/);
  assert.match(html, /title="清空运行输出"/);
  assert.match(renderer, /consoleBuffers:\s*\{/);
  assert.match(renderer, /debug:\s*createConsoleBuffer\(\)/);
  assert.match(renderer, /build:\s*createConsoleBuffer\(\)/);
  assert.match(renderer, /clearConsoleBtn/);
  assert.match(renderer, /clearConsoleBtn\.addEventListener\("click",\s*\(\) =>\s*clearConsole\(\)/);
  assert.match(renderer, /function clearConsole\(scope = state\.console\.activeScope\)\s*\{[\s\S]*requestConsoleBufferRender\(\)/);
  assert.match(renderer, /buffer\.lines = \[\]/);
  assert.match(renderer, /buffer\.commandOutputChunks = \[\]/);
  assert.match(renderer, /function resetConsoleForExecution\(scope\)\s*\{[\s\S]*clearConsole\(scope\)/);
  assert.match(renderer, /resetConsoleForExecution\("debug"\);[\s\S]*appendLog\("info", `\$\{executionModeLabel\(mode\)\} started:/);
  assert.match(renderer, /resetConsoleForExecution\("debug"\);[\s\S]*appendLog\("info", `测试套运行 started:/);
  assert.match(renderer, /resetConsoleForExecution\("build"\);[\s\S]*appendLog\("info", `构建运行 started:/);
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
  assert.match(renderer, /currentConsoleBuffer\(\)\.commandOutputChunks\.join\(""\)/);
  assert.doesNotMatch(renderer, /copyConsoleOutput\(\)[\s\S]*state\.consoleLines\.join\("\\n"\)/);
  assert.match(renderer, /consoleView\.wrap/);
  assert.match(renderer, /consoleView\.expanded/);
  assert.match(css, /\.console-body\s*\{[\s\S]*user-select:\s*text/);
  assert.match(css, /\.console\.is-unwrapped\s+\.log-message/);
  assert.match(css, /\.main-stage\.is-console-expanded/);
});

test("console output and command preview are scoped between debug and build", () => {
  assert.match(renderer, /function consoleScopeForMode\(mode\)/);
  assert.match(renderer, /function setConsoleScope\(scope\)/);
  assert.match(renderer, /setConsoleScope\(nextView\)/);
  assert.match(renderer, /appendLog\("info", `构建运行 started:[\s\S]*\{ scope: "build" \}/);
  assert.match(renderer, /appendProcessOutput\(event\.type === "stderr" \? "error" : "info", event\.text, \{ scope: "build" \}\)/);
  assert.match(renderer, /appendProcessOutput\(event\.type === "stderr" \? "error" : "info", event\.text, \{ scope: "debug" \}\)/);
  assert.match(renderer, /commandPreviews:\s*\{/);
  assert.match(renderer, /function currentCommandPreview\(\)/);
  assert.match(renderer, /state\.commandPreviews\[scope\]/);
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

test("command bar preserves actual execution while console preview stays live", () => {
  assert.match(renderer, /commandPreviews:\s*\{/);
  assert.match(renderer, /function previewCommand\(/);
  assert.match(renderer, /function setExecutionCommand\(/);
  assert.match(renderer, /function releaseExecutionCommand\(/);
  assert.match(renderer, /function lockGeneratedCommand\(/);
  assert.match(renderer, /updateCommandPreview\(event\.command \|\| currentCommand\(\),\s*\{[\s\S]*taskId:\s*event\.taskId/);
  assert.match(renderer, /releaseExecutionCommand\(event\.taskId\)/);
  assert.match(renderer, /lockGeneratedCommand\(updated,\s*\{[\s\S]*taskId:\s*options\.taskId/);
  assert.match(renderer, /preview\.persistent = false/);
  assert.match(renderer, /updateCommandPreview\(currentCommand\(\),\s*\{[\s\S]*context:\s*"preview"/);
});

test("editor keyword tools stay available outside active debug sessions", () => {
  assert.match(html, /class="head-actions"[\s\S]*id="keywordBtn"[\s\S]*id="commandBtn"/);
  assert.doesNotMatch(renderer, /keywordBtn\.disabled = !executable/);
  assert.match(renderer, /const showKeywordTools = hasFile && isExecutableFile\(state\.currentFile\)/);
  assert.match(renderer, /keywordBtn\.hidden = !showKeywordTools/);
  assert.match(renderer, /commandBtn\.hidden = !showKeywordTools/);
  assert.match(renderer, /keywordBtn\.disabled = !hasFile \|\| readonlySource \|\| !isExecutableFile\(state\.currentFile\)/);
  assert.doesNotMatch(renderer, /!state\.currentFile \|\| !isExecutableFile\(state\.currentFile\)[\s\S]*当前文件不支持关键字插入/);
  assert.match(renderer, /renderActiveFile\(\)[\s\S]*updateFileActionState\(\)/);
  assert.match(css, /\.param-head\s*\{[\s\S]*grid-template-columns:/);
  assert.match(css, /\.inline-actions\s*\{[\s\S]*overflow:\s*visible/);
});

test("renderer hides keyword tools for YAML, Python, and Markdown files", () => {
  assert.match(renderer, /function detectLanguage/);
  assert.match(renderer, /name\.endsWith\("\.yaml"\) \|\| name\.endsWith\("\.yml"\)/);
  assert.match(renderer, /name\.endsWith\("\.py"\)/);
  assert.match(renderer, /name\.endsWith\("\.md"\) \|\| name\.endsWith\("\.markdown"\)/);
  assert.match(renderer, /const showKeywordTools = hasFile && isExecutableFile\(state\.currentFile\)/);
  assert.match(renderer, /keywordBtn\.hidden = !showKeywordTools/);
  assert.match(renderer, /commandBtn\.hidden = !showKeywordTools/);
  assert.match(renderer, /language === "dsl" \|\| language === "resource"/);
  assert.match(css, /(?:^|\n)\[hidden\]\s*\{[\s\S]*display:\s*none\s*!important/);
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

test("workspace shell uses the Pytest DSL Studio product name", () => {
  assert.match(html, /<title>Pytest DSL Studio<\/title>/);
  assert.match(html, /<strong id="projectName"[\s\S]*>Pytest DSL Studio<\/strong\s*>/);
  assert.match(main, /title: "Pytest DSL Studio"/);
  assert.match(renderer, /el\.projectName\.textContent = "Pytest DSL Studio"/);
  assert.doesNotMatch(html, /pytest-dsl Local Workbench/);
  assert.doesNotMatch(main, /pytest-dsl Local Workbench/);
  assert.doesNotMatch(renderer, /pytest-dsl Local Workbench/);
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

test("editor offers DSL and resource completions from keywords metadata and config variables", () => {
  assert.match(editorBridge, /snippetCompletion/);
  assert.match(editorBridge, /snippet\(/);
  assert.match(editorBridge, /function dslCompletionSource/);
  assert.match(editorBridge, /const nextChar = line\.text\.slice\(context\.pos - line\.from, context\.pos - line\.from \+ 1\)/);
  assert.match(editorBridge, /function keywordSnippetTemplate/);
  assert.match(editorBridge, /function keywordCompletionApply/);
  assert.match(editorBridge, /const replaceTo = options\.replaceNextBracket && view\.state\.doc\.sliceString\(to, to \+ 1\) === "\]" \? to \+ 1 : to/);
  assert.match(editorBridge, /function metadataCompletions/);
  assert.match(editorBridge, /function parameterCompletionMatch/);
  assert.match(editorBridge, /function parameterCompletions/);
  assert.match(editorBridge, /function keywordParametersForName/);
  assert.match(editorBridge, /usedParameterNames/);
  assert.match(editorBridge, /function variableCompletions/);
  assert.match(editorBridge, /setCompletionContext/);
  assert.match(editorBridge, /isDslLikeLanguage/);
  assert.match(editorBridge, /autocompletion\(\{\s*override:\s*\[dslCompletionSource\]/);
  assert.match(editorBridge, /replaceNextBracket: keywordMatch\.inBracket && nextChar === "\]"/);
  assert.doesNotMatch(editorBridge, /line\.from \+ keywordMatch\.to \+ \(keywordMatch\.inBracket && nextChar === "\]" \? 1 : 0\),\s*\n\s*completionContext\.keywords/);

  assert.match(renderer, /completionKeywords/);
  assert.match(renderer, /syncEditorCompletionContext/);
  assert.match(renderer, /loadEditorCompletionKeywords/);
  assert.match(renderer, /flattenConfigVariablePaths\(selectedMergedConfig\(\)\)/);
  assert.match(renderer, /CM6\.setCompletionContext/);
  assert.match(renderer, /language === "dsl" \|\| language === "resource"/);
  assert.match(renderer, /api\.listKeywords\(\{\s*projectRoot: state\.snapshot\.project\.rootPath,[\s\S]*limit: 500/);
  assert.match(renderer, /syncEditorCompletionContext\(\);[\s\S]*renderActiveFile\(\);/);
});

test("command bar separates live preview from generated command copying", () => {
  assert.match(html, /id="commandBar"/);
  assert.match(html, /id="generatedCommandStatus"/);
  assert.match(html, /id="generatedCommandText"/);
  assert.match(html, /id="copyCommandBtn"/);
  assert.match(html, /id="regenerateCommandBtn"/);
  assert.match(html, /id="commandBtn"[\s\S]*生成并锁定/);
  assert.match(renderer, /generateCurrentCommand/);
  assert.match(renderer, /copyGeneratedCommand/);
  assert.match(renderer, /lockGeneratedCommand/);
  assert.match(renderer, /renderCommandBar/);
  assert.match(renderer, /commandBar:\s*createCommandBar\(\)/);
  assert.match(renderer, /generatedCommandText\.textContent = state\.commandBar\.command/);
  assert.match(renderer, /generatedCommandStatus\.textContent = state\.commandBar\.locked/);
  assert.match(renderer, /api\.copyText/);
  assert.match(renderer, /命令已锁定/);
  assert.match(renderer, /命令已复制/);
  const generateStart = renderer.indexOf("async function generateCurrentCommand()");
  const copyStart = renderer.indexOf("async function copyGeneratedCommand()");
  assert.ok(generateStart >= 0, "missing generateCurrentCommand function");
  assert.ok(copyStart > generateStart, "copyGeneratedCommand should follow generateCurrentCommand");
  assert.doesNotMatch(renderer.slice(generateStart, copyStart), /api\.copyText/);
  assert.match(css, /\.command-bar/);
  assert.match(css, /\.command-bar\s*\{[\s\S]*min-height:\s*34px/);
  assert.match(css, /\.generated-command-text/);
  assert.match(css, /\.generated-command-text\s*\{[\s\S]*height:\s*24px/);
  assert.match(css, /\.generated-command-text\s*\{[\s\S]*overflow-x:\s*auto/);
  assert.match(css, /\.generated-command-text\s*\{[\s\S]*overflow-y:\s*hidden/);
  assert.match(css, /\.generated-command-text\s*\{[\s\S]*overscroll-behavior:\s*contain/);
  assert.match(css, /\.generated-command-actions/);
  assert.match(css, /\.command-tool-btn\s*\{[\s\S]*height:\s*28px/);
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

test("runtime config section exposes Python and Allure controls", () => {
  [
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
    assert.match(html, new RegExp(`id="${id}"`), `missing #${id}`);
  });

  assert.match(html, /运行环境/);
  assert.match(html, /Python/);
  assert.match(html, /Allure 3/);
  assert.match(html, /选择项目目录、\.venv\/venv 目录，或虚拟环境里的 Python 解释器/);
  assert.doesNotMatch(html, /id="runtimePythonSelectBtn"/);
  assert.doesNotMatch(html, />\s*文件\s*<\/button>/);

  assert.match(main, /runtime:status/);
  assert.match(main, /runtime:select/);
  assert.match(main, /runtime:reset/);
  assert.match(main, /getRuntimeStatus/);
  assert.match(main, /saveRuntimeExecutable/);
  assert.match(main, /resetRuntimeExecutable/);
  assert.match(main, /runtimeDialogProperties/);
  assert.match(main, /options\.selectionMode/);
  assert.match(main, /"python-directory"/);
  assert.doesNotMatch(main, /"python-file"/);
  assert.match(main, /"openDirectory"/);
  assert.match(main, /"showHiddenFiles"/);
  assert.match(main, /defaultPath:\s*options\.projectRoot/);

  assert.match(preload, /getRuntimeStatus/);
  assert.match(preload, /selectRuntimeExecutable/);
  assert.match(preload, /resetRuntimeExecutable/);

  assert.match(renderer, /function runtimeUnavailableText/);
  assert.match(renderer, /function runtimeFullText/);
  assert.match(renderer, /function runtimeCandidateStatusText/);
  assert.match(renderer, /probeStatus/);
  assert.doesNotMatch(renderer, /changeRuntime\("python", false, "python-file"\)/);
  assert.match(renderer, /changeRuntime\("python", false, "python-directory"\)/);
  assert.match(renderer, /showActionFeedback\(\s*runtimeChangeFeedback\(kind, reset, result\)/);
  assert.match(renderer, /function runtimeChangeFeedback/);
  assert.match(renderer, /function showRuntimeRequirementDialog/);
  assert.match(renderer, /window\.alert/);
  assert.match(renderer, /showActionFeedback\(`运行环境更新失败: \$\{error\.message\}`,\s*"error"\)/);
  assert.match(renderer, /命令:/);
  assert.match(renderer, /处理:/);
  const runtimePathRule = css.match(/\.runtime-path\s*\{[^}]*\}/)[0];
  assert.match(runtimePathRule, /white-space:\s*pre-wrap/);
  assert.match(runtimePathRule, /overflow-wrap:\s*anywhere/);
  assert.doesNotMatch(runtimePathRule, /text-overflow:\s*ellipsis/);
});

test("Python runtime availability gates debug suite and build actions", () => {
  assert.match(renderer, /runtimeStatus:\s*\{/);
  assert.match(renderer, /function isPythonRuntimeAvailable/);
  assert.match(renderer, /pythonRuntimeUnavailableMessage/);
  assert.match(renderer, /runAllBtn\.disabled = !state\.snapshot \|\| isRunning \|\| !pythonReady \|\| !hasDebugSuites/);
  assert.match(renderer, /syntaxBtn\.disabled = !executable \|\| isRunning \|\| !pythonReady/);
  assert.match(renderer, /runBtn\.disabled = !canRun \|\| isRunning \|\| !pythonReady/);
  assert.match(renderer, /debugStepsBtn\.disabled = !canDebug \|\| isRunning \|\| !pythonReady/);
  assert.match(renderer, /buildRunBtn\.disabled = !hasProject \|\| !hasSuites \|\| isAnyTaskRunning \|\| !pythonReady/);
  assert.match(renderer, /Python 运行环境不可用，无法调试或构建/);
});
