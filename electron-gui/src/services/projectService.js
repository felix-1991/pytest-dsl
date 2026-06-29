const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { TextDecoder } = require("node:util");

const { loadProjectConfig } = require("./configService");
const {
  readMetadata,
  recordOpenedFile,
  updateConfigSelectionMetadata
} = require("./metadataStore");
const {
  buildSuiteTree,
  discoverConventionSuites
} = require("./suiteService");

const UTF8_DECODER = new TextDecoder("utf-8", { fatal: true });

const IGNORED_DIRS = new Set([
  ".git",
  ".pytest-dsl-gui",
  ".pytest-dsl-generated",
  ".venv",
  "__pycache__",
  "node_modules",
  "dist",
  "build",
  ".pytest_cache"
]);

function getProjectSnapshot(projectRoot) {
  const root = assertProjectRoot(projectRoot);
  const metadata = readMetadata(root);
  const config = loadProjectConfig(root, {
    selectedPaths: metadata.config.selectedPaths
  });
  const tree = buildProjectTree(root);
  const editableFiles = flattenProjectTreeFiles(tree);
  const dslFiles = editableFiles.filter((file) => file.language === "dsl");
  const git = detectGit(root);
  const suites = discoverConventionSuites(root);
  const suiteTree = buildSuiteTree(suites);

  return {
    project: {
      rootPath: root,
      name: path.basename(root),
      openedAt: new Date().toISOString()
    },
    git,
    score: calculateScore(dslFiles, config),
    tree,
    editableFiles,
    dslFiles,
    suites,
    suiteTree,
    config,
    metadata
  };
}

function getProjectConfigSnapshot(projectRoot) {
  const root = assertProjectRoot(projectRoot);
  const metadata = readMetadata(root);
  const config = loadProjectConfig(root, {
    selectedPaths: metadata.config.selectedPaths
  });

  return {
    project: {
      rootPath: root,
      name: path.basename(root),
      scannedAt: new Date().toISOString()
    },
    config
  };
}

function saveProjectConfigSelection(projectRoot, selectedPaths) {
  const root = assertProjectRoot(projectRoot);
  const config = loadProjectConfig(root, { selectedPaths });
  const metadata = updateConfigSelectionMetadata(root, config.selectedPaths);

  return { config, metadata };
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

function createProjectEntry(projectRoot, options = {}) {
  const root = assertProjectRoot(projectRoot);
  const kind = options.kind === "directory" ? "directory" : "file";
  const normalized = normalizeRelative(options.relativePath);
  assertMutableRelativePath(normalized);
  const target = resolveProjectFile(root, normalized);
  assertParentDirectoryExists(target, normalized);
  if (fs.existsSync(target)) {
    throw new Error(`Project entry already exists: ${normalized}`);
  }

  if (kind === "directory") {
    fs.mkdirSync(target);
  } else {
    const content = options.content || "";
    assertTextContent(content, normalized);
    fs.writeFileSync(target, content, "utf8");
  }

  return projectEntryResult(root, target);
}

function renameProjectEntry(projectRoot, options = {}) {
  const root = assertProjectRoot(projectRoot);
  const normalized = normalizeRelative(options.relativePath);
  assertMutableRelativePath(normalized);
  const newName = assertSimpleEntryName(options.newName);
  const source = resolveProjectFile(root, normalized);
  if (!fs.existsSync(source)) {
    throw new Error(`Project entry does not exist: ${normalized}`);
  }

  const targetRelative = normalizeRelative(path.join(path.dirname(normalized), newName));
  const target = resolveProjectFile(root, targetRelative);
  if (fs.existsSync(target)) {
    throw new Error(`Project entry already exists: ${targetRelative}`);
  }

  fs.renameSync(source, target);
  return projectEntryResult(root, target);
}

function moveProjectEntry(projectRoot, options = {}) {
  const root = assertProjectRoot(projectRoot);
  const normalized = normalizeRelative(options.relativePath);
  assertMutableRelativePath(normalized);
  const targetDirectory = normalizeRelative(options.targetDirectory || "");
  const targetDirectoryPath = resolveProjectFile(root, targetDirectory);
  if (!fs.existsSync(targetDirectoryPath) || !fs.statSync(targetDirectoryPath).isDirectory()) {
    throw new Error(`Target directory does not exist: ${targetDirectory || "."}`);
  }

  const source = resolveProjectFile(root, normalized);
  if (!fs.existsSync(source)) {
    throw new Error(`Project entry does not exist: ${normalized}`);
  }
  if (!fs.statSync(source).isFile()) {
    throw new Error(`Only files can be moved from the file tree: ${normalized}`);
  }

  const targetRelative = normalizeRelative(path.join(targetDirectory, path.basename(normalized)));
  const target = resolveProjectFile(root, targetRelative);
  if (target === source) {
    return {
      ...projectEntryResult(root, source),
      previousPath: normalized,
      moved: false
    };
  }
  if (fs.existsSync(target)) {
    throw new Error(`Project entry already exists: ${targetRelative}`);
  }

  fs.renameSync(source, target);
  return {
    ...projectEntryResult(root, target),
    previousPath: normalized,
    moved: true
  };
}

function deleteProjectEntry(projectRoot, options = {}) {
  const root = assertProjectRoot(projectRoot);
  const normalized = normalizeRelative(options.relativePath);
  assertMutableRelativePath(normalized);
  const target = resolveProjectFile(root, normalized);
  if (!fs.existsSync(target)) {
    throw new Error(`Project entry does not exist: ${normalized}`);
  }

  const stats = fs.statSync(target);
  if (stats.isDirectory() && fs.readdirSync(target).length > 0 && !options.recursive) {
    throw new Error(`Cannot delete non-empty directory without confirmation: ${normalized}`);
  }

  fs.rmSync(target, { recursive: stats.isDirectory(), force: false });
  return {
    kind: stats.isDirectory() ? "directory" : "file",
    relativePath: normalized,
    deleted: true
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

function assertMutableRelativePath(relativePath) {
  if (!relativePath || relativePath === ".") {
    throw new Error("Project root cannot be modified from the file tree");
  }
}

function assertSimpleEntryName(name) {
  const value = String(name || "").trim();
  if (!value) {
    throw new Error("Project entry name is required");
  }
  if (value === "." || value === ".." || value.includes("/") || value.includes("\\")) {
    throw new Error("Project entry name cannot contain path separators");
  }
  return value;
}

function assertParentDirectoryExists(target, relativePath) {
  const parent = path.dirname(target);
  if (!fs.existsSync(parent) || !fs.statSync(parent).isDirectory()) {
    throw new Error(`Parent directory does not exist: ${relativePath}`);
  }
}

function projectEntryResult(projectRoot, target) {
  const stats = fs.statSync(target);
  const relativePath = normalizeRelative(path.relative(projectRoot, target));
  if (stats.isDirectory()) {
    return {
      kind: "directory",
      relativePath
    };
  }

  const content = readTextFileContent(target);
  return {
    kind: "file",
    relativePath,
    language: detectLanguage(relativePath),
    bytes: stats.size,
    lineCount: content === null ? null : countLines(content)
  };
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
  const root = assertProjectRoot(projectRoot);
  return flattenProjectTreeFiles(buildProjectTree(root));
}

function buildProjectTree(projectRoot) {
  const root = assertProjectRoot(projectRoot);
  return buildDirectoryNode(root, "");
}

function buildDirectoryNode(projectRoot, relativePath) {
  const directory = relativePath ? path.join(projectRoot, relativePath) : projectRoot;
  const children = fs.readdirSync(directory, { withFileTypes: true })
    .sort(compareDirectoryEntries)
    .flatMap((entry) => {
      const childRelative = normalizeRelative(path.join(relativePath, entry.name));
      const childPath = path.join(projectRoot, childRelative);
      if (entry.isDirectory()) {
        if (IGNORED_DIRS.has(entry.name)) {
          return [];
        }
        return [buildDirectoryNode(projectRoot, childRelative)];
      }
      if (!entry.isFile()) {
        return [];
      }
      const content = readTextFileContent(childPath);
      if (content === null) {
        return [];
      }
      const stats = fs.statSync(childPath);
      return [{
        type: "file",
        path: childRelative,
        name: entry.name,
        language: detectLanguage(childRelative),
        size: stats.size,
        lineCount: countLines(content)
      }];
    });

  return {
    type: "directory",
    path: normalizeRelative(relativePath),
    name: relativePath ? path.basename(relativePath) : path.basename(projectRoot),
    fileCount: children.reduce((total, child) => (
      total + (child.type === "file" ? 1 : child.fileCount)
    ), 0),
    children
  };
}

function flattenProjectTreeFiles(tree) {
  const files = [];
  collectTreeFiles(tree, files);
  return files.sort((left, right) => left.relativePath.localeCompare(right.relativePath));
}

function collectTreeFiles(node, files) {
  if (!node) {
    return;
  }
  if (node.type === "file") {
    files.push({
      relativePath: node.path,
      name: node.name,
      directory: path.dirname(node.path) === "." ? "" : normalizeRelative(path.dirname(node.path)),
      language: node.language,
      size: node.size,
      lineCount: node.lineCount
    });
    return;
  }
  (node.children || []).forEach((child) => collectTreeFiles(child, files));
}

function compareDirectoryEntries(left, right) {
  if (left.isDirectory() !== right.isDirectory()) {
    return left.isDirectory() ? -1 : 1;
  }
  return left.name.localeCompare(right.name);
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
  createProjectEntry,
  deleteProjectEntry,
  getProjectConfigSnapshot,
  getProjectSnapshot,
  moveProjectEntry,
  readProjectFile,
  renameProjectEntry,
  saveProjectConfigSelection,
  saveProjectFile,
  buildProjectTree,
  listEditableFiles,
  listDslFiles,
  detectGit,
  calculateScore,
  resolveProjectFile
};
