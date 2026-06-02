const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const test = require("node:test");

const {
  getProjectConfigSnapshot,
  getProjectSnapshot,
  readProjectFile,
  saveProjectFile
} = require("../src/services/projectService");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-gui-"));
}

function writeFile(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}

test("non-git projects display local, list DSL files, and load config defaults", () => {
  const root = makeTempProject();
  writeFile(root, "tests/b.dsl", "@name: \"B\"\n[打印], 内容: \"b\"\n");
  writeFile(root, "examples/a.dsl", "@name: \"A\"\n[打印], 内容: \"a\"\n");
  writeFile(root, "config/vars.yaml", "environment: local\napi:\n  base_url: http://localhost\n");
  writeFile(root, "config/override.yml", "environment: test\n");
  writeFile(root, "keywords/gui_keywords.py", "def click_button():\n    return True\n");
  writeFile(root, "README.md", "# Local project\n");
  writeFile(root, "assets/blob.bin", Buffer.from([0, 1, 2, 3]).toString("binary"));

  const snapshot = getProjectSnapshot(root);

  assert.equal(snapshot.git.displayName, "local");
  assert.equal(snapshot.project.name, path.basename(root));
  assert.deepEqual(new Set(snapshot.editableFiles.map((item) => item.relativePath)), new Set([
    "README.md",
    "config/override.yml",
    "config/vars.yaml",
    "examples/a.dsl",
    "keywords/gui_keywords.py",
    "tests/b.dsl"
  ]));
  assert.equal(snapshot.dslFiles.length, 2);
  assert.deepEqual(snapshot.dslFiles.map((item) => item.relativePath), [
    "examples/a.dsl",
    "tests/b.dsl"
  ]);
  assert.equal(snapshot.config.sources.length, 2);
  assert.deepEqual(snapshot.config.selectedPaths, [
    "config/override.yml",
    "config/vars.yaml"
  ]);
  assert.equal(snapshot.config.merged.environment, "local");
  assert.equal(snapshot.config.merged.api.base_url, "http://localhost");
  assert.equal(snapshot.score.value, 100);
});

test("config discovery includes extra YAML candidates but defaults to project config", () => {
  const root = makeTempProject();
  writeFile(root, "case.dsl", "@name: \"Config candidates\"\n");
  writeFile(root, "config/dev.yaml", "environment: dev\n");
  writeFile(root, "tests/auth_config.yaml", "auth:\n  token: local\n");

  const snapshot = getProjectSnapshot(root);

  assert.deepEqual(snapshot.config.sources.map((item) => item.relativePath), [
    "config/dev.yaml",
    "tests/auth_config.yaml"
  ]);
  assert.deepEqual(snapshot.config.selectedPaths, ["config/dev.yaml"]);
  assert.equal(snapshot.config.merged.environment, "dev");
  assert.equal(snapshot.config.merged.auth, undefined);
});

test("git projects display the current branch name", { skip: !hasGit() }, () => {
  const root = makeTempProject();
  execFileSync("git", ["init"], { cwd: root, stdio: "ignore" });
  execFileSync("git", ["checkout", "-b", "feature/electron-gui"], { cwd: root, stdio: "ignore" });
  writeFile(root, "case.dsl", "@name: \"Git case\"\n");
  writeFile(root, "config/default.yaml", "env: dev\n");

  const snapshot = getProjectSnapshot(root);

  assert.equal(snapshot.git.displayName, "feature/electron-gui");
});

test("config parse errors are reported and reduce the score", () => {
  const root = makeTempProject();
  writeFile(root, "case.dsl", "@name: \"Bad config\"\n");
  writeFile(root, "config/bad.yaml", "root:\n  - ok\n broken: true\n");

  const snapshot = getProjectSnapshot(root);

  assert.equal(snapshot.config.errors.length, 1);
  assert.equal(snapshot.config.sources.length, 1);
  assert.equal(snapshot.score.value, 90);
});

test("config snapshots include a signature that changes when YAML changes", () => {
  const root = makeTempProject();
  writeFile(root, "config/remote_servers.yaml", [
    "remote_servers:",
    "  gui_server:",
    "    url: http://localhost:8278/",
    ""
  ].join("\n"));

  const first = getProjectConfigSnapshot(root);
  writeFile(root, "config/remote_servers.yaml", [
    "remote_servers:",
    "  gui_server:",
    "    url: http://localhost:8278/",
    "  i18n_server:",
    "    url: http://localhost:8279/",
    ""
  ].join("\n"));
  const second = getProjectConfigSnapshot(root);

  assert.notEqual(second.config.signature, first.config.signature);
  assert.deepEqual(Object.keys(second.config.merged.remote_servers), [
    "gui_server",
    "i18n_server"
  ]);
});

test("saving a DSL file writes content and updates project metadata", () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "@name: \"Old\"\n");

  const result = saveProjectFile(root, "tests/case.dsl", "@name: \"New\"\n");
  const saved = readProjectFile(root, "tests/case.dsl");
  const metadata = JSON.parse(
    fs.readFileSync(path.join(root, ".pytest-dsl-gui", "metadata.json"), "utf8")
  );

  assert.equal(result.relativePath, "tests/case.dsl");
  assert.equal(saved.content, "@name: \"New\"\n");
  assert.equal(metadata.lastOpenedFile, "tests/case.dsl");
  assert.deepEqual(metadata.recentFiles, ["tests/case.dsl"]);
  assert.equal(metadata.version, 1);
});

test("reading and saving editable text files is not limited to DSL", () => {
  const root = makeTempProject();
  writeFile(root, "config/app.yaml", "name: old\n");
  writeFile(root, "keywords/gui_keywords.py", "VALUE = 'old'\n");

  const yaml = readProjectFile(root, "config/app.yaml");
  const result = saveProjectFile(root, "keywords/gui_keywords.py", "VALUE = 'new'\n");
  const saved = readProjectFile(root, "keywords/gui_keywords.py");
  const metadata = JSON.parse(
    fs.readFileSync(path.join(root, ".pytest-dsl-gui", "metadata.json"), "utf8")
  );

  assert.equal(yaml.content, "name: old\n");
  assert.equal(result.relativePath, "keywords/gui_keywords.py");
  assert.equal(saved.content, "VALUE = 'new'\n");
  assert.equal(metadata.lastOpenedFile, "keywords/gui_keywords.py");
});

test("editable file language classification includes resources and markdown", () => {
  const root = makeTempProject();
  writeFile(root, "resources/gui.resource", "function 准备 do\n  [打印], 内容: \"ok\"\n");
  writeFile(root, "README.md", "# GUI validation\n\n- item\n");
  writeFile(root, "tests/case.dsl", "@name: \"Case\"\n");

  const snapshot = getProjectSnapshot(root);
  const languages = new Map(
    snapshot.editableFiles.map((file) => [file.relativePath, file.language])
  );

  assert.equal(languages.get("resources/gui.resource"), "resource");
  assert.equal(languages.get("README.md"), "markdown");
  assert.equal(languages.get("tests/case.dsl"), "dsl");
  assert.deepEqual(snapshot.dslFiles.map((file) => file.relativePath), ["tests/case.dsl"]);
});

test("reading a DSL file records it as the last opened file", () => {
  const root = makeTempProject();
  writeFile(root, "tests/read.dsl", "@name: \"Read\"\n");

  const result = readProjectFile(root, "tests/read.dsl");
  const metadata = JSON.parse(
    fs.readFileSync(path.join(root, ".pytest-dsl-gui", "metadata.json"), "utf8")
  );

  assert.equal(result.relativePath, "tests/read.dsl");
  assert.equal(result.metadata.lastOpenedFile, "tests/read.dsl");
  assert.equal(metadata.lastOpenedFile, "tests/read.dsl");
});

test("path traversal is rejected for project files", () => {
  const root = makeTempProject();

  assert.throws(
    () => readProjectFile(root, "../outside.dsl"),
    /outside project root/
  );
});

function hasGit() {
  try {
    execFileSync("git", ["--version"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}
