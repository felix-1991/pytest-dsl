const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { updateRuntimeMetadata } = require("../src/services/metadataStore");
const {
  resolveAllureCandidates,
  resolveAllureRuntime,
} = require("../src/services/allureEnvService");

function makeTempProject() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-allure-env-"));
  return root;
}

function writeExecutable(filePath, content = "#!/bin/sh\necho fixture\n") {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
  fs.chmodSync(filePath, 0o755);
  return filePath;
}

function writeAllureFake(root, name, versionOutput) {
  const target = path.join(root, name);
  const script = process.platform === "win32"
    ? `@echo off\necho ${versionOutput}\n`
    : `#!/bin/sh\necho "${versionOutput}"\n`;
  writeExecutable(target, script);
  return target;
}

test("configured Allure from metadata is an exclusive candidate with source project-config", async () => {
  const root = makeTempProject();
  const configured = writeAllureFake(root, "my-allure", "Allure commandline, version 3.1.0");
  updateRuntimeMetadata(root, { allureExecutable: configured });

  const result = await resolveAllureRuntime(root, { PATH: "" });
  assert.equal(result.available, true);
  assert.equal(result.source, "project-config");
  assert.equal(result.version, "3.1.0");
  assert.equal(result.reason, null);
});

test("configured Allure from PYTEST_DSL_ALLURE env wins over metadata", async () => {
  const root = makeTempProject();
  const fromEnv = writeAllureFake(root, "env-allure", "Allure commandline, version 3.2.0");
  const fromMeta = writeAllureFake(root, "meta-allure", "Allure commandline, version 3.1.0");
  updateRuntimeMetadata(root, { allureExecutable: fromMeta });

  const candidates = resolveAllureCandidates(root, { PYTEST_DSL_ALLURE: fromEnv, PATH: "" });
  assert.equal(candidates.length, 1);
  assert.equal(candidates[0].command, fromEnv);
  assert.equal(candidates[0].source, "project-config");
});

test("configured Allure v2 returns version-unsupported", async () => {
  const root = makeTempProject();
  const configured = writeAllureFake(root, "allure-v2", "Allure commandline, version 2.20.0");
  updateRuntimeMetadata(root, { allureExecutable: configured });

  const result = await resolveAllureRuntime(root, { PATH: process.env.PATH || "" });
  assert.equal(result.available, false);
  assert.equal(result.reason, "allure-version-unsupported");
  assert.match(result.message, /Allure 3/);
  assert.equal(result.version, "2.20.0");
});

test("configured Allure missing returns allure-config-invalid", async () => {
  const root = makeTempProject();
  updateRuntimeMetadata(root, { allureExecutable: "/nonexistent/path/allure" });

  const result = await resolveAllureRuntime(root, { PATH: process.env.PATH || "" });
  assert.equal(result.available, false);
  assert.equal(result.reason, "allure-config-invalid");
});

test("no Allure anywhere returns allure-not-found", async () => {
  const root = makeTempProject();
  const result = await resolveAllureRuntime(root, { PATH: "" }, { skipCommonPaths: true });
  assert.equal(result.available, false);
  assert.equal(result.reason, "allure-not-found");
  assert.match(result.detail, /Checked Allure locations/);
  assert.match(result.detail, /node_modules/);
  assert.match(result.action, /Install Allure 3/);
});

test("project node_modules Allure 3 is discovered before PATH", async () => {
  const root = makeTempProject();
  const projectAllure = writeAllureFake(
    root,
    path.join("node_modules", ".bin", "allure"),
    "Allure commandline, version 3.0.5",
  );

  const result = await resolveAllureRuntime(root, { PATH: "" }, { skipCommonPaths: true });
  assert.equal(result.available, true);
  assert.equal(result.source, "project-node-modules");
  assert.equal(result.command, projectAllure);
});

test("Windows project node_modules Allure candidate is selected by requested platform", () => {
  const root = makeTempProject();
  const projectAllure = writeAllureFake(
    root,
    path.join("node_modules", ".bin", "allure.cmd"),
    "Allure commandline, version 3.0.5",
  );

  const candidates = resolveAllureCandidates(root, { PATH: "" }, {
    platform: "win32",
    skipCommonPaths: true,
  });

  assert.equal(candidates[0].command, projectAllure);
  assert.equal(candidates[0].source, "project-node-modules");
});

test("POSIX Allure detection can use login shell PATH without fixed install paths", async () => {
  const root = makeTempProject();
  const shellBin = path.join(root, "shell-bin");
  const shellAllure = writeAllureFake(
    shellBin,
    "allure",
    "Allure commandline, version 3.4.0",
  );

  const result = await resolveAllureRuntime(root, { PATH: "" }, {
    platform: "linux",
    skipCommonPaths: true,
    shellPathProvider: () => shellBin,
  });

  assert.equal(result.available, true);
  assert.equal(result.command, shellAllure);
  assert.equal(result.source, "path");
  assert.equal(result.version, "3.4.0");
});

test("non-configured v2 candidate is skipped, allowing v3 fallback", async () => {
  const root = makeTempProject();
  writeAllureFake(
    root,
    path.join("node_modules", ".bin", "allure"),
    "Allure commandline, version 2.10.0",
  );
  const pathBinDir = path.join(root, "path-bin");
  fs.mkdirSync(pathBinDir, { recursive: true });
  const pathAllureName = process.platform === "win32" ? "allure.cmd" : "allure";
  const pathAllure = path.join(pathBinDir, pathAllureName);
  writeExecutable(pathAllure, process.platform === "win32"
    ? "@echo off\necho Allure commandline, version 3.2.0\n"
    : "#!/bin/sh\necho \"Allure commandline, version 3.2.0\"\n");

  const result = await resolveAllureRuntime(root, { PATH: pathBinDir }, { skipCommonPaths: true });
  assert.equal(result.available, true);
  assert.equal(result.version, "3.2.0");
  assert.equal(result.command, pathAllure);
});

test("configured Allure with unreadable version returns allure-version-unreadable", async () => {
  const root = makeTempProject();
  const configured = writeAllureFake(root, "bad-allure", "no version here");
  updateRuntimeMetadata(root, { allureExecutable: configured });

  const result = await resolveAllureRuntime(root, { PATH: "" });
  assert.equal(result.available, false);
  assert.equal(result.reason, "allure-version-unreadable");
});
