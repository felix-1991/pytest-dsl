const fs = require("node:fs");
const path = require("node:path");
const { execFile } = require("node:child_process");

const {
  mergeEnvironment,
  resolvePythonTargets,
  withPythonProcessEnv,
} = require("./pythonEnvService");

const PYTHON_TIMEOUT_MS = 15000;
const PYTHON_MAX_BUFFER = 10 * 1024 * 1024;
const DEFINITION_CACHE_TTL_MS = 60000;
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");

const definitionFullCache = new Map();
const resourceDefinitionCache = new Map();
const IGNORED_DIRS = new Set([
  ".git",
  ".pytest-dsl-gui",
  ".venv",
  "venv",
  "__pycache__",
  "node_modules",
  "dist",
  "build",
  ".pytest_cache",
]);

const PYTHON_DEFINITION_SCRIPT = `
import contextlib
import inspect
import io
import json
import os
import sys

project_root = sys.argv[1]

os.chdir(project_root)
captured = io.StringIO()

def parameter_dict(param):
    return {
        "name": getattr(param, "name", str(param)),
        "mapping": getattr(param, "mapping", ""),
        "description": getattr(param, "description", ""),
        "default": getattr(param, "default", None),
    }

definitions = []
with contextlib.redirect_stdout(captured):
    from pytest_dsl.core.keyword_loader import load_all_keywords
    from pytest_dsl.core.keyword_manager import keyword_manager

    project_custom_keywords = load_all_keywords(include_remote=False) or {}

    for name, info in keyword_manager._keywords.items():
        if name in project_custom_keywords:
            continue

        func = info.get("func")
        if not func:
            continue

        try:
            unwrapped = inspect.unwrap(func)
            source_file = inspect.getsourcefile(unwrapped) or inspect.getfile(unwrapped)
            source_lines = None
            start_line = None
            try:
                source_lines, start_line = inspect.getsourcelines(unwrapped)
            except Exception:
                pass
        except Exception:
            continue

        if not source_file:
            continue

        definition_line = int(start_line or 1)
        if source_lines is not None:
            for offset, line_text in enumerate(source_lines):
                if line_text.lstrip().startswith("def "):
                    definition_line = int(start_line + offset)
                    break

        definitions.append({
            "name": name,
            "sourceType": "python",
            "path": os.path.abspath(source_file),
            "line": definition_line,
            "column": 1,
            "module": getattr(unwrapped, "__module__", ""),
            "parameters": [parameter_dict(param) for param in info.get("parameters", [])],
        })

diagnostics = captured.getvalue()
if diagnostics:
    print(diagnostics, file=sys.stderr, end="")

print(json.dumps({"definitions": definitions}, ensure_ascii=False))
`;

async function listKeywordDefinitions(options = {}) {
  const projectRoot = assertProjectRoot(options.projectRoot || REPO_ROOT);
  const keywordName = String(options.keywordName || "").trim();

  const cached = getCachedDefinitions(projectRoot);
  if (cached) {
    return keywordName
      ? { definitions: cached.definitions.filter((d) => d.name === keywordName) }
      : cached;
  }

  const [resourcePayload, pythonPayload] = await Promise.all([
    Promise.resolve(scanResourceDefinitions(projectRoot)),
    runPythonDefinitionQuery(projectRoot),
  ]);
  const payload = normalizeDefinitionPayload(projectRoot, {
    definitions: [
      ...resourcePayload.definitions,
      ...pythonPayload.definitions,
    ],
  });

  setCachedDefinitions(projectRoot, payload);

  return keywordName
    ? { definitions: payload.definitions.filter((d) => d.name === keywordName) }
    : payload;
}

async function findKeywordDefinitions(options = {}) {
  const keywordName = String(options.keywordName || "").trim();
  if (!keywordName) {
    return { definitions: [] };
  }
  const result = await listKeywordDefinitions({
    ...options,
    keywordName,
  });
  return result;
}

function normalizeDefinitionPayload(projectRoot, payload = {}) {
  const root = realPath(projectRoot);
  const definitions = (Array.isArray(payload.definitions) ? payload.definitions : [])
    .map((definition) => normalizeDefinition(root, definition))
    .filter((definition) => definition.name && definition.path && definition.line > 0)
    .sort(compareDefinitions);

  return { definitions };
}

function normalizeDefinition(projectRoot, definition = {}) {
  const absolutePath = realPath(definition.path || "");
  const relativePath = projectRelativePath(projectRoot, absolutePath);
  const requestedType = String(definition.sourceType || "");
  const sourceType = normalizeSourceType(requestedType, relativePath);
  const line = Math.max(1, Math.trunc(Number(definition.line)) || 1);
  const column = Math.max(1, Math.trunc(Number(definition.column)) || 1);
  const name = String(definition.name || "");

  return {
    definitionId: `${name}:${sourceType}:${line}:${absolutePath}`,
    name,
    sourceType,
    path: absolutePath,
    relativePath,
    line,
    column,
    readonly: relativePath === null,
    module: String(definition.module || ""),
    parameters: normalizeParameters(definition.parameters),
  };
}

function normalizeSourceType(sourceType, relativePath) {
  if (sourceType === "resource") {
    return "project_resource";
  }
  if (sourceType === "python") {
    return relativePath ? "project_python" : "package_python";
  }
  if (sourceType === "remote") {
    return "remote";
  }
  return relativePath ? "project_python" : "package_python";
}

function normalizeParameters(parameters) {
  return (Array.isArray(parameters) ? parameters : []).map((param) => ({
    name: String(param && param.name ? param.name : ""),
    mapping: String(param && param.mapping ? param.mapping : ""),
    description: String(param && param.description ? param.description : ""),
    default: param ? param.default : undefined,
  }));
}

function readSourceFile(projectRoot, sourcePath) {
  const root = realPath(projectRoot || REPO_ROOT);
  const target = realPath(sourcePath || "");
  if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
    throw new Error(`Source file does not exist: ${sourcePath}`);
  }
  const content = readTextFileContent(target);
  if (content === null) {
    throw new Error(`Only text source files can be opened: ${sourcePath}`);
  }
  const relativePath = projectRelativePath(root, target);
  return {
    path: target,
    relativePath,
    content,
    language: detectLanguage(target),
    readonly: relativePath === null,
  };
}

function readTextFileContent(filePath) {
  const buffer = fs.readFileSync(filePath);
  if (buffer.includes(0)) {
    return null;
  }
  try {
    return buffer.toString("utf8");
  } catch {
    return null;
  }
}

function detectLanguage(filePath) {
  const name = String(filePath || "").toLowerCase();
  if (name.endsWith(".dsl")) return "dsl";
  if (name.endsWith(".resource")) return "resource";
  if (name.endsWith(".yaml") || name.endsWith(".yml")) return "yaml";
  if (name.endsWith(".py")) return "python";
  if (name.endsWith(".md") || name.endsWith(".markdown")) return "markdown";
  return "plain";
}

function projectRelativePath(projectRoot, absolutePath) {
  const relative = path.relative(projectRoot, absolutePath);
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) {
    return null;
  }
  return relative.replace(/\\/g, "/");
}

function realPath(filePath) {
  const resolved = path.resolve(String(filePath || ""));
  try {
    return fs.realpathSync.native(resolved);
  } catch {
    return resolved;
  }
}

function compareDefinitions(left, right) {
  const rank = {
    project_resource: 0,
    project_python: 1,
    package_python: 2,
    remote: 3,
  };
  const rankDiff = (rank[left.sourceType] ?? 99) - (rank[right.sourceType] ?? 99);
  if (rankDiff !== 0) {
    return rankDiff;
  }
  return left.name.localeCompare(right.name, "zh-CN") ||
    String(left.path).localeCompare(String(right.path)) ||
    left.line - right.line;
}

function scanResourceDefinitions(projectRoot) {
  const cached = resourceDefinitionCache.get(projectRoot);
  if (cached && Date.now() - cached.timestamp < DEFINITION_CACHE_TTL_MS) {
    return cached.payload;
  }

  const definitions = [];
  walk(projectRoot, (filePath) => {
    if (!filePath.endsWith(".resource")) {
      return;
    }
    const relativePath = path.relative(projectRoot, filePath).replace(/\\/g, "/");
    const content = fs.readFileSync(filePath, "utf8");
    content.split(/\r?\n/).forEach((lineText, index) => {
      const match = lineText.match(/^\s*function\s+(.+?)\s*\((.*?)\)\s+do\s*$/);
      if (!match) {
        return;
      }
      const name = match[1].trim();
      definitions.push({
        name,
        sourceType: "resource",
        path: path.join(projectRoot, relativePath),
        line: index + 1,
        column: Math.max(1, lineText.indexOf("function") + 1),
        module: "",
        parameters: parseResourceParameters(match[2]),
      });
    });
  });

  const payload = { definitions };
  resourceDefinitionCache.set(projectRoot, {
    timestamp: Date.now(),
    payload,
  });
  return payload;
}

function parseResourceParameters(rawParameters) {
  return String(rawParameters || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const [namePart, defaultPart] = item.split("=", 2);
      const param = {
        name: namePart.trim(),
        mapping: namePart.trim(),
        description: `自定义关键字参数 ${namePart.trim()}`,
      };
      if (defaultPart !== undefined) {
        param.default = defaultPart.trim();
      }
      return param;
    });
}

function runPythonDefinitionQuery(projectRoot) {
  return new Promise((resolve, reject) => {
    const baseEnv = withPythonProcessEnv(process.env);
    const targets = resolvePythonTargets(projectRoot, baseEnv);
    const envs = pythonQueryEnvs();

    const tryTarget = (targetIndex, envIndex = 0) => {
      const target = targets[targetIndex];
      execFile(
        target.command,
        [
          ...target.args,
          "-c",
          PYTHON_DEFINITION_SCRIPT,
          projectRoot,
        ],
        {
          cwd: projectRoot,
          env: envs[envIndex],
          timeout: PYTHON_TIMEOUT_MS,
          maxBuffer: PYTHON_MAX_BUFFER,
        },
        (error, stdout, stderr) => {
          if (error && error.code === "ENOENT" && targetIndex + 1 < targets.length) {
            tryTarget(targetIndex + 1, envIndex);
            return;
          }
          if (error && shouldRetryWithDevPythonPath(stderr) && envIndex + 1 < envs.length) {
            tryTarget(0, envIndex + 1);
            return;
          }
          if (error) {
            reject(new Error(definitionErrorMessage(error, stderr)));
            return;
          }

          try {
            resolve(JSON.parse(stdout));
          } catch (parseError) {
            reject(new Error(
              `Unable to parse pytest-dsl definition output: ${parseError.message}`,
            ));
          }
        },
      );
    };

    tryTarget(0, 0);
  });
}

function pythonQueryEnvs() {
  const envs = [withPythonProcessEnv(process.env)];
  if (isDirectory(path.join(REPO_ROOT, "pytest_dsl"))) {
    envs.push(devPythonPathEnv());
  }
  return envs;
}

function devPythonPathEnv() {
  const baseEnv = withPythonProcessEnv(process.env);
  const existing = baseEnv.PYTHONPATH || "";
  return mergeEnvironment(baseEnv, {
    PYTHONPATH: existing ? `${REPO_ROOT}${path.delimiter}${existing}` : REPO_ROOT,
  });
}

function isDirectory(directory) {
  try {
    return fs.statSync(directory).isDirectory();
  } catch {
    return false;
  }
}

function shouldRetryWithDevPythonPath(stderr) {
  return /No module named ['"]pytest_dsl['"]/.test(String(stderr || ""));
}

function definitionErrorMessage(error, stderr) {
  const detail = String(stderr || "").trim();
  if (detail) {
    return `Unable to load pytest-dsl keyword definitions: ${detail}`;
  }
  return `Unable to load pytest-dsl keyword definitions: ${error.message}`;
}

function assertProjectRoot(projectRoot) {
  const root = path.resolve(String(projectRoot || ""));
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
    throw new Error(`Project root does not exist: ${projectRoot}`);
  }
  return root;
}

function walk(directory, onFile) {
  const entries = fs.readdirSync(directory, { withFileTypes: true })
    .sort((left, right) => left.name.localeCompare(right.name));

  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (!IGNORED_DIRS.has(entry.name)) {
        walk(fullPath, onFile);
      }
      continue;
    }
    if (entry.isFile()) {
      onFile(fullPath);
    }
  }
}

function prefetchDefinitionCache(projectRoot) {
  if (!projectRoot) return;
  const cached = getCachedDefinitions(projectRoot);
  if (cached) return;
  listKeywordDefinitions({ projectRoot }).catch(() => {
    // Silently ignore prefetch failures — cache will populate on first user request
  });
}

function getCachedDefinitions(projectRoot) {
  const entry = definitionFullCache.get(projectRoot);
  if (entry && Date.now() - entry.timestamp < DEFINITION_CACHE_TTL_MS) {
    return entry.payload;
  }
  return null;
}

function setCachedDefinitions(projectRoot, payload) {
  definitionFullCache.set(projectRoot, {
    timestamp: Date.now(),
    payload,
  });
}

function invalidateDefinitionCache(projectRoot) {
  if (projectRoot) {
    definitionFullCache.delete(projectRoot);
    resourceDefinitionCache.delete(projectRoot);
  } else {
    definitionFullCache.clear();
    resourceDefinitionCache.clear();
  }
}

module.exports = {
  findKeywordDefinitions,
  listKeywordDefinitions,
  normalizeDefinitionPayload,
  prefetchDefinitionCache,
  readSourceFile,
  scanResourceDefinitions,
  invalidateDefinitionCache,
};
