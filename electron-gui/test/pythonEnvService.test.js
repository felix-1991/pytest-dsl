const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  resolvePythonCommand
} = require("../src/services/pythonEnvService");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-python-env-"));
}

function writeExecutable(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, "#!/bin/sh\nexit 0\n", "utf8");
  fs.chmodSync(filePath, 0o755);
}

test("resolvePythonCommand uses explicit pytest-dsl Python first", () => {
  const root = makeTempProject();

  assert.equal(
    resolvePythonCommand(root, { PYTEST_DSL_PYTHON: "/opt/custom/python" }),
    "/opt/custom/python"
  );
});

test("resolvePythonCommand prefers the project virtualenv interpreter", () => {
  const root = makeTempProject();
  const venvPython = process.platform === "win32"
    ? path.join(root, ".venv", "Scripts", "python.exe")
    : path.join(root, ".venv", "bin", "python");
  writeExecutable(venvPython);

  assert.equal(resolvePythonCommand(root, {}), venvPython);
});

test("resolvePythonCommand falls back to python and python3 candidates", () => {
  const root = makeTempProject();

  assert.deepEqual(resolvePythonCommand(root, {}, { all: true }), [
    "python",
    "python3"
  ]);
});
