const fs = require("node:fs");
const path = require("node:path");
const { execFile } = require("node:child_process");
const { resolvePythonCommands } = require("./pythonEnvService");

const DEFAULT_LIMIT = 80;
const PYTHON_TIMEOUT_MS = 15000;
const PYTHON_MAX_BUFFER = 10 * 1024 * 1024;
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");

const KEYWORD_QUERY_SCRIPT = `
import contextlib
import io
import json
import os
import sys

project_root = sys.argv[1]
name_filter = sys.argv[2] or None
include_remote = sys.argv[3] == "1"

os.chdir(project_root)
captured = io.StringIO()

with contextlib.redirect_stdout(captured):
    from pytest_dsl.core.keyword_utils import list_keywords

    payload = list_keywords(
        output_format="json",
        name_filter=name_filter,
        include_remote=include_remote,
        print_summary=False,
        group_by="flat",
    )

diagnostics = captured.getvalue()
if diagnostics:
    print(diagnostics, file=sys.stderr, end="")

print(json.dumps(payload, ensure_ascii=False))
`;

async function listKeywords(options = {}) {
  const projectRoot = assertProjectRoot(options.projectRoot || REPO_ROOT);
  const query = String(options.query || "").trim();
  const includeRemote = Boolean(options.includeRemote);
  const limit = normalizeLimit(options.limit);
  const payload = await runKeywordQuery(projectRoot, query, includeRemote);
  const result = normalizeKeywordPayload(payload);
  result.keywords = result.keywords.slice(0, limit);
  result.summary.visible_count = result.keywords.length;
  result.query = query;
  return result;
}

function normalizeKeywordPayload(payload = {}) {
  const keywords = (Array.isArray(payload.keywords) ? payload.keywords : [])
    .map(normalizeKeyword)
    .filter((keyword) => keyword.name)
    .sort((left, right) => left.name.localeCompare(right.name, "zh-CN"));

  return {
    summary: {
      ...(isPlainObject(payload.summary) ? payload.summary : {}),
      total_count: Number(
        payload.summary && payload.summary.total_count,
      ) || keywords.length,
    },
    categories: isPlainObject(payload.categories) ? payload.categories : {},
    keywords,
  };
}

function normalizeKeyword(keyword = {}) {
  return {
    name: String(keyword.name || ""),
    category: String(keyword.category || ""),
    categoryName: String(keyword.category_name || keyword.categoryName || ""),
    source: String(keyword.source || sourceName(keyword.source_info) || ""),
    parameters: normalizeParameters(keyword.parameters),
    documentation: firstDocumentationLine(keyword.documentation),
  };
}

function normalizeParameters(parameters) {
  return (Array.isArray(parameters) ? parameters : []).map((param) => ({
    name: String(param && param.name ? param.name : ""),
    mapping: String(param && param.mapping ? param.mapping : ""),
    description: String(param && param.description ? param.description : ""),
    default: param ? param.default : undefined,
  }));
}

function firstDocumentationLine(documentation) {
  return String(documentation || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean) || "";
}

function sourceName(sourceInfo) {
  if (!isPlainObject(sourceInfo)) {
    return "";
  }
  return sourceInfo.display_name || sourceInfo.name || sourceInfo.module || "";
}

function runKeywordQuery(projectRoot, query, includeRemote) {
  return new Promise((resolve, reject) => {
    const commands = resolvePythonCommands(projectRoot, process.env);
    const envs = keywordQueryEnvs();

    const tryCommand = (commandIndex, envIndex = 0) => {
      execFile(
        commands[commandIndex],
        ["-c", KEYWORD_QUERY_SCRIPT, projectRoot, query, includeRemote ? "1" : "0"],
        {
          cwd: projectRoot,
          env: envs[envIndex],
          timeout: PYTHON_TIMEOUT_MS,
          maxBuffer: PYTHON_MAX_BUFFER,
        },
        (error, stdout, stderr) => {
          if (error && error.code === "ENOENT" && commandIndex + 1 < commands.length) {
            tryCommand(commandIndex + 1, envIndex);
            return;
          }
          if (error && shouldRetryWithDevPythonPath(stderr) && envIndex + 1 < envs.length) {
            tryCommand(0, envIndex + 1);
            return;
          }
          if (error) {
            reject(new Error(keywordErrorMessage(error, stderr)));
            return;
          }

          try {
            resolve(JSON.parse(stdout));
          } catch (parseError) {
            reject(new Error(
              `Unable to parse pytest-dsl keyword output: ${parseError.message}`,
            ));
          }
        },
      );
    };

    tryCommand(0, 0);
  });
}

function keywordQueryEnvs() {
  return [process.env, devPythonPathEnv()];
}

function devPythonPathEnv() {
  const existing = process.env.PYTHONPATH || "";
  return {
    ...process.env,
    PYTHONPATH: existing ? `${REPO_ROOT}${path.delimiter}${existing}` : REPO_ROOT,
  };
}

function shouldRetryWithDevPythonPath(stderr) {
  return /No module named ['"]pytest_dsl['"]/.test(String(stderr || ""));
}

function keywordErrorMessage(error, stderr) {
  const detail = String(stderr || "").trim();
  if (detail) {
    return `Unable to load pytest-dsl keywords: ${detail}`;
  }
  return `Unable to load pytest-dsl keywords: ${error.message}`;
}

function assertProjectRoot(projectRoot) {
  const root = path.resolve(String(projectRoot || ""));
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
    throw new Error(`Project root does not exist: ${projectRoot}`);
  }
  return root;
}

function normalizeLimit(limit) {
  const parsed = Math.trunc(Number(limit));
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_LIMIT;
  }
  return Math.min(parsed, 500);
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

module.exports = {
  listKeywords,
  normalizeKeywordPayload,
};
