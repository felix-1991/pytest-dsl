const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  createBuildPlan,
  hasRunningBuild,
  startBuildTask,
  stopBuildTask,
} = require("../src/services/buildService");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-build-"));
}

function writeFile(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
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
