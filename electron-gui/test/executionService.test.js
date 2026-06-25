const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { execFileSync } = require("node:child_process");

const {
  createExecutionPlan,
  hasRunningTask,
  sendExecutionCommand,
  startExecutionTask,
  stopExecutionTask,
} = require("../src/services/executionService");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-exec-"));
}

function writeFile(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}

function writeNodeCommand(root, name) {
  const target = path.join(root, process.platform === "win32" ? `${name}.exe` : name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(process.execPath, target);
  if (process.platform !== "win32") {
    fs.chmodSync(target, 0o755);
  }
  return target;
}

function writeExecutable(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
  fs.chmodSync(filePath, 0o755);
  return filePath;
}

function writePythonRuntimeModules(root) {
  writeFile(root, "pytest_dsl/__init__.py", "");
  writeFile(root, "pytest_dsl/cli.py", [
    "import sys",
    "print('-m pytest_dsl.cli ' + ' '.join(sys.argv[1:]), flush=True)",
    "",
  ].join("\n"));
  writeFile(root, "pytest_dsl/workbench/__init__.py", "");
  writeFile(root, "pytest_dsl/workbench/runner.py", [
    "import sys",
    "print('-m pytest_dsl.workbench.runner ' + ' '.join(sys.argv[1:]), flush=True)",
    "",
  ].join("\n"));
  writeFile(root, "pytest.py", [
    "import sys",
    "print('-m pytest ' + ' '.join(sys.argv[1:]), flush=True)",
    "",
  ].join("\n"));
}

function preparePythonRuntime(root) {
  const pythonExecutable = installedTestPython();
  writePythonRuntimeModules(root);
  return { pythonExecutable };
}

function loadPackagedExecutionService(root) {
  const sourceDir = path.resolve(__dirname, "..", "src", "services");
  const serviceDir = path.join(root, "Resources", "app.asar", "src", "services");
  fs.mkdirSync(serviceDir, { recursive: true });
  for (const name of [
    "executionService.js",
    "metadataStore.js",
    "pythonEnvService.js",
    "runtimePathService.js",
    "suiteService.js",
  ]) {
    fs.copyFileSync(path.join(sourceDir, name), path.join(serviceDir, name));
  }
  return require(path.join(serviceDir, "executionService.js"));
}

let cachedTestPython = null;

function installedTestPython() {
  if (cachedTestPython) {
    return cachedTestPython;
  }
  const candidates = [
    [process.env.PYTEST_DSL_TEST_PYTHON, []],
    [process.env.PYTHON, []],
    ["python", []],
    ["python3", []],
    ["py", ["-3"]],
  ];
  for (const [command, prefixArgs] of candidates) {
    if (!command) {
      continue;
    }
    try {
      cachedTestPython = execFileSync(
        command,
        [...prefixArgs, "-c", "import allure, sys; print(sys.executable)"],
        { encoding: "utf8" },
      ).trim();
      if (cachedTestPython) {
        return cachedTestPython;
      }
    } catch (_error) {
      // Try the next installed Python command.
    }
  }
  throw new Error("No test Python with pytest-dsl dependencies is available");
}

test("execution plans materialize selected lines and build syntax command", () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"disk\"\n");

  const plan = createExecutionPlan({
    taskId: "plan-syntax",
    projectRoot: root,
    relativePath: "tests/case.dsl",
    mode: "syntax",
    content: "[打印], 内容: \"editor\"\n",
    selection: {
      startLine: 2,
      endLine: 3,
      content: "[打印], 内容: \"selected\"\n[断言], 条件: \"1 == 1\"",
    },
    yamlVars: ["config/dev.yaml"],
  });

  assert.equal(plan.mode, "syntax");
  assert.equal(plan.source.kind, "selection");
  assert.equal(plan.source.startLine, 2);
  assert.equal(
    fs.readFileSync(plan.targetPath, "utf8"),
    "[打印], 内容: \"selected\"\n[断言], 条件: \"1 == 1\"\n",
  );
  assert.equal(plan.command, "pytest-dsl-workbench");
  assert.deepEqual(plan.args.slice(0, 2), ["syntax", plan.targetRelativePath]);
  assert.match(plan.displayCommand, /syntax tests\/case\.dsl:2-3/);
});

test("execution plans use public CLI executables instead of Python module paths", () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"disk\"\n");

  const syntaxPlan = createExecutionPlan({
    taskId: "public-syntax-plan",
    projectRoot: root,
    relativePath: "tests/case.dsl",
    mode: "syntax",
    content: "[打印], 内容: \"editor\"\n",
  });
  const debugPlan = createExecutionPlan({
    taskId: "public-debug-plan",
    projectRoot: root,
    relativePath: "tests/case.dsl",
    mode: "debug",
    content: "[打印], 内容: \"editor\"\n",
  });
  const runPlan = createExecutionPlan({
    taskId: "public-run-plan",
    projectRoot: root,
    relativePath: "tests/case.dsl",
    mode: "run",
    content: "[打印], 内容: \"editor\"\n",
  });

  assert.equal(syntaxPlan.command, "pytest-dsl-workbench");
  assert.deepEqual(syntaxPlan.args.slice(0, 2), ["syntax", syntaxPlan.targetRelativePath]);
  assert.equal(debugPlan.command, "pytest-dsl-workbench");
  assert.deepEqual(debugPlan.args.slice(0, 2), ["debug", debugPlan.targetRelativePath]);
  assert.equal(runPlan.command, "pytest-dsl");
  assert.deepEqual(runPlan.args.slice(0, 1), [runPlan.targetRelativePath]);
});

test("suite execution plans use directory pytest targets for selected suites", () => {
  const root = makeTempProject();
  writeFile(root, "tests/root_case.dsl", "[打印], 内容: \"root\"\n");
  writeFile(root, "tests/api/auth/login.dsl", "[打印], 内容: \"login\"\n");
  writeFile(root, "tests/api/auth/logout.dsl", "[打印], 内容: \"logout\"\n");
  writeFile(root, "tests/api/test_contract.py", "def test_contract():\n    pass\n");
  writeFile(root, "tests/ui/pages/dashboard.dsl", "[打印], 内容: \"dashboard\"\n");

  const plan = createExecutionPlan({
    taskId: "suite-plan",
    projectRoot: root,
    mode: "suite",
    selectedSuiteIds: ["api", "api/auth"],
    yamlVars: ["config/dev.yaml"],
  });

  assert.equal(plan.mode, "suite");
  assert.equal(plan.command, "pytest");
  assert.equal(plan.targetPath, null);
  assert.equal(plan.cleanupDir, null);
  assert.equal(plan.source.kind, "suite");
  assert.deepEqual(plan.args, [
    "tests/api",
    "--yaml-vars",
    "config/dev.yaml",
  ]);
  assert.match(plan.displayCommand, /^pytest tests\/api --yaml-vars config\/dev\.yaml$/);
  assert.equal(
    fs.existsSync(path.join(root, "tests/api/auth/.pytest-dsl-generated/test_dsl_cases.py")),
    false,
  );
});

test("suite execution plans support file level filtering via selectedFiles", () => {
  const root = makeTempProject();
  writeFile(root, "tests/root_case.dsl", "[打印], 内容: \"root\"\n");
  writeFile(root, "tests/api/auth/login.dsl", "[打印], 内容: \"login\"\n");
  writeFile(root, "tests/api/auth/logout.dsl", "[打印], 内容: \"logout\"\n");

  const plan = createExecutionPlan({
    taskId: "suite-file-plan",
    projectRoot: root,
    mode: "suite",
    selectedSuiteIds: ["api/auth"],
    selectedFiles: ["tests/api/auth/login.dsl"],
    yamlVars: ["config/dev.yaml"],
  });

  assert.equal(plan.mode, "suite");
  assert.equal(plan.command, "pytest");
  assert.equal(plan.source.kind, "suite");
  assert.deepEqual(plan.source.selectedFiles, ["tests/api/auth/login.dsl"]);
  assert.deepEqual(plan.args, [
    "tests/api/auth/login.dsl",
    "--yaml-vars",
    "config/dev.yaml",
  ]);
  assert.match(plan.displayCommand, /^pytest tests\/api\/auth\/login\.dsl --yaml-vars config\/dev\.yaml$/);
});

test("execution plans mirror source paths for temporary materialization", () => {
  const root = makeTempProject();
  writeFile(root, "tests/nested/case.dsl", "@import: \"helpers.resource\"\n[打印], 内容: \"ok\"\n");

  const plan = createExecutionPlan({
    taskId: "mirror-path-plan",
    projectRoot: root,
    relativePath: "tests/nested/case.dsl",
    mode: "run",
    content: "@import: \"helpers.resource\"\n[打印], 内容: \"editor\"\n",
  });

  assert.equal(
    plan.targetRelativePath,
    ".pytest-dsl-gui/runs/mirror-path-plan/tests/nested/case.dsl",
  );
  assert.equal(
    fs.readFileSync(plan.targetPath, "utf8"),
    "@import: \"helpers.resource\"\n[打印], 内容: \"editor\"\n",
  );
});

test("execution plans run selected resource content through temporary files", () => {
  const root = makeTempProject();
  writeFile(root, "resources/gui.resource", "function 准备 do\n  [打印], 内容: \"all\"\nend\n");

  const plan = createExecutionPlan({
    taskId: "resource-selection-plan",
    projectRoot: root,
    relativePath: "resources/gui.resource",
    mode: "run",
    content: "function 准备 do\n  [打印], 内容: \"all\"\nend\n",
    selection: {
      startLine: 2,
      endLine: 2,
      content: "[打印], 内容: \"selected\"",
    },
  });

  assert.equal(plan.source.kind, "selection");
  assert.equal(plan.source.label, "resources/gui.resource:2-2");
  assert.equal(
    plan.targetRelativePath,
    ".pytest-dsl-gui/runs/resource-selection-plan/resources/gui.resource",
  );
  assert.equal(
    fs.readFileSync(plan.targetPath, "utf8"),
    "[打印], 内容: \"selected\"\n",
  );
  assert.deepEqual(plan.args.slice(0, 1), [plan.targetRelativePath]);
});

test("execution tasks stream process output and completion status", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const events = [];

  const result = await startExecutionTask(
    {
      taskId: "stream-task",
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "run",
      content: "[打印], 内容: \"ok\"\n",
      commandOverride: {
        command: process.execPath,
        args: ["-e", "console.log('hello'); console.error('warning');"],
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  assert.equal(result.status, "passed");
  assert.equal(result.exitCode, 0);
  assert.equal(hasRunningTask("stream-task"), false);
  assert.equal(events[0].type, "started");
  assert.ok(events.some((event) => event.type === "stdout" && event.text.includes("hello")));
  assert.ok(events.some((event) => event.type === "stderr" && event.text.includes("warning")));
  assert.equal(events.at(-1).type, "completed");
});

test("duplicate sanitized task ids do not overwrite the active staged file", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"disk\"\n");
  const events = [];
  const taskId = "duplicate/id";
  const stagedPath = path.join(
    root,
    ".pytest-dsl-gui",
    "runs",
    "duplicate_id",
    "tests",
    "case.dsl",
  );
  const pending = startExecutionTask(
    {
      taskId,
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "run",
      content: "[打印], 内容: \"first\"\n",
      commandOverride: {
        command: process.execPath,
        args: ["-e", "console.log('ready'); setInterval(() => {}, 1000);"],
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  try {
    await waitFor(() => events.some((event) => (
      event.type === "stdout" && event.text.includes("ready")
    )));
    assert.equal(fs.readFileSync(stagedPath, "utf8"), "[打印], 内容: \"first\"\n");

    assert.throws(() => startExecutionTask({
      taskId,
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "run",
      content: "[打印], 内容: \"second\"\n",
      commandOverride: {
        command: process.execPath,
        args: ["-e", "process.exit(0)"],
      },
    }), /Execution task is already running: duplicate_id/);

    assert.equal(fs.readFileSync(stagedPath, "utf8"), "[打印], 内容: \"first\"\n");
  } finally {
    stopExecutionTask(taskId);
    await pending;
  }
});

test("execution flushes ordinary stdout tail without a trailing newline", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const events = [];

  const result = await startExecutionTask({
    taskId: "stdout-tail",
    projectRoot: root,
    relativePath: "tests/case.dsl",
    mode: "run",
    content: "[打印], 内容: \"ok\"\n",
    commandOverride: {
      command: process.execPath,
      args: ["-e", "process.stdout.write('tail-without-newline')"],
    },
  }, {
    onEvent(event) {
      events.push(event);
    },
  });

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "stdout" && event.text.includes("tail-without-newline")
  )));
  assert.equal(events.at(-1).type, "completed");
});

test("execution flushes structured debug event tail without a trailing newline", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const events = [];
  const payload = JSON.stringify({
    type: "debug_step",
    phase: "start",
    line: 1,
    nodeType: "KeywordCall",
    description: "tail debug event",
  });

  const result = await startExecutionTask({
    taskId: "structured-tail",
    projectRoot: root,
    relativePath: "tests/case.dsl",
    mode: "debug",
    content: "[打印], 内容: \"ok\"\n",
    commandOverride: {
      command: process.execPath,
      args: ["-e", `process.stdout.write('__PYTEST_DSL_GUI_EVENT__' + ${JSON.stringify(payload)})`],
    },
  }, {
    onEvent(event) {
      events.push(event);
    },
  });

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "debug-step" &&
    event.description === "tail debug event" &&
    event.line === 1
  )));
  assert.equal(events.at(-1).type, "completed");
});

test("execution child environment applies Windows key replacement semantics", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const externalPythonPath = path.join(root, "external-pythonpath");
  const events = [];

  const result = await startExecutionTask({
    taskId: "windows-env-merge",
    projectRoot: root,
    relativePath: "tests/case.dsl",
    mode: "run",
    content: "[打印], 内容: \"ok\"\n",
    platform: "win32",
    env: {
      Path: "stale-path",
      PATH: "restricted-path",
      PathExt: ".CMD",
      PATHEXT: ".EXE;.CMD",
      PythonPath: "stale-pythonpath",
      PYTHONPATH: externalPythonPath,
      PYTHONIOENCODING: "gbk",
      PYTHONUTF8: "0",
      PYTHONUNBUFFERED: "0",
    },
    commandOverride: {
      command: process.execPath,
      args: ["-e", [
        "const keys = Object.keys(process.env).filter(key =>",
        "  ['path', 'pathext', 'pythonpath'].includes(key.toLowerCase()));",
        "console.log(JSON.stringify({ keys, PATH: process.env.PATH,",
        "  PATHEXT: process.env.PATHEXT, PYTHONPATH: process.env.PYTHONPATH,",
        "  PYTHONIOENCODING: process.env.PYTHONIOENCODING,",
        "  PYTHONUTF8: process.env.PYTHONUTF8,",
        "  PYTHONUNBUFFERED: process.env.PYTHONUNBUFFERED }));",
      ].join(" ")],
    },
  }, {
    onEvent(event) {
      events.push(event);
    },
  });

  const output = events.find((event) => event.type === "stdout");
  const payload = JSON.parse(output.text);
  assert.equal(result.status, "passed");
  assert.equal(payload.PATH, "restricted-path");
  assert.equal(payload.PATHEXT, ".EXE;.CMD");
  assert.deepEqual(payload.keys.sort(), ["PATH", "PATHEXT", "PYTHONPATH"]);
  assert.equal(payload.PYTHONPATH.split(";").at(-1), externalPythonPath);
  assert.equal(payload.PYTHONIOENCODING, "utf-8");
  assert.equal(payload.PYTHONUTF8, "1");
  assert.equal(payload.PYTHONUNBUFFERED, "1");
});

test("normal run uses configured absolute Python when PATH is empty", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const runtimeOptions = preparePythonRuntime(root);
  const events = [];

  const result = await startExecutionTask(
    {
      taskId: "project-python-run",
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "run",
      content: "[打印], 内容: \"ok\"\n",
      ...runtimeOptions,
      env: {
        PATH: "",
        PYTHON: "",
        PYTEST_DSL_PYTHON: "",
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "stdout" && event.text.includes("-m pytest_dsl.cli")
  )));
  assert.equal(events.some((event) => String(event.text || "").includes("ENOENT")), false);
  assert.equal(hasRunningTask("project-python-run"), false);
});

test("default public CLI on PATH does not bypass resolved project Python", async () => {
  const root = makeTempProject();
  const binDir = fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-default-cli-"));
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const runtimeOptions = preparePythonRuntime(root);
  writeNodeCommand(binDir, "pytest-dsl");
  const events = [];

  const result = await startExecutionTask(
    {
      taskId: "default-public-cli",
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "run",
      content: "console.log('default public CLI')\n",
      ...runtimeOptions,
      env: {
        PATH: binDir,
        PATHEXT: ".EXE;.CMD",
        PYTHON: "",
        PYTEST_DSL_PYTHON: "",
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "stdout" && event.text.includes("-m pytest_dsl.cli")
  )));
  assert.equal(events.some((event) => (
    event.type === "stdout" && event.text.includes("default public CLI")
  )), false);
});

test("task environment public CLI overrides bypass Python only for their modes", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const runtimeOptions = preparePythonRuntime(root);
  const cases = [
    { mode: "syntax", envName: "PYTEST_DSL_WORKBENCH" },
    { mode: "debug", envName: "PYTEST_DSL_WORKBENCH" },
    { mode: "suite", envName: "PYTEST_DSL_PYTEST" },
    { mode: "run", envName: "PYTEST_DSL_CLI" },
  ];

  for (const item of cases) {
    const marker = `task env ${item.mode}`;
    if (item.mode === "syntax" || item.mode === "debug") {
      writeFile(root, item.mode, `console.log(${JSON.stringify(marker)})\n`);
    } else if (item.mode === "suite") {
      writeFile(root, "suite-cli.js", `console.log(${JSON.stringify(marker)})\n`);
    }
    const events = [];
    const options = {
      taskId: `task-env-${item.mode}`,
      projectRoot: root,
      mode: item.mode,
      ...runtimeOptions,
      env: {
        PATH: "",
        PYTHON: "",
        PYTEST_DSL_PYTHON: "",
        PYTEST_DSL_WORKBENCH: "",
        PYTEST_DSL_PYTEST: "",
        PYTEST_DSL_CLI: "",
        [item.envName]: process.execPath,
      },
    };
    if (item.mode === "suite") {
      options.selectedFiles = ["suite-cli.js"];
    } else {
      options.relativePath = "tests/case.dsl";
      options.content = item.mode === "run"
        ? `console.log(${JSON.stringify(marker)})\n`
        : "[打印], 内容: \"ok\"\n";
    }

    const result = await startExecutionTask(options, {
      onEvent(event) {
        events.push(event);
      },
    });

    assert.equal(result.status, "passed", item.mode);
    assert.ok(events.some((event) => (
      event.type === "stdout" && event.text.includes(marker)
    )), item.mode);
  }
});

test("Python fallback maps syntax, debug, and suite execution to their modules", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const runtimeOptions = preparePythonRuntime(root);

  const cases = [
    { mode: "syntax", module: "pytest_dsl.workbench.runner" },
    { mode: "debug", module: "pytest_dsl.workbench.runner" },
    { mode: "suite", module: "pytest" },
  ];
  for (const item of cases) {
    const events = [];
    const options = {
      taskId: `project-python-${item.mode}`,
      projectRoot: root,
      mode: item.mode,
      ...runtimeOptions,
      env: {
        PATH: "",
        PYTHON: "",
        PYTEST_DSL_PYTHON: "",
      },
    };
    if (item.mode !== "suite") {
      options.relativePath = "tests/case.dsl";
      options.content = "[打印], 内容: \"ok\"\n";
    }

    const result = await startExecutionTask(options, {
      onEvent(event) {
        events.push(event);
      },
    });

    assert.equal(result.status, "passed", item.mode);
    assert.ok(events.some((event) => (
      event.type === "stdout" && event.text.includes(`-m ${item.module}`)
    )), item.mode);
  }
});

test("Python resolution failures clean temporary execution files", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const taskId = "invalid-python-cleanup";

  await assert.rejects(
    async () => startExecutionTask({
      taskId,
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "run",
      content: "[打印], 内容: \"ok\"\n",
      pythonExecutable: path.join(root, "missing-python"),
      env: { PATH: "" },
    }),
    /Configured Python executable does not exist or is not executable/,
  );

  assert.equal(
    fs.existsSync(path.join(root, ".pytest-dsl-gui", "runs", taskId)),
    false,
  );
  assert.equal(hasRunningTask(taskId), false);
});

test("Python runtime preflight failures stop file and suite execution before spawning", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const python = writeExecutable(path.join(root, ".venv", "bin", "python"), [
    "#!/bin/sh",
    "echo \"ModuleNotFoundError: No module named 'pytest_dsl'\" >&2",
    "exit 1",
    "",
  ].join("\n"));

  for (const mode of ["run", "suite"]) {
    const taskId = `preflight-${mode}`;
    const options = {
      taskId,
      projectRoot: root,
      mode,
      pythonExecutable: python,
      env: { PATH: "" },
    };
    if (mode !== "suite") {
      options.relativePath = "tests/case.dsl";
      options.content = "[打印], 内容: \"ok\"\n";
    }

    await assert.rejects(
      async () => startExecutionTask(options),
      /Python 3\.9.*pip install pytest-dsl/,
    );
    assert.equal(hasRunningTask(taskId), false);
  }
});

test("packaged execution preserves external PYTHONPATH without adding Resources", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const packaged = loadPackagedExecutionService(root);
  const externalPythonPath = path.join(root, "external-pythonpath");
  const events = [];

  const result = await packaged.startExecutionTask(
    {
      taskId: "packaged-pythonpath",
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "run",
      content: "[打印], 内容: \"ok\"\n",
      env: {
        PATH: "",
        PYTHONPATH: externalPythonPath,
      },
      commandOverride: {
        command: process.execPath,
        args: ["-e", "console.log(process.env.PYTHONPATH || '')"],
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "stdout" && event.text.trim() === externalPythonPath
  )));
});

test("workbench tasks fall back to the Python module when the public executable is unavailable", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  const events = [];

  const result = await startExecutionTask(
    {
      taskId: "workbench-fallback-task",
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "syntax",
      content: "[打印], 内容: \"ok\"\n",
      workbenchExecutable: "missing-pytest-dsl-workbench-for-test",
      pythonExecutable: installedTestPython(),
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "stdout" &&
    event.text.includes("语法检查通过")
  )));
});

test("workbench executable lookup honors the task environment PATH", async () => {
  const root = makeTempProject();
  const binDir = fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-bin-"));
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"ok\"\n");
  writeFile(root, "syntax", "console.log('env workbench syntax')\n");
  writeNodeCommand(binDir, "env-workbench");
  const events = [];

  const result = await startExecutionTask(
    {
      taskId: "env-path-workbench-task",
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "syntax",
      content: "[打印], 内容: \"ok\"\n",
      workbenchExecutable: "env-workbench",
      env: {
        PATH: binDir,
        PATHEXT: ".EXE;.CMD",
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "stdout" &&
    event.text.includes("env workbench syntax")
  )));
});

test("running tasks can be stopped by task id", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/slow.dsl", "[打印], 内容: \"slow\"\n");
  const events = [];

  const pending = startExecutionTask(
    {
      taskId: "stop-task",
      projectRoot: root,
      relativePath: "tests/slow.dsl",
      mode: "debug",
      content: "[打印], 内容: \"slow\"\n",
      commandOverride: {
        command: process.execPath,
        args: ["-e", "setInterval(() => console.log('tick'), 50);"],
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  await waitFor(() => events.some((event) => event.type === "stdout"));
  assert.equal(hasRunningTask("stop-task"), true);

  const stopped = stopExecutionTask("stop-task");
  const result = await pending;

  assert.equal(stopped.stopped, true);
  assert.equal(result.status, "stopped");
  assert.equal(hasRunningTask("stop-task"), false);
  assert.equal(events.at(-1).type, "completed");
  assert.equal(events.at(-1).status, "stopped");
});

test("execution tasks parse structured debug events and map selected line offsets", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"one\"\n[打印], 内容: \"two\"\n");
  const events = [];
  const prefix = "__PYTEST_DSL_GUI_EVENT__";

  const result = await startExecutionTask(
    {
      taskId: "debug-events",
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "debug",
      content: "[打印], 内容: \"one\"\n[打印], 内容: \"two\"\n",
      selection: {
        startLine: 10,
        endLine: 11,
        content: "[打印], 内容: \"one\"\n[打印], 内容: \"two\"\n",
      },
      commandOverride: {
        command: process.execPath,
        args: [
          "-e",
          `console.log('${prefix}' + JSON.stringify({type:'debug_step', phase:'start', line:2, nodeType:'KeywordCall', description:'调用关键字: 打印'})); console.log('normal output');`,
        ],
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "debug-step" &&
    event.phase === "start" &&
    event.line === 11 &&
    event.originalLine === 2 &&
    event.description === "调用关键字: 打印"
  )));
  assert.ok(events.some((event) => event.type === "stdout" && event.text.includes("normal output")));
  assert.equal(events.some((event) => event.type === "stdout" && event.text.includes(prefix)), false);
});

test("debug execution plans can pause from a source line without materializing a suffix", () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"one\"\n[打印], 内容: \"two\"\n");

  const plan = createExecutionPlan({
    taskId: "from-line-plan",
    projectRoot: root,
    relativePath: "tests/case.dsl",
    mode: "debug",
    content: "[打印], 内容: \"one\"\n[打印], 内容: \"two\"\n",
    debugScope: {
      kind: "fromLine",
      startLine: 2,
    },
    yamlVars: ["config/dev.yaml"],
  });

  assert.equal(plan.source.kind, "fromLine");
  assert.equal(plan.source.startLine, 2);
  assert.equal(plan.source.endLine, null);
  assert.equal(
    fs.readFileSync(plan.targetPath, "utf8"),
    "[打印], 内容: \"one\"\n[打印], 内容: \"two\"\n",
  );
  assert.deepEqual(
    plan.args.slice(0, 4),
    ["debug", plan.targetRelativePath, "--pause-from-line", "2"],
  );
  assert.match(plan.displayCommand, /debug tests\/case\.dsl:2-end/);
});

test("structured debug events keep original line numbers when pausing from a line", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"one\"\n[打印], 内容: \"two\"\n");
  const events = [];
  const prefix = "__PYTEST_DSL_GUI_EVENT__";

  const result = await startExecutionTask(
    {
      taskId: "from-line-debug-events",
      projectRoot: root,
      relativePath: "tests/case.dsl",
      mode: "debug",
      content: "[打印], 内容: \"one\"\n[打印], 内容: \"two\"\n",
      debugScope: {
        kind: "fromLine",
        startLine: 2,
      },
      commandOverride: {
        command: process.execPath,
        args: [
          "-e",
          `console.log('${prefix}' + JSON.stringify({type:'debug_step', phase:'start', line:2, nodeType:'KeywordCall', description:'调用关键字: 打印'}));`,
        ],
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => (
    event.type === "debug-step" &&
    event.phase === "start" &&
    event.line === 2 &&
    event.originalLine === 2
  )));
});

test("debug commands are sent to the running process stdin", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/step.dsl", "[打印], 内容: \"step\"\n");
  const events = [];

  const pending = startExecutionTask(
    {
      taskId: "command-task",
      projectRoot: root,
      relativePath: "tests/step.dsl",
      mode: "debug",
      content: "[打印], 内容: \"step\"\n",
      commandOverride: {
        command: process.execPath,
        args: [
          "-e",
          "console.log('ready'); process.stdin.once('data', data => { console.log('command:' + data.toString().trim()); process.exit(0); }); setInterval(() => {}, 1000);",
        ],
      },
    },
    {
      onEvent(event) {
        events.push(event);
      },
    },
  );

  await waitFor(() => events.some((event) => event.type === "stdout" && event.text.includes("ready")));
  const sent = sendExecutionCommand("command-task", "next");
  const result = await pending;

  assert.equal(sent.sent, true);
  assert.equal(result.status, "passed");
  assert.ok(events.some((event) => event.type === "stdout" && event.text.includes("command:next")));
});

async function waitFor(predicate) {
  const deadline = Date.now() + 2000;
  while (Date.now() < deadline) {
    if (predicate()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error("Timed out waiting for condition");
}
