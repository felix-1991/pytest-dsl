const fs = require("node:fs");
const path = require("node:path");
const { buildSync } = require("esbuild");

const root = path.resolve(__dirname, "..");
const requiredFiles = [
  "main.js",
  "preload.js",
  "src/index.html",
  "src/styles.css",
  "src/renderer.js",
  "src/renderer/buildReportController.js",
  "src/renderer/commandController.js",
  "src/renderer/configController.js",
  "src/renderer/consoleController.js",
  "src/renderer/executionController.js",
  "src/renderer/fileController.js",
  "src/renderer/keywordController.js",
  "src/renderer/layoutController.js",
  "src/renderer/projectController.js",
  "src/renderer/projectTreeController.js",
  "src/renderer/remoteStatusController.js",
  "src/renderer/runtimeController.js",
  "src/renderer/state.js",
  "src/renderer/suiteTreeController.js",
  "src/renderer/treeVirtualizer.js",
  "src/renderer/utils.js",
  "src/renderer/workspaceController.js",
  "src/services/configService.js",
  "src/services/executionService.js",
  "src/services/metadataStore.js",
  "src/services/projectService.js",
  "src/services/remoteStatusService.js",
  "test/projectService.test.js",
  "test/remoteStatusService.test.js"
];

const missing = requiredFiles.filter((filePath) => !fs.existsSync(path.join(root, filePath)));

if (missing.length > 0) {
  console.error(`Missing app files:\n${missing.map((item) => `- ${item}`).join("\n")}`);
  process.exit(1);
}

require(path.join(root, "src/services/projectService"));
checkRendererModuleGraph();

console.log(`Electron GUI app file check passed (${requiredFiles.length} files).`);

function checkRendererModuleGraph() {
  try {
    buildSync({
      entryPoints: [path.join(root, "src", "renderer.js")],
      bundle: true,
      format: "esm",
      platform: "browser",
      write: false,
      logLevel: "silent",
    });
  } catch (error) {
    console.error(`Renderer module graph check failed:\n${formatBuildError(error)}`);
    process.exit(1);
  }
}

function formatBuildError(error) {
  if (Array.isArray(error.errors) && error.errors.length > 0) {
    return error.errors
      .map((item) => item.text || item.message || String(item))
      .join("\n");
  }
  return error && error.message ? error.message : String(error);
}
