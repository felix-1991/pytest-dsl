const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const requiredFiles = [
  "main.js",
  "preload.js",
  "src/index.html",
  "src/styles.css",
  "src/renderer.js",
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

console.log(`Electron GUI app file check passed (${requiredFiles.length} files).`);
