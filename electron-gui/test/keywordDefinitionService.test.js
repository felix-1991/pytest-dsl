const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { execFileSync } = require("node:child_process");

const {
  findKeywordDefinitions,
  listKeywordDefinitions,
  normalizeDefinitionPayload
} = require("../src/services/keywordDefinitionService");

const { updateRuntimeMetadata } = require("../src/services/metadataStore");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-definitions-"));
}

function writeFile(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}

function writeSiteCustomize(directory, lines) {
  fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(
    path.join(directory, "sitecustomize.py"),
    `${lines.join("\n")}\n`,
    "utf8",
  );
}

function setProcessEnv(t, name, value) {
  const hadValue = Object.prototype.hasOwnProperty.call(process.env, name);
  const previous = process.env[name];
  process.env[name] = value;
  t.after(() => {
    if (hadValue) {
      process.env[name] = previous;
    } else {
      delete process.env[name];
    }
  });
}

function loadPackagedDefinitionService(root) {
  const sourceDir = path.resolve(__dirname, "..", "src", "services");
  const serviceDir = path.join(root, "Resources", "app.asar", "src", "services");
  fs.mkdirSync(serviceDir, { recursive: true });
  for (const name of [
    "keywordDefinitionService.js",
    "metadataStore.js",
    "pythonEnvService.js",
  ]) {
    fs.copyFileSync(path.join(sourceDir, name), path.join(serviceDir, name));
  }
  return require(path.join(serviceDir, "keywordDefinitionService.js"));
}

let cachedTestPython = null;

function installedTestPython() {
  if (cachedTestPython) {
    return cachedTestPython;
  }
  const candidates = [
    [process.env.PYTEST_DSL_TEST_PYTHON, []],
    [process.env.PYTHON, []],
    ["python", []],
    ["python3", []],
    ["py", ["-3"]],
  ];
  for (const [command, prefixArgs] of candidates) {
    if (!command) {
      continue;
    }
    try {
      cachedTestPython = execFileSync(
        command,
        [...prefixArgs, "-c", "import allure, sys; print(sys.executable)"],
        { encoding: "utf8" },
      ).trim();
      if (cachedTestPython) {
        return cachedTestPython;
      }
    } catch (_error) {
      // Try the next installed Python command.
    }
  }
  throw new Error("No test Python with pytest-dsl dependencies is available");
}

test("normalizeDefinitionPayload marks files outside the project as readonly package definitions", () => {
  const root = makeTempProject();
  const externalFile = path.join(os.tmpdir(), "site-packages", "pytest_dsl", "keywords", "system_keywords.py");

  const normalized = normalizeDefinitionPayload(root, {
    definitions: [
      {
        name: "打印",
        sourceType: "python",
        path: externalFile,
        line: 17,
        column: 1,
        module: "pytest_dsl.keywords.system_keywords",
        parameters: []
      }
    ]
  });

  assert.deepEqual(normalized.definitions, [
    {
      definitionId: "打印:package_python:17:" + externalFile,
      name: "打印",
      sourceType: "package_python",
      path: externalFile,
      relativePath: null,
      line: 17,
      column: 1,
      readonly: true,
      module: "pytest_dsl.keywords.system_keywords",
      parameters: []
    }
  ]);
});

test("listKeywordDefinitions indexes resource and project Python keyword locations", async () => {
  const root = makeTempProject();
  updateRuntimeMetadata(root, { pythonExecutable: installedTestPython() });
  writeFile(root, "resources/gui.resource", [
    "@name: \"GUI资源\"",
    "",
    "function GUI测试关键字 (输入) do",
    "    [打印], 内容: ${输入}",
    "    return ${输入}",
    "end",
    ""
  ].join("\n"));
  writeFile(root, "keywords/gui_keywords.py", [
    "from pytest_dsl.core.keyword_manager import keyword_manager",
    "",
    "@keyword_manager.register('项目Python关键字', [",
    "    {'name': '输入', 'mapping': 'value', 'description': '输入值'}",
    "])",
    "def project_python_keyword(**kwargs):",
    "    return kwargs.get('value')",
    ""
  ].join("\n"));

  const result = await listKeywordDefinitions({ projectRoot: root });
  const resource = result.definitions.find((item) => item.name === "GUI测试关键字");
  const projectPython = result.definitions.find((item) => item.name === "项目Python关键字");

  assert.equal(resource.sourceType, "project_resource");
  assert.equal(resource.relativePath, "resources/gui.resource");
  assert.equal(resource.line, 3);
  assert.equal(resource.readonly, false);
  assert.deepEqual(resource.parameters.map((param) => param.name), ["输入"]);

  assert.equal(projectPython.sourceType, "project_python");
  assert.equal(projectPython.relativePath, "keywords/gui_keywords.py");
  assert.equal(projectPython.line, 6);
  assert.equal(projectPython.readonly, false);
  assert.deepEqual(projectPython.parameters.map((param) => param.name), ["输入"]);
});

test("findKeywordDefinitions returns package Python definitions for pip-installed builtins", async () => {
  const root = makeTempProject();
  updateRuntimeMetadata(root, { pythonExecutable: installedTestPython() });

  const result = await findKeywordDefinitions({
    projectRoot: root,
    keywordName: "打印"
  });

  assert.ok(result.definitions.length >= 1);
  const builtin = result.definitions[0];
  assert.equal(builtin.name, "打印");
  assert.equal(builtin.sourceType, "package_python");
  assert.equal(builtin.relativePath, null);
  assert.equal(builtin.readonly, true);
  assert.match(builtin.path, /system_keywords\.py$/);
  assert.ok(builtin.line > 0);
});

test("definition list and find queries use the persisted project Python", async (t) => {
  const root = makeTempProject();
  const sourcePath = path.join(root, "keywords", "configured_keyword.py");
  writeFile(root, "keywords/configured_keyword.py", "def configured_keyword():\n    pass\n");
  const payload = JSON.stringify({
    definitions: [{
      name: "配置解释器定义",
      sourceType: "python",
      path: sourcePath,
      line: 1,
      column: 1,
      module: "configured_keyword",
      parameters: [],
    }],
  });
  writeSiteCustomize(root, [
    "import os",
    `print(${JSON.stringify(payload)}, flush=True)`,
    "os._exit(0)",
  ]);
  setProcessEnv(t, "PYTHONPATH", root);
  updateRuntimeMetadata(root, { pythonExecutable: installedTestPython() });

  const listed = await listKeywordDefinitions({ projectRoot: root });
  const found = await findKeywordDefinitions({
    projectRoot: root,
    keywordName: "配置解释器定义",
  });

  assert.deepEqual(listed.definitions.map((definition) => definition.name), ["配置解释器定义"]);
  assert.deepEqual(found.definitions.map((definition) => definition.name), ["配置解释器定义"]);
  assert.equal(found.definitions[0].relativePath, "keywords/configured_keyword.py");
});

test("invalid configured Python remains exclusive for definition queries", async () => {
  const root = makeTempProject();
  const missing = path.join(root, "missing-configured-python");
  updateRuntimeMetadata(root, { pythonExecutable: missing });

  await assert.rejects(
    findKeywordDefinitions({ projectRoot: root, keywordName: "打印" }),
    /Configured Python executable does not exist or is not executable/,
  );
});

test("definition queries preserve the development PYTHONPATH retry", async (t) => {
  const root = makeTempProject();
  const repoRoot = path.resolve(__dirname, "..", "..");
  const externalPythonPath = path.join(root, "external-pythonpath");
  const sourcePath = path.join(root, "keywords", "dev_retry.py");
  writeFile(root, "keywords/dev_retry.py", "def dev_retry():\n    pass\n");
  const payload = JSON.stringify({
    definitions: [{
      name: "开发路径重试定义",
      sourceType: "python",
      path: sourcePath,
      line: 1,
      column: 1,
      module: "dev_retry",
      parameters: [],
    }],
  });
  writeSiteCustomize(externalPythonPath, [
    "import os",
    "import sys",
    `repo_root = os.path.normcase(os.path.realpath(${JSON.stringify(repoRoot)}))`,
    "first_entry = os.environ.get('PYTHONPATH', '').split(os.pathsep)[0]",
    "if os.path.normcase(os.path.realpath(first_entry)) != repo_root:",
    "    print(\"No module named 'pytest_dsl'\", file=sys.stderr, flush=True)",
    "    os._exit(1)",
    `print(${JSON.stringify(payload)}, flush=True)`,
    "os._exit(0)",
  ]);
  updateRuntimeMetadata(root, { pythonExecutable: installedTestPython() });
  setProcessEnv(t, "PYTHONPATH", externalPythonPath);

  const result = await findKeywordDefinitions({
    projectRoot: root,
    keywordName: "开发路径重试定义",
  });

  assert.deepEqual(result.definitions.map((definition) => definition.name), ["开发路径重试定义"]);
});

test("packaged definition queries do not retry with Electron Resources on PYTHONPATH", async (t) => {
  const root = makeTempProject();
  const attemptsPath = path.join(root, "pythonpath-attempts.log");
  const externalPythonPath = path.join(root, "external-pythonpath");
  writeSiteCustomize(externalPythonPath, [
    "import os",
    "import sys",
    `with open(${JSON.stringify(attemptsPath)}, 'a', encoding='utf-8') as stream:`,
    "    stream.write(os.environ.get('PYTHONPATH', '') + '\\n')",
    "print(\"No module named 'pytest_dsl'\", file=sys.stderr, flush=True)",
    "os._exit(1)",
  ]);
  updateRuntimeMetadata(root, { pythonExecutable: installedTestPython() });
  setProcessEnv(t, "PYTHONPATH", externalPythonPath);
  const packaged = loadPackagedDefinitionService(root);

  await assert.rejects(
    packaged.findKeywordDefinitions({ projectRoot: root, keywordName: "打印" }),
    /No module named 'pytest_dsl'/,
  );

  assert.deepEqual(
    fs.readFileSync(attemptsPath, "utf8").trim().split(/\r?\n/),
    [externalPythonPath],
  );
});
