const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  appendConsoleLogFile,
  consoleLogPath,
  exportConsoleLogFile,
  resetConsoleLogFile,
} = require("../src/services/consoleLogService");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-console-log-"));
}

test("console log sessions stream to a per-scope project file", () => {
  const root = makeTempProject();

  const reset = resetConsoleLogFile({
    projectRoot: root,
    scope: "debug",
    taskId: "run-123",
  });
  appendConsoleLogFile({
    projectRoot: root,
    scope: "debug",
    text: "[12:00:00] INFO first line\n",
  });
  appendConsoleLogFile({
    projectRoot: root,
    scope: "debug",
    text: "[12:00:01] ERROR failed line\n",
  });

  assert.equal(reset.path, consoleLogPath(root, "debug"));
  const content = fs.readFileSync(reset.path, "utf8");
  assert.match(content, /# pytest-dsl Console Log/);
  assert.match(content, /Scope: debug/);
  assert.match(content, /Task ID: run-123/);
  assert.match(content, /\[12:00:00\] INFO first line/);
  assert.match(content, /\[12:00:01\] ERROR failed line/);
});

test("exporting console logs copies the streamed file without renderer content", () => {
  const root = makeTempProject();
  const destinationPath = path.join(root, "exports", "debug.log");
  resetConsoleLogFile({ projectRoot: root, scope: "debug" });
  appendConsoleLogFile({
    projectRoot: root,
    scope: "debug",
    text: "[12:00:00] INFO streamed line\n",
  });

  const result = exportConsoleLogFile({
    projectRoot: root,
    scope: "debug",
    destinationPath,
  });

  assert.equal(result.path, destinationPath);
  assert.equal(result.sourcePath, consoleLogPath(root, "debug"));
  assert.ok(result.bytes > 0);
  assert.match(fs.readFileSync(destinationPath, "utf8"), /streamed line/);
});
