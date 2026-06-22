const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { execFileSync } = require("node:child_process");

const {
  listKeywords,
  normalizeKeywordPayload
} = require("../src/services/keywordService");

const { updateRuntimeMetadata } = require("../src/services/metadataStore");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-keywords-"));
}

function writeFile(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}

function writeExecutable(root, relativePath, body) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `#!${process.execPath}\n${body}\n`, {
    encoding: "utf8",
    mode: 0o755,
  });
  fs.chmodSync(target, 0o755);
  return target;
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

function loadPackagedKeywordService(root) {
  const sourceDir = path.resolve(__dirname, "..", "src", "services");
  const serviceDir = path.join(root, "Resources", "app.asar", "src", "services");
  fs.mkdirSync(serviceDir, { recursive: true });
  for (const name of ["keywordService.js", "metadataStore.js", "pythonEnvService.js"]) {
    fs.copyFileSync(path.join(sourceDir, name), path.join(serviceDir, name));
  }
  return require(path.join(serviceDir, "keywordService.js"));
}

function keywordPayload(name) {
  return JSON.stringify({
    summary: { total_count: 1 },
    categories: {},
    keywords: [{
      name,
      category: "configured",
      category_name: "Configured Python",
      source: "configured-runtime",
      parameters: [],
      documentation: "configured marker",
    }],
  });
}

function installedTestPython() {
  return execFileSync(
    "python",
    ["-c", "import allure, sys; print(sys.executable)"],
    { encoding: "utf8" },
  ).trim();
}

test("normalizeKeywordPayload keeps editor-facing keyword fields stable", () => {
  const result = normalizeKeywordPayload({
    summary: { total_count: 1 },
    keywords: [
      {
        name: "打印",
        category: "builtin",
        category_name: "系统/基础",
        source: "pytest-dsl内置",
        parameters: [
          { name: "内容", mapping: "content", description: "输出内容" }
        ],
        documentation: "输出日志\n\n更多文档"
      }
    ]
  });

  assert.equal(result.summary.total_count, 1);
  assert.deepEqual(result.keywords, [
    {
      name: "打印",
      category: "builtin",
      categoryName: "系统/基础",
      source: "pytest-dsl内置",
      parameters: [
        { name: "内容", mapping: "content", description: "输出内容", default: undefined }
      ],
      documentation: "输出日志"
    }
  ]);
});

test("listKeywords reads built-in and project resource keywords through pytest-dsl", async () => {
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

  const result = await listKeywords({
    projectRoot: root,
    query: "GUI测试",
    limit: 20
  });

  assert.ok(result.keywords.some((keyword) => keyword.name === "GUI测试关键字"));
  const keyword = result.keywords.find((item) => item.name === "GUI测试关键字");
  assert.equal(keyword.category, "project_custom");
  assert.deepEqual(keyword.parameters.map((param) => param.name), ["输入"]);
});

test("listKeywords uses the Python persisted in project runtime metadata", async () => {
  const root = makeTempProject();
  const python = writeExecutable(
    root,
    "runtime/configured-python",
    `console.log(${JSON.stringify(keywordPayload("配置解释器关键字"))});`,
  );
  updateRuntimeMetadata(root, { pythonExecutable: python });

  const result = await listKeywords({ projectRoot: root, limit: 20 });

  assert.deepEqual(result.keywords.map((keyword) => keyword.name), ["配置解释器关键字"]);
});

test("listKeywords retries an ENOENT candidate with the next resolved Python target", async (t) => {
  const root = makeTempProject();
  writeExecutable(
    root,
    path.join(".venv", "bin", "python"),
    `console.log(${JSON.stringify(keywordPayload("候选重试关键字"))});`,
  );
  setProcessEnv(t, "PYTEST_DSL_PYTHON", path.join(root, "missing-python"));
  setProcessEnv(t, "PYTHON", "");

  const result = await listKeywords({ projectRoot: root, limit: 20 });

  assert.deepEqual(result.keywords.map((keyword) => keyword.name), ["候选重试关键字"]);
});

test("invalid configured Python remains exclusive for keyword listing", async () => {
  const root = makeTempProject();
  const missing = path.join(root, "missing-configured-python");
  updateRuntimeMetadata(root, { pythonExecutable: missing });

  await assert.rejects(
    listKeywords({ projectRoot: root }),
    /Configured Python executable does not exist or is not executable/,
  );
});

test("keyword listing preserves the development PYTHONPATH retry", async (t) => {
  const root = makeTempProject();
  const repoRoot = path.resolve(__dirname, "..", "..");
  const externalPythonPath = path.join(root, "external-pythonpath");
  const python = writeExecutable(
    root,
    "runtime/configured-python",
    [
      "const path = require('node:path');",
      `const repoRoot = ${JSON.stringify(repoRoot)};`,
      "const firstEntry = String(process.env.PYTHONPATH || '').split(path.delimiter)[0];",
      "if (firstEntry !== repoRoot) {",
      "  console.error(\"No module named 'pytest_dsl'\");",
      "  process.exit(1);",
      "}",
      `console.log(${JSON.stringify(keywordPayload("开发路径重试关键字"))});`,
    ].join("\n"),
  );
  updateRuntimeMetadata(root, { pythonExecutable: python });
  setProcessEnv(t, "PYTHONPATH", externalPythonPath);

  const result = await listKeywords({ projectRoot: root, limit: 20 });

  assert.deepEqual(result.keywords.map((keyword) => keyword.name), ["开发路径重试关键字"]);
});

test("packaged keyword listing does not retry with Electron Resources on PYTHONPATH", async (t) => {
  const root = makeTempProject();
  const attemptsPath = path.join(root, "pythonpath-attempts.log");
  const externalPythonPath = path.join(root, "external-pythonpath");
  const python = writeExecutable(
    root,
    "runtime/configured-python",
    [
      "const fs = require('node:fs');",
      `fs.appendFileSync(${JSON.stringify(attemptsPath)}, (process.env.PYTHONPATH || '') + '\\n');`,
      "console.error(\"No module named 'pytest_dsl'\");",
      "process.exit(1);",
    ].join("\n"),
  );
  updateRuntimeMetadata(root, { pythonExecutable: python });
  setProcessEnv(t, "PYTHONPATH", externalPythonPath);
  const packaged = loadPackagedKeywordService(root);

  await assert.rejects(
    packaged.listKeywords({ projectRoot: root }),
    /No module named 'pytest_dsl'/,
  );

  assert.deepEqual(
    fs.readFileSync(attemptsPath, "utf8").trim().split(/\r?\n/),
    [externalPythonPath],
  );
});
