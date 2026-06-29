const fs = require("node:fs");
const path = require("node:path");

function consoleLogPath(projectRoot, scope) {
  return path.join(
    assertProjectRoot(projectRoot),
    ".pytest-dsl-gui",
    "console",
    `${normalizeScope(scope)}.log`,
  );
}

function resetConsoleLogFile(options = {}) {
  const targetPath = consoleLogPath(options.projectRoot, options.scope);
  const header = [
    "# pytest-dsl Console Log",
    `Scope: ${normalizeScope(options.scope)}`,
    options.taskId ? `Task ID: ${sanitizeHeaderValue(options.taskId)}` : null,
    `Started At: ${new Date().toISOString()}`,
    "",
  ].filter((line) => line !== null).join("\n");

  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, `${header}\n`, "utf8");
  return {
    path: targetPath,
    bytes: fs.statSync(targetPath).size,
  };
}

function appendConsoleLogFile(options = {}) {
  const text = String(options.text || "");
  const targetPath = consoleLogPath(options.projectRoot, options.scope);
  if (!text) {
    return { path: targetPath, bytes: fileSize(targetPath) };
  }
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.appendFileSync(targetPath, text, "utf8");
  return {
    path: targetPath,
    bytes: fs.statSync(targetPath).size,
  };
}

function exportConsoleLogFile(options = {}) {
  const sourcePath = consoleLogPath(options.projectRoot, options.scope);
  const destinationPath = assertDestinationPath(options.destinationPath);
  if (!fs.existsSync(sourcePath)) {
    throw new Error("Console log file is not available for the current execution");
  }
  fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
  fs.copyFileSync(sourcePath, destinationPath);
  return {
    path: destinationPath,
    sourcePath,
    bytes: fs.statSync(destinationPath).size,
  };
}

function defaultConsoleLogExportName(scope) {
  return `pytest-dsl-console-${normalizeScope(scope)}.log`;
}

function normalizeScope(scope) {
  return scope === "build" ? "build" : "debug";
}

function assertProjectRoot(projectRoot) {
  if (!projectRoot || typeof projectRoot !== "string") {
    throw new Error("projectRoot is required");
  }
  return path.resolve(projectRoot);
}

function assertDestinationPath(destinationPath) {
  if (!destinationPath || typeof destinationPath !== "string") {
    throw new Error("destinationPath is required");
  }
  return path.resolve(destinationPath);
}

function sanitizeHeaderValue(value) {
  return String(value).replace(/\r?\n/g, " ");
}

function fileSize(filePath) {
  return fs.existsSync(filePath) ? fs.statSync(filePath).size : 0;
}

module.exports = {
  appendConsoleLogFile,
  consoleLogPath,
  defaultConsoleLogExportName,
  exportConsoleLogFile,
  resetConsoleLogFile,
};
