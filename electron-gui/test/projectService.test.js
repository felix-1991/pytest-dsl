const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const test = require("node:test");

const {
  createProjectEntry,
  deleteProjectEntry,
  getProjectConfigSnapshot,
  getProjectSnapshot,
  moveProjectEntry,
  readProjectFile,
  renameProjectEntry,
  saveProjectConfigSelection,
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

test("project config snapshot records YAML variable definition sources", () => {
  const root = makeTempProject();
  writeFile(root, "tests/case.dsl", "[打印], 内容: \"${api.base_url}\"\n");
  writeFile(root, "config/app.yaml", [
    "environment: local",
    "api:",
    "  base_url: http://localhost",
    "  timeout: 30",
    "enabled: true",
    ""
  ].join("\n"));

  const snapshot = getProjectSnapshot(root);
  const source = snapshot.config.sources.find((item) => item.relativePath === "config/app.yaml");

  assert.ok(source);
  assert.deepEqual(
    source.variableDefinitions.map((definition) => ({
      path: definition.path,
      relativePath: definition.relativePath,
      line: definition.line,
      column: definition.column,
      valuePreview: definition.valuePreview
    })),
    [
      { path: "environment", relativePath: "config/app.yaml", line: 1, column: 1, valuePreview: "local" },
      { path: "api", relativePath: "config/app.yaml", line: 2, column: 1, valuePreview: "{...}" },
      { path: "api.base_url", relativePath: "config/app.yaml", line: 3, column: 3, valuePreview: "http://localhost" },
      { path: "api.timeout", relativePath: "config/app.yaml", line: 4, column: 3, valuePreview: "30" },
      { path: "enabled", relativePath: "config/app.yaml", line: 5, column: 1, valuePreview: "true" }
    ]
  );
});

test("project snapshots include convention suite metadata and ignore generated files", () => {
  const root = makeTempProject();
  writeFile(root, "tests/setup.dsl", "[打印], 内容: \"setup\"\n");
  writeFile(root, "tests/root_case.dsl", "[打印], 内容: \"root\"\n");
  writeFile(root, "tests/test_smoke.py", "def test_smoke():\n    pass\n");
  writeFile(root, "tests/api/auth/login.dsl", "[打印], 内容: \"login\"\n");
  writeFile(root, "tests/api/auth/logout.auto", "[打印], 内容: \"logout\"\n");
  writeFile(root, "tests/api/auth/teardown.dsl", "[打印], 内容: \"teardown\"\n");
  writeFile(root, "tests/api/test_contract.py", "def test_contract():\n    pass\n");
  writeFile(root, "tests/ui/pages/dashboard.dsl", "[打印], 内容: \"dashboard\"\n");
  writeFile(root, "tests/api/auth/.pytest-dsl-generated/test_dsl_cases.py", "def test_generated():\n    pass\n");

  const snapshot = getProjectSnapshot(root);
  const suites = new Map(snapshot.suites.map((suite) => [suite.id, suite]));

  assert.deepEqual(snapshot.suites.map((suite) => suite.id), ["__root__", "api", "api/auth", "ui/pages"]);
  assert.equal(suites.get("__root__").dslCaseCount, 1);
  assert.equal(suites.get("__root__").pythonTestCount, 1);
  assert.deepEqual(suites.get("__root__").dslCaseFiles, ["tests/root_case.dsl"]);
  assert.equal(suites.get("api").dslCaseCount, 0);
  assert.equal(suites.get("api").pythonTestCount, 1);
  assert.equal(suites.get("api/auth").dslCaseCount, 2);
  assert.equal(suites.get("api/auth").pythonTestCount, 0);
  assert.deepEqual(suites.get("api/auth").dslCaseFiles, ["tests/api/auth/login.dsl", "tests/api/auth/logout.auto"]);
  assert.deepEqual(suites.get("api/auth").generatedFiles, []);
  assert.deepEqual(suites.get("api").pythonTestFiles, ["tests/api/test_contract.py"]);
  assert.equal(suites.get("ui/pages").dslCaseCount, 1);
  assert.equal(snapshot.suiteTree.path, "tests");
  
  const rootNode = snapshot.suiteTree;
  const rootDslFileNode = rootNode.children.find(c => c.type === "file" && c.name === "root_case.dsl");
  assert.ok(rootDslFileNode);
  assert.equal(rootDslFileNode.fileType, "dsl");

  const authNode = findTreeNode(snapshot.suiteTree, "api/auth");
  assert.equal(authNode.suiteId, "api/auth");
  assert.equal(authNode.children.length, 2);
  assert.equal(authNode.children[0].type, "file");
  assert.equal(authNode.children[0].name, "login.dsl");
  assert.equal(authNode.children[1].name, "logout.auto");

  assert.equal(findTreeNode(snapshot.suiteTree, "ui/pages").suiteId, "ui/pages");
  assert.equal(
    snapshot.editableFiles.some((file) => file.relativePath.includes(".pytest-dsl-generated")),
    false
  );
});

test("project snapshots include a recursive editable tree with empty directories", () => {
  const root = makeTempProject();
  fs.mkdirSync(path.join(root, "tests/empty/nested"), { recursive: true });
  writeFile(root, "README.md", "# Project\n");
  writeFile(root, "tests/nested/case.dsl", "@name: \"Nested\"\n");
  writeFile(root, "config/app.yaml", "name: gui\n");
  writeFile(root, ".pytest-dsl-generated/ignored.dsl", "[打印], 内容: \"ignored\"\n");
  writeFile(root, "assets/blob.bin", Buffer.from([0, 1, 2, 3]).toString("binary"));

  const snapshot = getProjectSnapshot(root);

  assert.equal(snapshot.tree.type, "directory");
  assert.equal(snapshot.tree.path, "");
  assert.equal(findTreeNode(snapshot.tree, "README.md").type, "file");
  assert.equal(findTreeNode(snapshot.tree, "tests").type, "directory");
  assert.equal(findTreeNode(snapshot.tree, "tests/empty/nested").type, "directory");
  assert.equal(findTreeNode(snapshot.tree, "tests/nested/case.dsl").language, "dsl");
  assert.equal(findTreeNode(snapshot.tree, "config/app.yaml").lineCount, 1);
  assert.equal(findTreeNode(snapshot.tree, ".pytest-dsl-generated/ignored.dsl"), null);
  assert.equal(findTreeNode(snapshot.tree, "assets/blob.bin"), null);
});

test("config discovery only includes YAML files under the config directory", () => {
  const root = makeTempProject();
  writeFile(root, "case.dsl", "@name: \"Config candidates\"\n");
  writeFile(root, "config/dev.yaml", "environment: dev\n");
  writeFile(root, "tests/auth_config.yaml", "auth:\n  token: local\n");

  const snapshot = getProjectSnapshot(root);

  assert.deepEqual(snapshot.config.sources.map((item) => item.relativePath), [
    "config/dev.yaml"
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

test("project snapshots restore persisted config selection", () => {
  const root = makeTempProject();
  writeFile(root, "config/app.yaml", "name: gui\n");
  writeFile(root, "config/i18n.yaml", "locale: zh-CN\n");
  writeFile(root, "config/remote_servers.yaml", [
    "remote_servers:",
    "  gui_server:",
    "    url: http://localhost:8278/",
    ""
  ].join("\n"));

  saveProjectConfigSelection(root, ["config/remote_servers.yaml"]);

  const snapshot = getProjectSnapshot(root);
  const configSnapshot = getProjectConfigSnapshot(root);

  assert.deepEqual(snapshot.metadata.config.selectedPaths, ["config/remote_servers.yaml"]);
  assert.deepEqual(snapshot.config.selectedPaths, ["config/remote_servers.yaml"]);
  assert.equal(snapshot.config.merged.name, undefined);
  assert.equal(snapshot.config.merged.locale, undefined);
  assert.deepEqual(Object.keys(snapshot.config.merged.remote_servers), ["gui_server"]);
  assert.deepEqual(configSnapshot.config.selectedPaths, ["config/remote_servers.yaml"]);
});

test("saving config selection drops missing paths and keeps empty selections explicit", () => {
  const root = makeTempProject();
  writeFile(root, "config/app.yaml", "name: gui\n");
  writeFile(root, "config/remote_servers.yaml", "remote_servers: {}\n");

  const saved = saveProjectConfigSelection(root, [
    "config/missing.yaml",
    "config/remote_servers.yaml",
    "config/remote_servers.yaml"
  ]);

  assert.deepEqual(saved.metadata.config.selectedPaths, ["config/remote_servers.yaml"]);
  assert.deepEqual(saved.config.selectedPaths, ["config/remote_servers.yaml"]);

  const empty = saveProjectConfigSelection(root, []);
  const snapshot = getProjectSnapshot(root);

  assert.deepEqual(empty.metadata.config.selectedPaths, []);
  assert.deepEqual(snapshot.config.selectedPaths, []);
  assert.deepEqual(snapshot.config.merged, {});
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

test("project entry CRUD creates renames and deletes files and folders", () => {
  const root = makeTempProject();
  fs.mkdirSync(path.join(root, "tests"), { recursive: true });

  const createdDir = createProjectEntry(root, {
    kind: "directory",
    relativePath: "tests/new_suite"
  });
  const createdFile = createProjectEntry(root, {
    kind: "file",
    relativePath: "tests/new_suite/case.dsl",
    content: "@name: \"New\"\n"
  });
  const renamedFile = renameProjectEntry(root, {
    relativePath: createdFile.relativePath,
    newName: "renamed.dsl"
  });
  const renamedDir = renameProjectEntry(root, {
    relativePath: createdDir.relativePath,
    newName: "renamed_suite"
  });

  assert.equal(createdDir.kind, "directory");
  assert.equal(createdFile.kind, "file");
  assert.equal(renamedFile.relativePath, "tests/new_suite/renamed.dsl");
  assert.equal(renamedDir.relativePath, "tests/renamed_suite");
  assert.equal(
    fs.readFileSync(path.join(root, "tests/renamed_suite/renamed.dsl"), "utf8"),
    "@name: \"New\"\n"
  );

  assert.throws(
    () => deleteProjectEntry(root, { relativePath: "tests/renamed_suite" }),
    /non-empty directory/
  );
  const deleted = deleteProjectEntry(root, {
    relativePath: "tests/renamed_suite",
    recursive: true
  });

  assert.equal(deleted.relativePath, "tests/renamed_suite");
  assert.equal(fs.existsSync(path.join(root, "tests/renamed_suite")), false);
});

test("project entry move relocates files into directories without overwriting", () => {
  const root = makeTempProject();
  writeFile(root, "tests/source/case.dsl", "@name: \"Move\"\n");
  fs.mkdirSync(path.join(root, "tests/target"), { recursive: true });

  const moved = moveProjectEntry(root, {
    relativePath: "tests/source/case.dsl",
    targetDirectory: "tests/target"
  });

  assert.equal(moved.kind, "file");
  assert.equal(moved.relativePath, "tests/target/case.dsl");
  assert.equal(moved.previousPath, "tests/source/case.dsl");
  assert.equal(fs.existsSync(path.join(root, "tests/source/case.dsl")), false);
  assert.equal(
    fs.readFileSync(path.join(root, "tests/target/case.dsl"), "utf8"),
    "@name: \"Move\"\n"
  );

  writeFile(root, "tests/source/case.dsl", "@name: \"Conflict\"\n");
  assert.throws(
    () => moveProjectEntry(root, {
      relativePath: "tests/source/case.dsl",
      targetDirectory: "tests/target"
    }),
    /already exists/
  );
  assert.throws(
    () => moveProjectEntry(root, {
      relativePath: "tests/source",
      targetDirectory: "tests/target"
    }),
    /Only files can be moved/
  );
});

test("path traversal is rejected for project files", () => {
  const root = makeTempProject();

  assert.throws(
    () => readProjectFile(root, "../outside.dsl"),
    /outside project root/
  );
  assert.throws(
    () => createProjectEntry(root, {
      kind: "file",
      relativePath: "../outside.dsl",
      content: ""
    }),
    /outside project root/
  );
  assert.throws(
    () => renameProjectEntry(root, {
      relativePath: "missing.dsl",
      newName: "../outside.dsl"
    }),
    /name cannot contain path separators/
  );
  assert.throws(
    () => moveProjectEntry(root, {
      relativePath: "missing.dsl",
      targetDirectory: "../outside"
    }),
    /outside project root/
  );
});

function findTreeNode(root, relativePath) {
  const target = String(relativePath || "").replace(/\\/g, "/");
  if (!root) {
    return null;
  }
  if ((root.path || "") === target) {
    return root;
  }
  for (const child of root.children || []) {
    const result = findTreeNode(child, target);
    if (result) {
      return result;
    }
  }
  return null;
}

function hasGit() {
  try {
    execFileSync("git", ["--version"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}
