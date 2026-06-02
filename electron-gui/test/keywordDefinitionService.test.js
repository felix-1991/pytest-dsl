const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  findKeywordDefinitions,
  listKeywordDefinitions,
  normalizeDefinitionPayload
} = require("../src/services/keywordDefinitionService");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-definitions-"));
}

function writeFile(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
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
