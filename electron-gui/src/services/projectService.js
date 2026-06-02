const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { TextDecoder } = require("node:util");

const { loadProjectConfig } = require("./configService");
const { readMetadata, recordOpenedFile } = require("./metadataStore");

const UTF8_DECODER = new TextDecoder("utf-8", { fatal: true });

const IGNORED_DIRS = new Set([
  ".git",
  ".pytest-dsl-gui",
  ".venv",
  "__pycache__",
  "node_modules",
  "dist",
  "build",
  ".pytest_cache"
]);

function getProjectSnapshot(projectRoot) {
  const root = assertProjectRoot(projectRoot);
  const config = loadProjectConfig(root);
  const editableFiles = listEditableFiles(root);
  const dslFiles = editableFiles.filter((file) => file.language === "dsl");
  const metadata = readMetadata(root);
  const git = detectGit(root);

  return {
    project: {
      rootPath: root,
      name: path.basename(root),
      openedAt: new Date().toISOString()
    },
    git,
    score: calculateScore(dslFiles, config),
    editableFiles,
    dslFiles,
    config,
    metadata
  };
}

function getProjectConfigSnapshot(projectRoot) {
  const root = assertProjectRoot(projectRoot);
  const config = loadProjectConfig(root);

  return {
    project: {
      rootPath: root,
      name: path.basename(root),
      scannedAt: new Date().toISOString()
    },
    config
  };
}

function readProjectFile(projectRoot, relativePath) {
  const root = assertProjectRoot(projectRoot);
  const target = resolveProjectFile(root, relativePath);
  assertEditableTextFile(target, relativePath);
  const normalized = normalizeRelative(relativePath);
  const content = fs.readFileSync(target, "utf8");
  const metadata = recordOpenedFile(root, normalized);

  return {
    relativePath: normalized,
    content,
    language: detectLanguage(normalized),
    metadata
  };
}

function saveProjectFile(projectRoot, relativePath, content) {
  const root = assertProjectRoot(projectRoot);
  const normalized = normalizeRelative(relativePath);
  const target = resolveProjectFile(root, normalized);
  if (fs.existsSync(target)) {
    assertEditableTextFile(target, normalized);
  }
  assertTextContent(content, normalized);

  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
  const metadata = recordOpenedFile(root, normalized);

  return {
    relativePath: normalized,
    language: detectLanguage(normalized),
    bytes: Buffer.byteLength(content, "utf8"),
    metadata
  };
}

function assertProjectRoot(projectRoot) {
  if (!projectRoot) {
    throw new Error("projectRoot is required");
  }
  const root = path.resolve(projectRoot);
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
    throw new Error(`Project root does not exist: ${projectRoot}`);
  }
  return root;
}

function resolveProjectFile(projectRoot, relativePath) {
  const normalized = normalizeRelative(relativePath);
  const target = path.resolve(projectRoot, normalized);
  const rootWithSep = `${path.resolve(projectRoot)}${path.sep}`;
  if (target !== path.resolve(projectRoot) && !target.startsWith(rootWithSep)) {
    throw new Error(`File path is outside project root: ${relativePath}`);
  }
  return target;
}

function normalizeRelative(relativePath) {
  return String(relativePath || "").replace(/\\/g, "/");
}

function assertEditableTextFile(filePath, relativePath) {
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    throw new Error(`Editable file does not exist: ${relativePath}`);
  }
  const content = readTextFileContent(filePath);
  if (content === null) {
    throw new Error(`Only non-binary text files are editable: ${relativePath}`);
  }
}

function assertTextContent(content, relativePath) {
  if (typeof content !== "string" || content.includes("\u0000")) {
    throw new Error(`Only text content can be saved: ${relativePath}`);
  }
}

function listDslFiles(projectRoot) {
  return listEditableFiles(projectRoot).filter((file) => file.language === "dsl");
}

function listEditableFiles(projectRoot) {
  const files = [];
  walk(projectRoot, (filePath, stats) => {
    const content = readTextFileContent(filePath);
    if (content === null) {
      return;
    }

    const relativePath = path.relative(projectRoot, filePath).replace(/\\/g, "/");
    files.push({
      relativePath,
      name: path.basename(filePath),
      directory: path.dirname(relativePath) === "." ? "" : path.dirname(relativePath).replace(/\\/g, "/"),
      language: detectLanguage(relativePath),
      size: stats.size,
      lineCount: countLines(content)
    });
  });

  return files.sort((left, right) => left.relativePath.localeCompare(right.relativePath));
}

function readTextFileContent(filePath) {
  const buffer = fs.readFileSync(filePath);
  if (!isTextBuffer(buffer)) {
    return null;
  }
  return buffer.toString("utf8");
}

function isTextBuffer(buffer) {
  if (buffer.includes(0)) {
    return false;
  }
  try {
    UTF8_DECODER.decode(buffer);
    return true;
  } catch {
    return false;
  }
}

function detectLanguage(relativePath) {
  const name = relativePath.toLowerCase();
  if (name.endsWith(".dsl")) return "dsl";
  if (name.endsWith(".resource")) return "resource";
  if (name.endsWith(".yaml") || name.endsWith(".yml")) return "yaml";
  if (name.endsWith(".py")) return "python";
  if (name.endsWith(".md") || name.endsWith(".markdown")) return "markdown";
  return "plain";
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
      onFile(fullPath, fs.statSync(fullPath));
    }
  }
}

function countLines(content) {
  if (!content) {
    return 0;
  }
  return content.endsWith("\n")
    ? content.split("\n").length - 1
    : content.split("\n").length;
}

function detectGit(projectRoot) {
  try {
    execFileSync("git", ["-C", projectRoot, "rev-parse", "--is-inside-work-tree"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"]
    });
    const branch = execFileSync("git", ["-C", projectRoot, "branch", "--show-current"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"]
    }).trim();

    if (branch) {
      return { isGit: true, branch, displayName: branch };
    }

    const revision = execFileSync("git", ["-C", projectRoot, "rev-parse", "--short", "HEAD"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"]
    }).trim();
    return { isGit: true, branch: null, displayName: revision || "git" };
  } catch {
    return { isGit: false, branch: null, displayName: "local" };
  }
}

function calculateScore(dslFiles, config) {
  const deductions = [];
  const defaultSources = config.sources.filter((source) => source.defaultSelected);
  const defaultPaths = defaultSources.map((source) => source.relativePath);
  const selectedConfigCount = defaultSources.length;
  const selectedErrors = config.errors.filter((error) => (
    defaultPaths.includes(error.relativePath)
  ));

  if (dslFiles.length === 0) {
    deductions.push({ reason: "No DSL files found", points: 20 });
  }
  if (selectedConfigCount === 0) {
    deductions.push({ reason: "No config YAML files found", points: 15 });
  }
  if (selectedErrors.length > 0) {
    deductions.push({
      reason: "Config parse errors",
      points: Math.min(selectedErrors.length * 10, 30)
    });
  }

  const value = Math.max(0, 100 - deductions.reduce((total, item) => total + item.points, 0));
  return { value, deductions };
}

module.exports = {
  getProjectConfigSnapshot,
  getProjectSnapshot,
  readProjectFile,
  saveProjectFile,
  listEditableFiles,
  listDslFiles,
  detectGit,
  calculateScore,
  resolveProjectFile
};
