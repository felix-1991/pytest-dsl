const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  prepareSearchCandidates,
  replaceProjectMatches,
  searchProjectBatches,
  searchProject,
} = require("../src/services/searchService");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-search-"));
}

function writeFile(root, relativePath, content, encoding = "utf8") {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, encoding);
}

function candidateFor(root, relativePath, language = "dsl") {
  const target = path.join(root, relativePath);
  const content = fs.readFileSync(target, "utf8");
  return {
    relativePath,
    language,
    size: Buffer.byteLength(content, "utf8"),
    lineCount: content.split(/\r?\n/).length,
  };
}

function initGitRepo(root) {
  try {
    execFileSync("git", ["init"], { cwd: root, stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

test("searchProject supports Chinese queries from the supplied editable-file snapshot", () => {
  const root = makeTempProject();
  writeFile(root, "included.dsl", "用户登录成功\n");
  writeFile(root, "excluded.dsl", "用户登录失败\n");

  const result = searchProject(root, {
    query: "登录",
    candidates: [candidateFor(root, "included.dsl")],
    options: {},
  });

  assert.equal(result.totalMatches, 1);
  assert.equal(result.scannedFiles, 1);
  assert.deepEqual(result.files.map((file) => file.relativePath), ["included.dsl"]);
  assert.deepEqual(result.files[0].matches.map((match) => ({
    line: match.line,
    column: match.column,
    matchText: match.matchText,
    preview: match.preview,
  })), [
    { line: 1, column: 3, matchText: "登录", preview: "用户登录成功" },
  ]);
});

test("searchProjectBatches emits Chinese search results incrementally", async () => {
  assert.equal(typeof searchProjectBatches, "function");
  const root = makeTempProject();
  writeFile(root, "a.dsl", "用户登录成功\n");
  writeFile(root, "b.dsl", "管理员登录成功\n");
  const batches = [];

  const summary = await searchProjectBatches(
    root,
    {
      query: "登录",
      candidates: [
        candidateFor(root, "a.dsl"),
        candidateFor(root, "b.dsl"),
      ],
      options: { batchSize: 1 },
    },
    (batch) => batches.push(batch),
  );

  assert.equal(summary.totalMatches, 2);
  assert.equal(summary.scannedFiles, 2);
  assert.equal(batches.length, 2);
  assert.deepEqual(
    batches.flatMap((batch) => batch.files.map((file) => file.relativePath)),
    ["a.dsl", "b.dsl"],
  );
  assert.deepEqual(
    batches.flatMap((batch) => batch.files.flatMap((file) => file.matches.map((match) => match.matchText))),
    ["登录", "登录"],
  );
});

test("searchProject scans editable text files and reports grouped matches", () => {
  const root = makeTempProject();
  writeFile(root, "tests/login.dsl", [
    "@name: \"Login\"",
    "[打印], 内容: \"hello\"",
    "[打印], 内容: \"hello again\"",
    "",
  ].join("\n"));
  writeFile(root, "README.md", "hello from docs\n");
  writeFile(root, ".pytest-dsl-generated/ignored.dsl", "hello generated\n");
  writeFile(root, "assets/blob.bin", Buffer.from([0, 1, 2, 3]));

  const result = searchProject(root, {
    query: "hello",
    options: { caseSensitive: false },
  });

  assert.equal(result.totalMatches, 3);
  assert.equal(result.matchedFiles, 2);
  assert.equal(result.scannedFiles, 2);
  assert.equal(result.truncated, false);
  assert.deepEqual(result.files.map((file) => file.relativePath), [
    "README.md",
    "tests/login.dsl",
  ]);
  assert.deepEqual(result.files[1].matches.map((match) => ({
    line: match.line,
    column: match.column,
    matchText: match.matchText,
  })), [
    { line: 2, column: 12, matchText: "hello" },
    { line: 3, column: 12, matchText: "hello" },
  ]);
});

test("searchProject excludes files and directories ignored by gitignore", (t) => {
  const root = makeTempProject();
  if (!initGitRepo(root)) {
    t.skip("git is not available");
    return;
  }
  writeFile(root, ".gitignore", "ignored-dir/\n*.secret\n");
  writeFile(root, "included.dsl", "needle included\n");
  writeFile(root, "ignored-dir/hidden.dsl", "needle ignored directory\n");
  writeFile(root, "notes.secret", "needle ignored file\n");

  const result = searchProject(root, {
    query: "needle",
    options: {},
  });

  assert.equal(result.totalMatches, 1);
  assert.equal(result.scannedFiles, 2);
  assert.deepEqual(result.files.map((file) => file.relativePath), ["included.dsl"]);

  const replacement = replaceProjectMatches(root, {
    query: "needle",
    replacement: "replaced",
    options: {},
    files: result.files,
  });

  assert.equal(replacement.replacements, 1);
  assert.equal(fs.readFileSync(path.join(root, "included.dsl"), "utf8"), "replaced included\n");
  assert.equal(fs.readFileSync(path.join(root, "ignored-dir/hidden.dsl"), "utf8"), "needle ignored directory\n");
  assert.equal(fs.readFileSync(path.join(root, "notes.secret"), "utf8"), "needle ignored file\n");
});

test("prepareSearchCandidates filters gitignored files once for cached project searches", (t) => {
  assert.equal(typeof prepareSearchCandidates, "function");
  const root = makeTempProject();
  if (!initGitRepo(root)) {
    t.skip("git is not available");
    return;
  }
  writeFile(root, ".gitignore", "ignored-dir/\n*.secret\n");
  writeFile(root, "included.dsl", "needle included\n");
  writeFile(root, "ignored-dir/hidden.dsl", "needle ignored directory\n");
  writeFile(root, "notes.secret", "needle ignored file\n");

  const candidates = [
    candidateFor(root, "included.dsl"),
    candidateFor(root, "ignored-dir/hidden.dsl"),
    candidateFor(root, "notes.secret"),
  ];
  const prepared = prepareSearchCandidates(root, candidates);

  assert.deepEqual(prepared.map((file) => file.relativePath), ["included.dsl"]);
  const result = searchProject(root, {
    query: "needle",
    candidates: prepared,
    candidatesRespectGitignore: true,
    options: {},
  });

  assert.equal(result.totalMatches, 1);
  assert.equal(result.scannedFiles, 1);
  assert.deepEqual(result.files.map((file) => file.relativePath), ["included.dsl"]);
});

test("searchProject supports case-sensitive, whole-word, regex, and result limits", () => {
  const root = makeTempProject();
  writeFile(root, "case.dsl", [
    "[打印], 内容: \"Token token tokenized\"",
    "[打印], 内容: \"id=42 id=43\"",
    "",
  ].join("\n"));

  const caseSensitive = searchProject(root, {
    query: "Token",
    options: { caseSensitive: true },
  });
  assert.equal(caseSensitive.totalMatches, 1);
  assert.equal(caseSensitive.files[0].matches[0].matchText, "Token");

  const wholeWord = searchProject(root, {
    query: "token",
    options: { wholeWord: true },
  });
  assert.equal(wholeWord.totalMatches, 2);
  assert.deepEqual(
    wholeWord.files[0].matches.map((match) => match.matchText),
    ["Token", "token"],
  );

  const regexp = searchProject(root, {
    query: "id=(\\d+)",
    options: { regexp: true },
  });
  assert.equal(regexp.totalMatches, 2);
  assert.deepEqual(
    regexp.files[0].matches.map((match) => match.matchText),
    ["id=42", "id=43"],
  );

  const limited = searchProject(root, {
    query: "token",
    options: { maxMatches: 1 },
  });
  assert.equal(limited.totalMatches, 1);
  assert.equal(limited.truncated, true);
});

test("searchProject bounds previews from very long single-line files", () => {
  const root = makeTempProject();
  const longLine = `${"a".repeat(5000)}GUI${"b".repeat(5000)}\n`;
  writeFile(root, "allure-report/app.js", longLine);

  const result = searchProject(root, {
    query: "GUI*",
    options: { regexp: true },
  });

  const match = result.files[0].matches[0];
  assert.equal(result.totalMatches, 1);
  assert.equal(match.line, 1);
  assert.equal(match.column, 5001);
  assert.equal(match.matchText, "GUI");
  assert.ok(match.preview.length <= 240, `preview length ${match.preview.length} should be bounded`);
  assert.match(match.preview, /^\.\.\./);
  assert.match(match.preview, /\.\.\.$/);
  assert.match(match.preview, /GUI/);
});

test("searchProject caps broad regex match text and replace still uses file content", () => {
  const root = makeTempProject();
  const longMatch = `start${"x".repeat(5000)}end\n`;
  writeFile(root, "long.dsl", longMatch);

  const preview = searchProject(root, {
    query: "start[\\s\\S]+end",
    options: { regexp: true },
  });

  const match = preview.files[0].matches[0];
  assert.equal(preview.totalMatches, 1);
  assert.equal(match.matchTextTruncated, true);
  assert.ok(match.matchText.length <= 1024);
  assert.ok(JSON.stringify(preview).length < longMatch.length);

  const replacement = replaceProjectMatches(root, {
    query: "start[\\s\\S]+end",
    replacement: "done",
    options: { regexp: true },
    files: preview.files,
  });

  assert.equal(replacement.replacements, 1);
  assert.equal(fs.readFileSync(path.join(root, "long.dsl"), "utf8"), "done\n");
});

test("searchProject skips files above the configured size limit", () => {
  const root = makeTempProject();
  writeFile(root, "small.dsl", "needle\n");
  writeFile(root, "large.dsl", "needle in a larger file\n");

  const result = searchProject(root, {
    query: "needle",
    options: { maxFileSizeBytes: 10 },
  });

  assert.equal(result.totalMatches, 1);
  assert.deepEqual(result.files.map((file) => file.relativePath), ["small.dsl"]);
  assert.deepEqual(result.skippedFiles, [
    { relativePath: "large.dsl", reason: "file-too-large", size: 24 },
  ]);
});

test("replaceProjectMatches updates previewed matches and rejects stale files", () => {
  const root = makeTempProject();
  writeFile(root, "tests/a.dsl", "[打印], 内容: \"hello\"\n");
  writeFile(root, "tests/b.dsl", "[打印], 内容: \"hello\"\n");

  const preview = searchProject(root, {
    query: "hello",
    options: {},
  });
  writeFile(root, "tests/b.dsl", "[打印], 内容: \"changed\"\n");

  const result = replaceProjectMatches(root, {
    query: "hello",
    replacement: "hi",
    options: {},
    files: preview.files,
  });

  assert.equal(result.replacements, 1);
  assert.deepEqual(result.changedFiles, ["tests/a.dsl"]);
  assert.deepEqual(result.conflicts.map((conflict) => conflict.relativePath), [
    "tests/b.dsl",
  ]);
  assert.equal(fs.readFileSync(path.join(root, "tests/a.dsl"), "utf8"), "[打印], 内容: \"hi\"\n");
  assert.equal(fs.readFileSync(path.join(root, "tests/b.dsl"), "utf8"), "[打印], 内容: \"changed\"\n");
});

test("replaceProjectMatches applies regex capture replacements", () => {
  const root = makeTempProject();
  writeFile(root, "ids.dsl", "id=42\nid=43\n");
  const preview = searchProject(root, {
    query: "id=(\\d+)",
    options: { regexp: true },
  });

  const result = replaceProjectMatches(root, {
    query: "id=(\\d+)",
    replacement: "case-$1",
    options: { regexp: true },
    files: preview.files,
  });

  assert.equal(result.replacements, 2);
  assert.equal(fs.readFileSync(path.join(root, "ids.dsl"), "utf8"), "case-42\ncase-43\n");
});

test("replaceProjectMatches treats dollar replacement text literally outside regex mode", () => {
  const root = makeTempProject();
  writeFile(root, "literal.dsl", "hello\n");
  const preview = searchProject(root, {
    query: "hello",
    options: {},
  });

  replaceProjectMatches(root, {
    query: "hello",
    replacement: "$&",
    options: {},
    files: preview.files,
  });

  assert.equal(fs.readFileSync(path.join(root, "literal.dsl"), "utf8"), "$&\n");
});
