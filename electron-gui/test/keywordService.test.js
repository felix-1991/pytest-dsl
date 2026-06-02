const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  listKeywords,
  normalizeKeywordPayload
} = require("../src/services/keywordService");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-keywords-"));
}

function writeFile(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
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
