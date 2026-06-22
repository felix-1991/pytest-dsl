const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  readMetadata,
  updateRuntimeMetadata,
} = require("../src/services/metadataStore");
const {
  getRuntimeStatus,
  resetRuntimeExecutable,
  saveRuntimeExecutable,
} = require("../src/services/runtimeConfigService");

function makeTempProject() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-runtime-config-"));
  return root;
}

function writeExecutable(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content || "#!/bin/sh\necho fixture\n", "utf8");
  fs.chmodSync(filePath, 0o755);
  return filePath;
}

function projectPython(root, platform = "linux") {
  return platform === "win32"
    ? path.join(root, ".venv", "Scripts", "python.exe")
    : path.join(root, ".venv", "bin", "python");
}

test("saveRuntimeExecutable requires absolute path", () => {
  const root = makeTempProject();
  const missingFile = path.join(root, "relative-python");
  fs.mkdirSync(path.dirname(missingFile), { recursive: true });
  fs.writeFileSync(missingFile, "fake", "utf8");

  assert.throws(
    () => saveRuntimeExecutable(root, "python", "relative/python"),
    /absolute path/,
  );
});

test("saveRuntimeExecutable requires file to exist", () => {
  const root = makeTempProject();
  assert.throws(
    () => saveRuntimeExecutable(root, "python", path.join(root, "missing-python")),
    /does not exist/,
  );
});

test("saveRuntimeExecutable persists the path", () => {
  const root = makeTempProject();
  const python = writeExecutable(path.join(root, "python"));

  saveRuntimeExecutable(root, "python", python);
  const metadata = readMetadata(root);
  assert.equal(metadata.runtime.pythonExecutable, python);

  const allure = writeExecutable(path.join(root, "allure"));
  saveRuntimeExecutable(root, "allure", allure);
  const updated = readMetadata(root);
  assert.equal(updated.runtime.pythonExecutable, python);
  assert.equal(updated.runtime.allureExecutable, allure);
});

test("resetRuntimeExecutable clears the saved path", () => {
  const root = makeTempProject();
  const python = writeExecutable(path.join(root, "python"));
  saveRuntimeExecutable(root, "python", python);

  resetRuntimeExecutable(root, "python");
  const metadata = readMetadata(root);
  assert.equal(metadata.runtime.pythonExecutable, null);
});

test("resetRuntimeExecutable rejects unsupported kind", () => {
  const root = makeTempProject();
  assert.throws(
    () => resetRuntimeExecutable(root, "java"),
    /Unsupported runtime kind/,
  );
});

test("getRuntimeStatus reports missing configured python as python-not-found", async () => {
  const root = makeTempProject();
  updateRuntimeMetadata(root, { pythonExecutable: "/nonexistent/python" });

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
    platform: "linux",
  });
  assert.equal(result.python.available, false);
  assert.equal(result.python.reason, "python-not-found");
  assert.match(result.python.message, /does not exist/);
});

test("getRuntimeStatus reports missing dependencies as python-dependency-missing", async () => {
  const root = makeTempProject();
  const python = writeExecutable(
    projectPython(root),
    "#!/bin/sh\necho fake\n",
  );

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
    platform: "linux",
    pythonDependencyProbe: () => ({ status: "missing", detail: "pytest_dsl" }),
    allureRuntimeProbe: () => ({
      available: false,
      command: null,
      args: [],
      source: null,
      version: null,
      reason: "allure-not-found",
      message: "Allure 3 was not found",
    }),
  });
  assert.equal(result.python.available, false);
  assert.equal(result.python.reason, "python-dependency-missing");
});

test("getRuntimeStatus reports available python when probe succeeds", async () => {
  const root = makeTempProject();
  const python = writeExecutable(projectPython(root));

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
    platform: "linux",
    pythonDependencyProbe: (target) => ({ status: "ok", executable: target.command }),
    allureRuntimeProbe: () => ({
      available: false,
      command: null,
      args: [],
      source: null,
      version: null,
      reason: "allure-not-found",
      message: "Allure 3 was not found",
    }),
  });
  assert.equal(result.python.available, true);
  assert.equal(result.python.reason, null);
  assert.equal(result.python.source, "project-venv");
});

test("getRuntimeStatus combines python and allure probes", async () => {
  const root = makeTempProject();
  writeExecutable(projectPython(root));

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
    platform: "linux",
    pythonDependencyProbe: (target) => ({ status: "ok", executable: target.command }),
    allureRuntimeProbe: () => ({
      available: true,
      command: "/opt/allure",
      args: [],
      source: "path",
      version: "3.1.0",
      reason: null,
      message: "Allure 3.1.0",
    }),
  });
  assert.equal(result.python.available, true);
  assert.equal(result.allure.available, true);
  assert.equal(result.allure.version, "3.1.0");
  assert.equal(result.projectRoot, root);
  assert.deepEqual(result.config, { pythonExecutable: null, allureExecutable: null });
});

test("getRuntimeStatus rejects invalid projectRoot", async () => {
  await assert.rejects(
    () => getRuntimeStatus({ projectRoot: "/nonexistent/path" }),
    /does not exist/,
  );
});
