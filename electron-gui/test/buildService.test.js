const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  createBuildPlan,
  exportAllureReportFile,
  exportBuildLogs,
  hasRunningBuild,
  startBuildTask,
  stopBuildTask,
} = require("../src/services/buildService");

const { updateRuntimeMetadata } = require("../src/services/metadataStore");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-build-"));
}

function writeFile(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}

function writeExecutable(root, name, content) {
  const target = path.join(root, name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, { encoding: "utf8", mode: 0o755 });
  fs.chmodSync(target, 0o755);
  return target;
}

function writeProjectPython(root) {
  return writeExecutable(
    root,
    path.join(".venv", "bin", "python"),
    `#!${process.execPath}\nconsole.log(process.argv.slice(2).join(' '));\n`,
  );
}

function loadPackagedBuildService(root) {
  const sourceDir = path.resolve(__dirname, "..", "src", "services");
  const serviceDir = path.join(root, "Resources", "app.asar", "src", "services");
  fs.mkdirSync(serviceDir, { recursive: true });
  for (const name of [
    "buildService.js",
    "metadataStore.js",
    "pythonEnvService.js",
    "suiteService.js",
  ]) {
    fs.copyFileSync(path.join(sourceDir, name), path.join(serviceDir, name));
  }
  return require(path.join(serviceDir, "buildService.js"));
}

test("build plans create isolated Allure artifact directories and pytest args", () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  writeFile(root, "tests/api/test_contract.py", "def test_contract():\n    pass\n");

  const plan = createBuildPlan({
    buildId: "build-plan",
    projectRoot: root,
    selectedSuiteIds: ["api"],
    yamlVars: ["config/dev.yaml"],
  });

  assert.equal(plan.buildId, "build-plan");
  assert.equal(plan.cwd, root);
  assert.equal(plan.command, "pytest");
  assert.equal(
    plan.buildDir,
    path.join(root, ".pytest-dsl-gui", "builds", "build-plan"),
  );
  assert.equal(plan.allureResultsDir, path.join(plan.buildDir, "allure-results"));
  assert.equal(plan.allureReportDir, path.join(plan.buildDir, "allure-report"));
  assert.deepEqual(plan.args, [
    "tests/api",
    "--alluredir",
    ".pytest-dsl-gui/builds/build-plan/allure-results",
    "--yaml-vars",
    "config/dev.yaml",
  ]);
  assert.match(
    plan.displayCommand,
    /^pytest tests\/api --alluredir \.pytest-dsl-gui\/builds\/build-plan\/allure-results --yaml-vars config\/dev\.yaml$/,
  );
});

test("build tasks stream pytest output, emit report url, and persist a manifest", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  const events = [];
  const buildId = "stream-build";

  try {
    const result = await startBuildTask(
      {
        buildId,
        projectRoot: root,
        selectedSuiteIds: ["api"],
        pytestCommandOverride: {
          command: process.execPath,
          args: ["-e", "console.log('pytest ok')"],
        },
        allureCommandOverride: {
          command: process.execPath,
          args: [
            "-e",
            "console.log('Allure report: http://127.0.0.1:4321'); setInterval(() => {}, 1000);",
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
    assert.equal(hasRunningBuild(buildId), true);
    assert.ok(events.some((event) => event.type === "build-started"));
    await waitFor(() => events.some((event) => event.type === "report-ready" && event.url === "http://127.0.0.1:4321/awesome/"));
    assert.ok(events.some((event) => event.type === "stdout" && event.text.includes("pytest ok")));
    assert.ok(events.some((event) => event.type === "build-completed" && event.status === "passed"));

    const manifestPath = path.join(root, ".pytest-dsl-gui", "builds", buildId, "build.json");
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    assert.equal(manifest.buildId, buildId);
    assert.equal(manifest.status, "passed");
    assert.equal(manifest.reportUrl, "http://127.0.0.1:4321/awesome/");

    const stopped = stopBuildTask(buildId);
    assert.equal(stopped.stopped, true);
    assert.equal(hasRunningBuild(buildId), false);
  } finally {
    stopBuildTask(buildId);
  }
});

test("build tasks emit a direct report url after the Allure report route is reachable", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  const events = [];
  const buildId = "direct-report-build";
  const probed = [];

  try {
    await startBuildTask(
      {
        buildId,
        projectRoot: root,
        selectedSuiteIds: ["api"],
        pytestCommandOverride: {
          command: process.execPath,
          args: ["-e", "console.log('pytest ok')"],
        },
        allureCommandOverride: {
          command: process.execPath,
          args: [
            "-e",
            "console.log('Allure is running on http://127.0.0.1:4323'); setInterval(() => {}, 1000);",
          ],
        },
        allureReportReadyProbe: async (url) => {
          probed.push(url);
          return `${url.replace(/\/$/, "")}/awesome/`;
        },
      },
      {
        onEvent(event) {
          events.push(event);
        },
      },
    );

    await waitFor(() => events.some((event) => event.type === "report-ready"));
    const reportReady = events.find((event) => event.type === "report-ready");
    assert.deepEqual(probed, ["http://127.0.0.1:4323"]);
    assert.equal(reportReady.url, "http://127.0.0.1:4323/awesome/");

    const manifestPath = path.join(root, ".pytest-dsl-gui", "builds", buildId, "build.json");
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    assert.equal(manifest.reportUrl, "http://127.0.0.1:4323/awesome/");
  } finally {
    stopBuildTask(buildId);
  }
});

test("build completion waits briefly for delayed Allure report readiness", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  const events = [];
  const buildId = "delayed-report-build";

  try {
    const result = await startBuildTask(
      {
        buildId,
        projectRoot: root,
        selectedSuiteIds: ["api"],
        pytestCommandOverride: {
          command: process.execPath,
          args: ["-e", "console.log('pytest finished')"],
        },
        allureCommandOverride: {
          command: process.execPath,
          args: [
            "-e",
            "setTimeout(() => console.log('Allure is running on http://127.0.0.1:4324'), 150); setInterval(() => {}, 1000);",
          ],
        },
        allureReportReadyProbe: async (url) => `${url.replace(/\/$/, "")}/awesome/`,
      },
      {
        onEvent(event) {
          events.push(event);
        },
      },
    );

    const reportReadyIndex = events.findIndex((event) => event.type === "report-ready");
    const completedIndex = events.findIndex((event) => event.type === "build-completed");
    assert.notEqual(reportReadyIndex, -1);
    assert.notEqual(completedIndex, -1);
    assert.ok(reportReadyIndex < completedIndex);
    assert.equal(result.reportUrl, "http://127.0.0.1:4324/awesome/");
    assert.equal(events[completedIndex].reportUrl, "http://127.0.0.1:4324/awesome/");
  } finally {
    stopBuildTask(buildId);
  }
});

test("build tasks are removed when pytest and the report process both exit", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  const buildId = "cleanup-build";

  const result = await startBuildTask({
    buildId,
    projectRoot: root,
    selectedSuiteIds: ["api"],
    pytestCommandOverride: {
      command: process.execPath,
      args: ["-e", "console.log('pytest done')"],
    },
    allureCommandOverride: {
      command: process.execPath,
      args: ["-e", "console.log('Allure report: http://127.0.0.1:4322')"],
    },
  });

  assert.equal(result.status, "passed");
  await waitFor(() => !hasRunningBuild(buildId));
  assert.equal(hasRunningBuild(buildId), false);
});

test("build uses the project virtualenv Python when PATH is empty", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  writeProjectPython(root);
  const events = [];
  const buildId = "project-python-build";

  const result = await startBuildTask(
    {
      buildId,
      projectRoot: root,
      selectedSuiteIds: ["api"],
      enableAllureWatch: false,
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
    event.type === "stdout" && event.text.includes("-m pytest")
  )));
  assert.equal(events.some((event) => String(event.text || "").includes("ENOENT")), false);
  assert.equal(hasRunningBuild(buildId), false);
});

test("Python preflight failure does not start Allure or register a running build", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  const buildId = "invalid-python-preflight";
  const reportMarker = path.join(root, "report-started.txt");
  const invalidPython = path.join(root, "missing-python");
  updateRuntimeMetadata(root, { pythonExecutable: invalidPython });

  try {
    await assert.rejects(
      startBuildTask({
        buildId,
        projectRoot: root,
        selectedSuiteIds: ["api"],
        env: { PATH: "" },
        allureCommandOverride: {
          command: process.execPath,
          args: [
            "-e",
            `require('node:fs').writeFileSync(${JSON.stringify(reportMarker)}, 'started'); setInterval(() => {}, 1000);`,
          ],
        },
      }),
      /Configured Python executable does not exist or is not executable/,
    );

    assert.equal(fs.existsSync(reportMarker), false);
    assert.equal(hasRunningBuild(buildId), false);
    assert.equal(
      fs.existsSync(path.join(root, ".pytest-dsl-gui", "builds", buildId)),
      false,
    );
  } finally {
    stopBuildTask(buildId);
  }
});

test("packaged builds preserve external PYTHONPATH without adding Resources", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  const packaged = loadPackagedBuildService(root);
  const externalPythonPath = path.join(root, "external-pythonpath");
  const events = [];

  const result = await packaged.startBuildTask(
    {
      buildId: "packaged-pythonpath-build",
      projectRoot: root,
      selectedSuiteIds: ["api"],
      enableAllureWatch: false,
      env: {
        PATH: "",
        PYTHONPATH: externalPythonPath,
      },
      pytestCommandOverride: {
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

test("completed build logs can be exported as a saved log file", async () => {
  const root = makeTempProject();
  writeFile(root, "tests/api/login.dsl", "[打印], 内容: \"login\"\n");
  const buildId = "download-log-build";
  const destinationPath = path.join(root, "exports", "download-log-build.log");

  await startBuildTask({
    buildId,
    projectRoot: root,
    selectedSuiteIds: ["api"],
    enableAllureWatch: false,
    pytestCommandOverride: {
      command: process.execPath,
      args: ["-e", "console.log('pytest stdout line'); console.error('pytest stderr line')"],
    },
  });

  const result = exportBuildLogs({
    projectRoot: root,
    buildId,
    destinationPath,
  });

  assert.equal(result.buildId, buildId);
  assert.equal(result.path, destinationPath);
  assert.ok(result.bytes > 0);
  const content = fs.readFileSync(destinationPath, "utf8");
  assert.match(content, /# pytest-dsl Build Log/);
  assert.match(content, /Build ID: download-log-build/);
  assert.match(content, /Status: passed/);
  assert.match(content, /## stdout/);
  assert.match(content, /pytest stdout line/);
  assert.match(content, /## stderr/);
  assert.match(content, /pytest stderr line/);
  assert.match(content, /## manifest/);
});

test("completed Allure results can be exported as a single HTML report file", async () => {
  const root = makeTempProject();
  const buildId = "download-report-build";
  const buildDir = path.join(root, ".pytest-dsl-gui", "builds", buildId);
  const resultsDir = path.join(buildDir, "allure-results");
  const destinationPath = path.join(root, "exports", "download-report-build.html");
  const fakeAllurePath = path.join(root, "fake-allure.js");
  const calledArgsPath = path.join(root, "fake-allure-args.json");

  fs.mkdirSync(resultsDir, { recursive: true });
  fs.writeFileSync(path.join(resultsDir, "result.json"), "{\"status\":\"passed\"}\n", "utf8");
  fs.writeFileSync(path.join(buildDir, "stdout.log"), "done\n", "utf8");
  fs.writeFileSync(path.join(buildDir, "stderr.log"), "", "utf8");
  fs.writeFileSync(path.join(buildDir, "build.json"), `${JSON.stringify({
    buildId,
    status: "passed",
    command: "pytest tests/api --alluredir .pytest-dsl-gui/builds/download-report-build/allure-results",
    allureResultsDir: resultsDir,
    allureReportDir: path.join(buildDir, "allure-report"),
  }, null, 2)}\n`, "utf8");
  fs.writeFileSync(fakeAllurePath, `
const fs = require("node:fs");
const path = require("node:path");
const args = process.argv.slice(2);
fs.writeFileSync(${JSON.stringify(calledArgsPath)}, JSON.stringify(args));
const output = args[args.indexOf("--output") + 1];
fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(path.join(output, "index.html"), "<!doctype html><title>Allure</title>");
`, "utf8");

  const result = await exportAllureReportFile({
    projectRoot: root,
    buildId,
    destinationPath,
    allureExportCommandOverride: {
      command: process.execPath,
      args: [fakeAllurePath],
    },
  });

  assert.equal(result.buildId, buildId);
  assert.equal(result.path, destinationPath);
  assert.ok(result.bytes > 0);
  assert.equal(fs.readFileSync(destinationPath, "utf8"), "<!doctype html><title>Allure</title>");
  const calledArgs = JSON.parse(fs.readFileSync(calledArgsPath, "utf8"));
  assert.deepEqual(calledArgs, [
    "awesome",
    "--single-file",
    "--output",
    path.join(buildDir, "allure-report"),
    resultsDir,
  ]);
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
