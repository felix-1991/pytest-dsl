# Electron GUI Runtime Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make packaged Pytest DSL Studio resolve project-specific Python and Allure 3 executables reliably, expose project-level runtime selection, and remove `spawn python ENOENT` from run and build flows.

**Architecture:** Persist optional runtime overrides in existing project metadata. Centralize Python and Allure discovery in focused services, then route execution, build, keyword, report, IPC, and UI status through those services.

**Tech Stack:** Electron 30, Node.js CommonJS, `node:test`, child-process `spawn`/`execFile`, HTML/CSS/vanilla JavaScript, electron-builder.

---

## File map

- `metadataStore.js`: normalize and persist `runtime.pythonExecutable` and `runtime.allureExecutable`.
- `pythonEnvService.js`: produce Python targets `{command, args, source, configured}` and reject missing explicit paths.
- New `allureEnvService.js`: discover candidates, run `--version`, and require Allure 3.
- New `runtimeConfigService.js`: save/reset paths and probe combined runtime status.
- Execution, build, keyword, and report services: consume shared runtime targets.
- Main/preload/HTML/renderer/CSS: expose project runtime selection and status.

### Task 1: Persist runtime overrides compatibly

**Files:**
- Modify: `electron-gui/src/services/metadataStore.js`
- Create: `electron-gui/test/metadataStore.test.js`

- [ ] **Step 1: Write failing metadata tests**

Create tests that write a legacy metadata file, read it, and assert:

```js
assert.deepEqual(metadata.runtime, {
  pythonExecutable: null,
  allureExecutable: null,
});
assert.equal(metadata.lastOpenedFile, "tests/case.dsl");
```

Then save and reset independently:

```js
updateRuntimeMetadata(root, { pythonExecutable: "/opt/project/python" });
updateRuntimeMetadata(root, { allureExecutable: "/opt/project/allure" });
assert.deepEqual(readMetadata(root).runtime, {
  pythonExecutable: "/opt/project/python",
  allureExecutable: "/opt/project/allure",
});
updateRuntimeMetadata(root, { pythonExecutable: null });
assert.equal(readMetadata(root).runtime.pythonExecutable, null);
assert.equal(readMetadata(root).runtime.allureExecutable, "/opt/project/allure");
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test --prefix electron-gui -- --test-reporter=spec test/metadataStore.test.js
```

Expected: FAIL because `runtime` and `updateRuntimeMetadata` do not exist.

- [ ] **Step 3: Implement normalized metadata**

Add:

```js
function defaultRuntimeMetadata() {
  return { pythonExecutable: null, allureExecutable: null };
}

function normalizeRuntimeMetadata(value) {
  const runtime = value && typeof value === "object" ? value : {};
  const normalize = (item) => {
    const text = typeof item === "string" ? item.trim() : "";
    return text || null;
  };
  return {
    pythonExecutable: normalize(runtime.pythonExecutable),
    allureExecutable: normalize(runtime.allureExecutable),
  };
}

function updateRuntimeMetadata(projectRoot, updates = {}) {
  const current = readMetadata(projectRoot);
  return writeMetadata(projectRoot, {
    ...current,
    runtime: { ...current.runtime, ...updates },
  });
}
```

Add `runtime: defaultRuntimeMetadata()` to `defaultMetadata()`, add `runtime: normalizeRuntimeMetadata(value && value.runtime)` to `normalizeMetadata()`, and export `updateRuntimeMetadata`.

- [ ] **Step 4: Verify GREEN**

```bash
npm test --prefix electron-gui -- --test-reporter=spec test/metadataStore.test.js test/projectService.test.js
```

Expected: both test files PASS and legacy fields remain unchanged.

- [ ] **Step 5: Commit**

```bash
git add -f electron-gui/src/services/metadataStore.js electron-gui/test/metadataStore.test.js
git commit -m "feat(gui): persist project runtime overrides"
```

### Task 2: Centralize Python resolution

**Files:**
- Modify: `electron-gui/src/services/pythonEnvService.js`
- Modify: `electron-gui/test/pythonEnvService.test.js`

- [ ] **Step 1: Add failing precedence tests**

Cover these exact contracts:

```js
updateRuntimeMetadata(root, { pythonExecutable: configured });
assert.deepEqual(resolvePythonTargets(root, {
  PYTEST_DSL_PYTHON: "/env/python",
  PATH: "",
}), [{
  command: configured,
  args: [],
  source: "project-config",
  configured: true,
}]);
```

```js
assert.throws(
  () => resolvePythonTarget(root, { PATH: process.env.PATH || "" }),
  /Configured Python executable does not exist/,
);
```

Also assert project `.venv` works with `PATH: ""`, and POSIX prefers `python3` over `python`.

- [ ] **Step 2: Verify RED**

```bash
npm test --prefix electron-gui -- --test-reporter=spec test/pythonEnvService.test.js
```

Expected: FAIL because target APIs and metadata precedence are absent.

- [ ] **Step 3: Implement target-based resolution**

Public contracts:

```js
function resolvePythonTarget(projectRoot, env = process.env, options = {}) {
  const targets = resolvePythonTargets(projectRoot, env, options);
  const configured = targets.find((target) => target.configured);
  if (configured && !isExecutableAvailable(configured.command, env, options.platform)) {
    throw new Error(`Configured Python executable does not exist: ${configured.command}`);
  }
  const selected = targets.find((target) => (
    isExecutableAvailable(target.command, env, options.platform)
  ));
  if (selected) return selected;
  throw new Error(
    `No usable Python executable was found. Checked: ${targets.map((target) => target.command).join(", ")}. ` +
    "Choose a Python interpreter in Configuration > Runtime.",
  );
}
```

```js
function resolvePythonTargets(projectRoot, env = process.env, options = {}) {
  const configured = Object.prototype.hasOwnProperty.call(options, "pythonExecutable")
    ? String(options.pythonExecutable || "").trim() || null
    : readMetadata(projectRoot).runtime.pythonExecutable;
  if (configured) {
    return [{ command: configured, args: [], source: "project-config", configured: true }];
  }

  const targets = [];
  if (env.PYTEST_DSL_PYTHON) targets.push(target(env.PYTEST_DSL_PYTHON, "environment"));
  if (env.PYTHON) targets.push(target(env.PYTHON, "environment"));
  const venv = findProjectVenvPython(projectRoot, options.platform);
  if (venv) targets.push(target(venv, "project-venv"));
  if ((options.platform || process.platform) === "win32") {
    targets.push(target("python", "path"));
    targets.push({ command: "py", args: ["-3"], source: "path", configured: false });
  } else {
    targets.push(target("python3", "path"));
    targets.push(target("python", "path"));
  }
  return dedupeTargets(targets);
}
```

Implement `findProjectVenvPython()` for `.venv` then `venv`, `isExecutableAvailable()` for absolute paths and PATH/PATHEXT, and compatibility wrappers `resolvePythonCommand()`/`resolvePythonCommands()`. Export all four resolution functions plus `isExecutableAvailable()`.

- [ ] **Step 4: Verify GREEN**

```bash
npm test --prefix electron-gui -- --test-reporter=spec test/pythonEnvService.test.js
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -f electron-gui/src/services/pythonEnvService.js electron-gui/test/pythonEnvService.test.js
git commit -m "fix(gui): centralize Python runtime resolution"
```

### Task 3: Use the same Python in execution, build, and keyword services

**Files:**
- Modify: `electron-gui/src/services/executionService.js`
- Modify: `electron-gui/src/services/buildService.js`
- Modify: `electron-gui/src/services/keywordService.js`
- Modify: `electron-gui/src/services/keywordDefinitionService.js`
- Modify: `electron-gui/test/executionService.test.js`
- Modify: `electron-gui/test/buildService.test.js`
- Modify: `electron-gui/test/keywordService.test.js`
- Modify: `electron-gui/test/keywordDefinitionService.test.js`

- [ ] **Step 1: Write restricted-PATH execution and build regressions**

Create a fake project `.venv` Python that echoes arguments and exits 0. Run both services with `env: { PATH: "" }`. Execution must contain `project python -m pytest_dsl.cli`; build must disable Allure watch and contain `project python -m pytest`. Neither event stream may contain `ENOENT`.

POSIX fixture:

```js
"#!/bin/sh\necho \"project python $@\"\n"
```

Windows fixture:

```js
"@echo off\r\necho project python %*\r\n"
```

- [ ] **Step 2: Write configured-Python keyword regressions**

Save a fake executable in metadata. `keywordService` fixture prints:

```json
{"keywords":[{"name":"配置解释器关键字","category":"runtime","category_name":"Runtime","source":"configured-python","parameters":[],"documentation":"configured"}],"summary":{"total_count":1},"categories":{}}
```

`keywordDefinitionService` fixture prints:

```json
{"definitions":[],"diagnostics":[]}
```

Assert both public queries complete through the configured executable.

- [ ] **Step 3: Verify RED**

```bash
npm test --prefix electron-gui -- --test-reporter=spec \
  test/executionService.test.js test/buildService.test.js \
  test/keywordService.test.js test/keywordDefinitionService.test.js
```

Expected: restricted PATH reproduces `spawn python ENOENT`; keyword tests ignore metadata.

- [ ] **Step 4: Integrate Python targets into execution**

Import `resolvePythonTarget` and shared `isExecutableAvailable`; delete local copies. Replace fallback resolution with:

```js
function resolveSpawnTarget(plan, options = {}, env = process.env) {
  const explicit = explicitExecutionCommand(plan.mode, options, env);
  if (explicit && isExecutableAvailable(explicit, env)) {
    return { command: explicit, args: plan.args };
  }
  const python = resolvePythonTarget(plan.cwd, env, options);
  const moduleName = plan.mode === "suite"
    ? "pytest"
    : plan.mode === "run"
      ? "pytest_dsl.cli"
      : "pytest_dsl.workbench.runner";
  return {
    command: python.command,
    args: [...python.args, "-m", moduleName, ...plan.args],
  };
}

function explicitExecutionCommand(mode, options, env) {
  if (mode === "syntax" || mode === "debug") {
    return options.workbenchExecutable || env.PYTEST_DSL_WORKBENCH || null;
  }
  if (mode === "suite") {
    return options.pytestExecutable || env.PYTEST_DSL_PYTEST || null;
  }
  return options.pytestExecutable || env.PYTEST_DSL_CLI || null;
}
```

- [ ] **Step 5: Integrate Python into build and keywords**

Build resolution:

```js
function resolvePytestSpawnTarget(plan, options = {}, env = process.env) {
  const explicit = options.pytestExecutable || env.PYTEST_DSL_PYTEST || null;
  if (explicit && isExecutableAvailable(explicit, env)) {
    return { command: explicit, args: plan.args };
  }
  const python = resolvePythonTarget(plan.cwd, env, options);
  return {
    command: python.command,
    args: [...python.args, "-m", "pytest", ...plan.args],
  };
}
```

In both keyword loops, replace command strings with `resolvePythonTargets()` entries and invoke:

```js
execFile(
  targets[targetIndex].command,
  [...targets[targetIndex].args, "-c", queryScript, ...queryArguments],
  execOptions,
  callback,
);
```

Preserve ENOENT and development-PYTHONPATH retries. In both execution environments, prepend the repository to `PYTHONPATH` only when `path.join(packageRoot, "pytest_dsl")` exists; packaged code must not add Electron Resources.

- [ ] **Step 6: Verify GREEN**

Run Step 3 again. Expected: all tests PASS and restricted PATH contains no ENOENT.

- [ ] **Step 7: Commit**

```bash
git add -f electron-gui/src/services/{executionService,buildService,keywordService,keywordDefinitionService}.js
git add -f electron-gui/test/{executionService,buildService,keywordService,keywordDefinitionService}.test.js
git commit -m "fix(gui): use project Python across runtime services"
```

### Task 4: Centralize Allure 3 validation

**Files:**
- Create: `electron-gui/src/services/allureEnvService.js`
- Create: `electron-gui/test/allureEnvService.test.js`
- Modify: `electron-gui/src/services/buildService.js`
- Modify: `electron-gui/test/buildService.test.js`

- [ ] **Step 1: Write failing Allure tests**

Use executable fixtures that print versions and cover:

```js
assert.equal((await resolveAllureRuntime(root, { PATH: "" })).source, "project-config");
assert.equal((await resolveAllureRuntime(root, { PATH: "" })).version, "3.1.0");
```

```js
const unsupported = await resolveAllureRuntime(rootWithConfiguredV2, { PATH: process.env.PATH || "" });
assert.equal(unsupported.available, false);
assert.equal(unsupported.reason, "allure-version-unsupported");
```

```js
const missing = await resolveAllureRuntime(rootWithoutAllure, { PATH: "" });
assert.equal(missing.available, false);
assert.equal(missing.reason, "allure-not-found");
```

- [ ] **Step 2: Verify RED**

```bash
npm test --prefix electron-gui -- --test-reporter=spec test/allureEnvService.test.js
```

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement Allure candidate and version resolution**

Export `resolveAllureCandidates()` and async `resolveAllureRuntime()`. Candidate priority is project metadata, `PYTEST_DSL_ALLURE`, project `node_modules/.bin`, Studio development `node_modules/.bin`, then PATH `allure`. A configured candidate is exclusive.

Probe with:

```js
execFile(
  candidate.command,
  [...candidate.args, "--version"],
  { cwd: projectRoot, env, timeout: 3000, windowsHide: true },
  callback,
);
```

Core resolver loop:

```js
async function resolveAllureRuntime(projectRoot, env = process.env, options = {}) {
  const candidates = resolveAllureCandidates(projectRoot, env, options);
  const configured = candidates.find((candidate) => candidate.configured);
  if (configured && !isExecutableAvailable(configured.command, env)) {
    return unavailable(
      "allure-config-invalid",
      `Configured Allure executable does not exist: ${configured.command}`,
      configured,
    );
  }
  for (const candidate of candidates) {
    if (!isExecutableAvailable(candidate.command, env)) continue;
    const version = await detectAllureVersion(candidate, projectRoot, env);
    if (!version) {
      if (candidate.configured) {
        return unavailable("allure-version-unreadable", "Unable to read configured Allure version", candidate);
      }
      continue;
    }
    if (Number(version.split(".")[0]) < 3) {
      if (candidate.configured) {
        return unavailable(
          "allure-version-unsupported",
          `Pytest DSL Studio requires Allure 3; configured version is ${version}`,
          candidate,
          version,
        );
      }
      continue;
    }
    return available(candidate, version);
  }
  return unavailable(
    "allure-not-found",
    "Allure 3 was not found. Choose it in Configuration > Runtime.",
  );
}
```

Available result:

```js
{
  available: true,
  command: candidate.command,
  args: candidate.args,
  source: candidate.source,
  version,
  reason: null,
  message: `Allure ${version}`,
}
```

Unavailable reasons are exactly `allure-config-invalid`, `allure-version-unreadable`, `allure-version-unsupported`, and `allure-not-found`, each with an actionable `message`.

- [ ] **Step 4: Replace build-local Allure discovery**

Delete `allureCandidates()` and `detectAllureMajor()` from `buildService.js`. Both watch and export call `resolveAllureRuntime(plan.cwd, env, options)`. Watch emits `reason` and `message`; export throws `new Error(runtime.message)` when unavailable. Keep command overrides for deterministic tests.

- [ ] **Step 5: Add optional-degradation regression and verify GREEN**

Run pytest through an override with Allure enabled and `PATH: ""`. Assert build status is `passed` and `report-unavailable.reason` is `allure-not-found`.

```bash
npm test --prefix electron-gui -- --test-reporter=spec test/allureEnvService.test.js test/buildService.test.js
```

Expected: all tests PASS; missing Allure does not alter pytest status.

- [ ] **Step 6: Commit**

```bash
git add -f electron-gui/src/services/allureEnvService.js electron-gui/src/services/buildService.js
git add -f electron-gui/test/allureEnvService.test.js electron-gui/test/buildService.test.js
git commit -m "fix(gui): centralize Allure 3 resolution"
```

### Task 5: Add project runtime IPC and UI

**Files:**
- Create: `electron-gui/src/services/runtimeConfigService.js`
- Create: `electron-gui/test/runtimeConfigService.test.js`
- Modify: `electron-gui/main.js`, `electron-gui/preload.js`
- Modify: `electron-gui/src/index.html`, `renderer.js`, `styles.css`
- Modify: `electron-gui/test/uiShell.test.js`

- [ ] **Step 1: Write failing service tests**

Test this public API:

```js
getRuntimeStatus({ projectRoot, env })
saveRuntimeExecutable(projectRoot, "python" | "allure", executablePath)
resetRuntimeExecutable(projectRoot, "python" | "allure")
```

Assertions:

```js
assert.throws(
  () => saveRuntimeExecutable(root, "python", "relative/python"),
  /absolute path/,
);
assert.throws(
  () => saveRuntimeExecutable(root, "python", path.join(root, "missing")),
  /does not exist/,
);
```

Save an executable, assert status reports `source: "project-config"`, reset it, and assert metadata returns `null`. Add probe tests distinguishing `python-not-found`, `python-dependency-missing`, and available Python.

- [ ] **Step 2: Write failing UI-shell assertions**

Assert these IDs exist: `runtimeConfig`, `runtimePythonStatus`, `runtimePythonPath`, `runtimePythonSelectBtn`, `runtimePythonAutoBtn`, `runtimeAllureStatus`, `runtimeAllurePath`, `runtimeAllureSelectBtn`, `runtimeAllureAutoBtn`.

Assert main/preload/renderer contain `runtime:status`, `runtime:select`, `runtime:reset`, `getRuntimeStatus`, `selectRuntimeExecutable`, `resetRuntimeExecutable`, `refreshRuntimeStatus`, and `renderRuntimeStatus`.

- [ ] **Step 3: Verify RED**

```bash
npm test --prefix electron-gui -- --test-reporter=spec test/runtimeConfigService.test.js test/uiShell.test.js
```

Expected: FAIL because service, IPC, and controls are absent.

- [ ] **Step 4: Implement runtime configuration service**

Validate project root, runtime kind, absolute path, and file existence synchronously. Persist through `updateRuntimeMetadata()`. Probe Python with:

```js
const PYTHON_PROBE_SCRIPT = "import pytest, pytest_dsl, sys; print(sys.executable)";

execFile(
  target.command,
  [...target.args, "-c", PYTHON_PROBE_SCRIPT],
  { cwd: projectRoot, env, timeout: 5000, windowsHide: true },
  callback,
);
```

Return Python status with `available`, `command`, `source`, `reason`, and `message`. Use reasons `python-not-found`, `python-dependency-missing`, and `python-probe-failed`. `getRuntimeStatus()` combines that probe, `resolveAllureRuntime()`, and persisted config:

```js
return {
  projectRoot,
  config: readMetadata(projectRoot).runtime,
  python,
  allure,
};
```

Persistence functions:

```js
function saveRuntimeExecutable(projectRoot, kind, executablePath) {
  const root = assertProjectRoot(projectRoot);
  const field = runtimeField(kind);
  const normalized = path.normalize(String(executablePath || "").trim());
  if (!path.isAbsolute(normalized)) {
    throw new Error("Runtime executable must use an absolute path");
  }
  if (!fs.existsSync(normalized) || !fs.statSync(normalized).isFile()) {
    throw new Error(`Runtime executable does not exist: ${normalized}`);
  }
  return updateRuntimeMetadata(root, { [field]: normalized });
}

function resetRuntimeExecutable(projectRoot, kind) {
  const root = assertProjectRoot(projectRoot);
  return updateRuntimeMetadata(root, { [runtimeField(kind)]: null });
}

function runtimeField(kind) {
  if (kind === "python") return "pythonExecutable";
  if (kind === "allure") return "allureExecutable";
  throw new Error(`Unsupported runtime kind: ${kind}`);
}
```

- [ ] **Step 5: Add narrow main/preload IPC**

Register:

```js
ipcMain.handle("runtime:status", (_event, options) => getRuntimeStatus(options));
ipcMain.handle("runtime:select", async (event, options) => {
  const result = await dialog.showOpenDialog(BrowserWindow.fromWebContents(event.sender), {
    title: options.kind === "allure" ? "选择 Allure 3 可执行文件" : "选择 Python 解释器",
    properties: ["openFile"],
  });
  if (result.canceled || result.filePaths.length === 0) return { canceled: true };
  saveRuntimeExecutable(options.projectRoot, options.kind, result.filePaths[0]);
  return getRuntimeStatus({ projectRoot: options.projectRoot });
});
ipcMain.handle("runtime:reset", (_event, options) => {
  resetRuntimeExecutable(options.projectRoot, options.kind);
  return getRuntimeStatus({ projectRoot: options.projectRoot });
});
```

Expose these preload methods:

```js
getRuntimeStatus: (options) => ipcRenderer.invoke("runtime:status", options),
selectRuntimeExecutable: (options) => ipcRenderer.invoke("runtime:select", options),
resetRuntimeExecutable: (options) => ipcRenderer.invoke("runtime:reset", options),
```

- [ ] **Step 6: Add compact runtime controls**

Insert into the existing config menu:

```html
<section class="runtime-config" id="runtimeConfig" aria-label="项目运行环境">
  <h3>运行环境</h3>
  <div class="runtime-row">
    <span class="status-dot unchecked" id="runtimePythonStatus"></span>
    <span class="runtime-name">Python</span>
    <code class="runtime-path" id="runtimePythonPath">自动发现</code>
    <button class="text-btn" id="runtimePythonSelectBtn" type="button">选择</button>
    <button class="text-btn" id="runtimePythonAutoBtn" type="button">自动</button>
  </div>
  <div class="runtime-row">
    <span class="status-dot unchecked" id="runtimeAllureStatus"></span>
    <span class="runtime-name">Allure 3</span>
    <code class="runtime-path" id="runtimeAllurePath">自动发现</code>
    <button class="text-btn" id="runtimeAllureSelectBtn" type="button">选择</button>
    <button class="text-btn" id="runtimeAllureAutoBtn" type="button">自动</button>
  </div>
</section>
```

Style `.runtime-row` with `grid-template-columns: 10px auto minmax(0, 1fr) auto auto`; ellipsize `.runtime-path`; reuse existing status dots and text buttons.

- [ ] **Step 7: Wire renderer behavior**

Cache all IDs, bind four buttons, and implement:

```js
async function refreshRuntimeStatus() {
  if (!state.snapshot) return;
  const projectRoot = state.snapshot.project.rootPath;
  try {
    const result = await api.getRuntimeStatus({ projectRoot });
    if (!state.snapshot || state.snapshot.project.rootPath !== projectRoot) return;
    renderRuntimeStatus(result);
  } catch (error) {
    appendLog("error", errorMessage(error));
  }
}

async function changeRuntime(kind, reset = false) {
  if (!state.snapshot) return;
  const projectRoot = state.snapshot.project.rootPath;
  const method = reset ? api.resetRuntimeExecutable : api.selectRuntimeExecutable;
  const result = await method({ projectRoot, kind });
  if (!result || result.canceled) return;
  renderRuntimeStatus(result);
  state.snapshot.metadata.runtime = result.config;
  renderMetadata(state.snapshot.metadata);
}
```

`renderRuntimeStatus()` maps available to `online`, missing optional Allure to `warning`, and broken configured paths to `offline`; each path’s `title` contains full diagnostics. Call `refreshRuntimeStatus()` from `applySnapshot()` with the root-race guard. Reset rows in `setEmptyProjectState()`.

- [ ] **Step 8: Verify GREEN**

Run Step 3 again. Expected: both test files PASS.

- [ ] **Step 9: Commit**

```bash
git add -f electron-gui/src/services/runtimeConfigService.js electron-gui/test/runtimeConfigService.test.js
git add -f electron-gui/main.js electron-gui/preload.js electron-gui/src/{index.html,renderer.js,styles.css}
git add -f electron-gui/test/uiShell.test.js
git commit -m "feat(gui): add project runtime controls"
```

### Task 6: Documentation and packaged verification

**Files:**
- Modify: `README.md`
- Modify: `examples/gui_validation/README.md`
- Modify: `electron-gui/test/packaging.test.js`

- [ ] **Step 1: Add failing documentation contracts**

Extend packaging tests:

```js
assert.match(readme, /项目.*\.venv/);
assert.match(readme, /运行环境.*Python/);
assert.match(readme, /Allure 3.*外部/);
assert.match(exampleReadme, /配置.*运行环境/);
assert.match(exampleReadme, /不会内置 Python 或 Allure/);
```

- [ ] **Step 2: Verify RED**

```bash
npm test --prefix electron-gui -- --test-reporter=spec test/packaging.test.js
```

Expected: FAIL because packaged-runtime prerequisites are undocumented.

- [ ] **Step 3: Add the documented boundary**

Add under Studio startup instructions in both READMEs:

```markdown
打包版 Studio 不会内置 Python、pytest-dsl 或 Allure。项目优先使用根目录 `.venv`/`venv` 中已安装 pytest-dsl 与测试依赖的解释器；也可以在顶部“配置 → 运行环境”中为当前项目选择 Python。实时报告和 HTML 报告导出需要外部 Allure 3，可在同一区域选择其可执行文件。
```

- [ ] **Step 4: Run complete automated verification**

```bash
npm test --prefix electron-gui
npm run check --prefix electron-gui
git diff --check
```

Expected: all tests and app-file checks PASS; diff check is clean.

- [ ] **Step 5: Rebuild macOS packages**

```bash
npm run package:mac --prefix electron-gui
```

Expected: x64/arm64 DMG and ZIP artifacts under `electron-gui/dist/`; exit 0.

- [ ] **Step 6: Verify the real packaged app under a desktop PATH**

Launch:

```bash
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  electron-gui/dist/mac-arm64/pytest-dsl-studio.app/Contents/MacOS/pytest-dsl-studio
```

Use `desktop-computer-automation` to open `/Users/chenshuanglin/code/python/pytest-dsl`, confirm `.venv/bin/python` is green, run a DSL smoke case with no ENOENT, select a controlled Allure 3 executable, verify build/report resolution, reset both controls, and close the app. Inspect the latest `.pytest-dsl-gui/builds/<buildId>/stderr.log` and `build.json` as durable evidence.

- [ ] **Step 7: Commit**

```bash
git add README.md examples/gui_validation/README.md
git add -f electron-gui/test/packaging.test.js
git commit -m "docs(gui): explain packaged runtime prerequisites"
```

### Task 7: Final audit

**Files:**
- Review: all files changed by Tasks 1-6

- [ ] **Step 1: Run original-symptom regressions**

```bash
npm test --prefix electron-gui -- --test-reporter=spec \
  test/pythonEnvService.test.js test/executionService.test.js \
  test/buildService.test.js test/allureEnvService.test.js \
  test/runtimeConfigService.test.js
```

Expected: all PASS, including restricted PATH cases.

- [ ] **Step 2: Run final full verification**

```bash
npm run check --prefix electron-gui
git status --short
git log -7 --oneline
```

Expected: checks PASS, no unintended build artifacts, and focused commits are visible.

- [ ] **Step 3: Review requirements line by line**

Confirm each point with an automated test or packaged evidence:

- no run/debug/suite/build path falls through to unchecked bare `python`;
- project Python is shared by execution and keyword lookup;
- invalid explicit paths do not silently fall back;
- Allure 2 is rejected and Allure 3 is shared by live/export flows;
- missing Allure does not fail pytest;
- both paths can be selected and reset in the UI;
- no Python, Java, pytest-dsl, or Allure runtime was bundled.
