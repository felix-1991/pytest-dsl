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

function writeNodeCommand(root, name, source) {
  const scriptPath = path.join(root, `${name}.js`);
  fs.writeFileSync(scriptPath, source, "utf8");
  if (process.platform === "win32") {
    const commandPath = path.join(root, `${name}.cmd`);
    fs.writeFileSync(commandPath, `@echo off\r\n"${process.execPath}" "${scriptPath}" %*\r\n`, "utf8");
    return commandPath;
  }
  const commandPath = path.join(root, name);
  fs.writeFileSync(commandPath, `#!/bin/sh\nexec "${process.execPath}" "${scriptPath}" "$@"\n`, "utf8");
  fs.chmodSync(commandPath, 0o755);
  return commandPath;
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

test("saveRuntimeExecutable resolves a Python virtualenv directory", () => {
  const root = makeTempProject();
  const python = writeExecutable(path.join(root, ".venv", "bin", "python"));

  saveRuntimeExecutable(root, "python", path.join(root, ".venv"));

  const metadata = readMetadata(root);
  assert.equal(metadata.runtime.pythonExecutable, python);
});

test("saveRuntimeExecutable resolves a Python project directory with a virtualenv", () => {
  const root = makeTempProject();
  const python = writeExecutable(path.join(root, "venv", "bin", "python"));

  saveRuntimeExecutable(root, "python", root);

  const metadata = readMetadata(root);
  assert.equal(metadata.runtime.pythonExecutable, python);
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

test("getRuntimeStatus allows slow Python dependency probes", async () => {
  const root = makeTempProject();
  const slowPython = writeNodeCommand(root, "slow-python", [
    "setTimeout(() => {",
    "  console.log(process.argv[1]);",
    "}, 6000);",
    "",
  ].join("\n"));
  updateRuntimeMetadata(root, { pythonExecutable: slowPython });

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
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
  assert.equal(result.python.command, slowPython);
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

test("getRuntimeStatus includes actionable Python probe failure details", async () => {
  const root = makeTempProject();
  const python = writeExecutable(projectPython(root));

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
    platform: "linux",
    pythonDependencyProbe: () => ({
      status: "error",
      detail: "Python was terminated by signal SIGKILL.",
      signal: "SIGKILL",
    }),
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
  assert.equal(result.python.reason, "python-probe-failed");
  assert.match(result.python.message, /SIGKILL/);
  assert.match(result.python.message, new RegExp(python.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  assert.match(result.python.detail, /Command:/);
  assert.match(result.python.detail, /project virtualenv/);
  assert.match(result.python.action, /Rebuild the project virtualenv/);
  assert.equal(result.python.checked[0].command, python);
});

test("getRuntimeStatus reports Python probe spawn errors without rejecting", async () => {
  const root = makeTempProject();
  const python = writeExecutable(projectPython(root));

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
    platform: "linux",
    pythonDependencyProbe: () => {
      throw new Error("spawn EINVAL");
    },
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
  assert.equal(result.python.reason, "python-probe-failed");
  assert.equal(result.python.command, python);
  assert.match(result.python.detail, /spawn EINVAL/);
});

test("getRuntimeStatus reports Allure probe spawn errors without rejecting", async () => {
  const root = makeTempProject();
  writeExecutable(projectPython(root));

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
    platform: "linux",
    pythonDependencyProbe: (target) => ({ status: "ok", executable: target.command }),
    allureRuntimeProbe: () => {
      throw new Error("spawn EINVAL");
    },
  });

  assert.equal(result.python.available, true);
  assert.equal(result.allure.available, false);
  assert.equal(result.allure.reason, "allure-probe-failed");
  assert.match(result.allure.message, /spawn EINVAL/);
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

test("getRuntimeStatus tries later project venv candidates when the first probe fails", async () => {
  const root = makeTempProject();
  const dotVenvPython = writeExecutable(projectPython(root));
  const venvPython = writeExecutable(path.join(root, "venv", "bin", "python"));
  const probed = [];

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: "" },
    platform: "linux",
    pythonDependencyProbe: (target) => {
      probed.push(target.command);
      if (target.command === dotVenvPython) {
        return { status: "missing", detail: "pytest_dsl" };
      }
      return { status: "ok", executable: target.command };
    },
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
  assert.equal(result.python.command, venvPython);
  assert.equal(result.python.source, "project-venv");
  assert.deepEqual(probed, [dotVenvPython, venvPython]);
  assert.equal(result.python.checked[0].probeStatus, "missing");
  assert.equal(result.python.checked[1].probeStatus, "ok");
});

test("getRuntimeStatus tries later PATH candidates when the first probe lacks dependencies", async () => {
  const root = makeTempProject();
  const binOne = path.join(root, "bin-one");
  const binTwo = path.join(root, "bin-two");
  const systemPython = writeExecutable(path.join(binOne, "python3"));
  const pyenvPython = writeExecutable(path.join(binTwo, "python"));
  const probed = [];

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: { PATH: `${binOne}${path.delimiter}${binTwo}` },
    platform: "linux",
    pythonDependencyProbe: (target) => {
      probed.push(target.command);
      if (target.command === systemPython) {
        return { status: "missing", detail: "pytest_dsl" };
      }
      return { status: "ok", executable: target.command };
    },
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
  assert.equal(result.python.command, pyenvPython);
  assert.equal(result.python.source, "path");
  assert.deepEqual(probed, [systemPython, pyenvPython]);
  assert.equal(result.python.checked[0].probeStatus, "missing");
  assert.equal(result.python.checked[1].probeStatus, "ok");
});

test("getRuntimeStatus prefers project virtualenv over environment python", async () => {
  const root = makeTempProject();
  const venvPython = writeExecutable(projectPython(root));
  const envPython = writeExecutable(path.join(root, "env", "python"));

  const result = await getRuntimeStatus({
    projectRoot: root,
    env: {
      PATH: "",
      PYTEST_DSL_PYTHON: envPython,
      PYTHON: envPython,
    },
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
  assert.equal(result.python.command, venvPython);
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
