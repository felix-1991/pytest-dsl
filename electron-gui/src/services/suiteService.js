const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const ROOT_SUITE_ID = "__root__";
const GENERATED_DIR_NAME = ".pytest-dsl-generated";
const HOOK_FILENAMES = new Set(["setup.dsl", "setup.auto", "teardown.dsl", "teardown.auto"]);
const DSL_EXTENSIONS = new Set([".dsl", ".auto"]);
const HELPER_DIRS = new Set(["_support", "_data"]);

function discoverConventionSuites(projectRoot) {
  const root = path.resolve(projectRoot);
  const testsRoot = path.join(root, "tests");
  if (!fs.existsSync(testsRoot) || !fs.statSync(testsRoot).isDirectory()) {
    return [];
  }

  const suites = new Map();
  for (const filePath of walkFiles(testsRoot)) {
    if (isGeneratedPath(filePath) || isHelperPath(filePath)) {
      continue;
    }
    const relativeToTests = normalizePath(path.relative(testsRoot, filePath));
    const suite = ensureSuite(suites, root, testsRoot, suiteIdFor(relativeToTests));
    const basename = path.basename(filePath);
    const extension = path.extname(filePath);

    if (DSL_EXTENSIONS.has(extension) && !HOOK_FILENAMES.has(basename)) {
      suite.dslCaseFiles.push(filePath);
    } else if (isPytestFile(basename)) {
      suite.pythonTestFiles.push(filePath);
    }
  }

  return [...suites.values()]
    .filter((suite) => suite.dslCaseFiles.length > 0 || suite.pythonTestFiles.length > 0)
    .sort((left, right) => compareSuiteIds(left.id, right.id))
    .map((suite) => toSuiteMetadata(suite, root));
}

function buildSuiteTree(suites = []) {
  const root = {
    type: "directory",
    path: "tests",
    name: "tests",
    suiteId: null,
    dslCaseCount: 0,
    pythonTestCount: 0,
    children: [],
  };

  for (const suite of Array.isArray(suites) ? suites : []) {
    if (suite.id === ROOT_SUITE_ID) {
      applySuiteToNode(root, suite);
      continue;
    }

    const parts = normalizePath(suite.id).split("/").filter(Boolean);
    let current = root;
    parts.forEach((part, index) => {
      const nodePath = parts.slice(0, index + 1).join("/");
      let child = current.children.find((item) => item.path === nodePath);
      if (!child) {
        child = {
          type: "directory",
          path: nodePath,
          name: part,
          suiteId: null,
          dslCaseCount: 0,
          pythonTestCount: 0,
          children: [],
        };
        current.children.push(child);
      }
      current = child;
    });
    applySuiteToNode(current, suite);
  }

  sortSuiteTree(root);
  return root;
}

function generatePytestFiles(projectRoot, selectedSuiteIds = []) {
  return [];
}

function buildPytestTargets(projectRoot, selectedSuiteIds = [], selectedFiles = null) {
  const root = path.resolve(projectRoot);
  const testsRoot = path.join(root, "tests");
  if (!fs.existsSync(testsRoot) || !fs.statSync(testsRoot).isDirectory()) {
    return [];
  }
  if (selectedFiles && Array.isArray(selectedFiles) && selectedFiles.length > 0) {
    return selectedFiles.map((f) => relativeToRoot(root, path.resolve(root, f)));
  }
  const selected = Array.isArray(selectedSuiteIds) ? selectedSuiteIds : [];
  if (selected.length === 0 || selected.includes("all")) {
    return [relativeToRoot(root, testsRoot)];
  }

  const targets = compactTargetPaths(
    selectedSuiteModels(root, selectedSuiteIds).map((suite) => suite.rootPath),
  );
  return targets.map((filePath) => relativeToRoot(root, filePath));
}

function selectedSuiteModels(projectRoot, selectedSuiteIds = []) {
  const root = path.resolve(projectRoot);
  const suites = discoverSuiteModels(root);
  const selected = Array.isArray(selectedSuiteIds) ? selectedSuiteIds : [];
  if (selected.length === 0) {
    return suites;
  }
  const selectedIds = selected.includes("all")
    ? new Set(suites.map((suite) => suite.id))
    : new Set(selected);
  return suites.filter((suite) => selectedIds.has(suite.id));
}

function discoverSuiteModels(projectRoot) {
  const root = path.resolve(projectRoot);
  const testsRoot = path.join(root, "tests");
  if (!fs.existsSync(testsRoot) || !fs.statSync(testsRoot).isDirectory()) {
    return [];
  }

  const suites = new Map();
  for (const filePath of walkFiles(testsRoot)) {
    if (isGeneratedPath(filePath) || isHelperPath(filePath)) {
      continue;
    }
    const relativeToTests = normalizePath(path.relative(testsRoot, filePath));
    const suite = ensureSuite(suites, root, testsRoot, suiteIdFor(relativeToTests));
    const basename = path.basename(filePath);
    const extension = path.extname(filePath);

    if (DSL_EXTENSIONS.has(extension) && !HOOK_FILENAMES.has(basename)) {
      suite.dslCaseFiles.push(filePath);
    } else if (isPytestFile(basename)) {
      suite.pythonTestFiles.push(filePath);
    }
  }

  return [...suites.values()]
    .filter((suite) => suite.dslCaseFiles.length > 0 || suite.pythonTestFiles.length > 0)
    .sort((left, right) => compareSuiteIds(left.id, right.id));
}

function ensureSuite(suites, projectRoot, testsRoot, suiteId) {
  if (!suites.has(suiteId)) {
    suites.set(suiteId, {
      id: suiteId,
      name: suiteId,
      rootPath: suiteId === ROOT_SUITE_ID ? testsRoot : path.join(testsRoot, suiteId),
      dslCaseFiles: [],
      pythonTestFiles: [],
      generatedFiles: [],
      diagnostics: [],
    });
  }
  return suites.get(suiteId);
}

function toSuiteMetadata(suite, projectRoot) {
  return {
    id: suite.id,
    name: suite.name,
    rootPath: relativeToRoot(projectRoot, suite.rootPath),
    dslCaseCount: suite.dslCaseFiles.length,
    pythonTestCount: suite.pythonTestFiles.length,
    dslCaseFiles: suite.dslCaseFiles.sort().map((filePath) => relativeToRoot(projectRoot, filePath)),
    generatedFiles: suite.generatedFiles.sort().map((filePath) => relativeToRoot(projectRoot, filePath)),
    pythonTestFiles: suite.pythonTestFiles.sort().map((filePath) => relativeToRoot(projectRoot, filePath)),
    diagnostics: [...suite.diagnostics],
  };
}

function makeTestFunctionName(caseName, usedNames) {
  const stem = path.basename(caseName, path.extname(caseName))
    .replace(/[^0-9a-zA-Z_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase() || "case";
  const safeStem = /^[0-9]/.test(stem) ? `case_${stem}` : stem;
  const baseName = `test_${safeStem}`;
  if (!usedNames.has(baseName)) {
    usedNames.add(baseName);
    return baseName;
  }
  const digest = crypto.createHash("sha1").update(caseName).digest("hex").slice(0, 8);
  const name = `${baseName}_${digest}`;
  usedNames.add(name);
  return name;
}

function suiteIdFor(relativeToTests) {
  const parts = normalizePath(relativeToTests).split("/").filter(Boolean);
  return parts.length <= 1 ? ROOT_SUITE_ID : parts.slice(0, -1).join("/");
}

function applySuiteToNode(node, suite) {
  node.suiteId = suite.id;
  node.rootPath = suite.rootPath;
  node.dslCaseCount = suite.dslCaseCount || 0;
  node.pythonTestCount = suite.pythonTestCount || 0;
  node.diagnostics = suite.diagnostics || [];

  if (!node.children) {
    node.children = [];
  }

  if (suite.dslCaseFiles) {
    suite.dslCaseFiles.forEach((file) => {
      node.children.push({
        type: "file",
        path: file,
        name: path.basename(file),
        suiteId: suite.id,
        filePath: file,
        fileType: "dsl"
      });
    });
  }

  if (suite.pythonTestFiles) {
    suite.pythonTestFiles.forEach((file) => {
      node.children.push({
        type: "file",
        path: file,
        name: path.basename(file),
        suiteId: suite.id,
        filePath: file,
        fileType: "python"
      });
    });
  }
}

function sortSuiteTree(node) {
  if (node.children) {
    node.children.sort((left, right) => {
      const leftIsDir = left.type === "directory";
      const rightIsDir = right.type === "directory";
      if (leftIsDir !== rightIsDir) {
        return leftIsDir ? -1 : 1;
      }
      return left.name.localeCompare(right.name);
    });
    node.children.forEach(sortSuiteTree);
  }
}

function isPytestFile(basename) {
  return /^test_.*\.py$/.test(basename) || /^.*_test\.py$/.test(basename);
}

function isGeneratedPath(filePath) {
  return normalizePath(filePath).split("/").includes(GENERATED_DIR_NAME);
}

function isHelperPath(filePath) {
  return normalizePath(filePath).split("/").some((part) => HELPER_DIRS.has(part));
}

function walkFiles(directory) {
  const files = [];
  if (!fs.existsSync(directory)) {
    return files;
  }
  for (const entry of fs.readdirSync(directory, { withFileTypes: true }).sort((left, right) => left.name.localeCompare(right.name))) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...walkFiles(fullPath));
    } else if (entry.isFile()) {
      files.push(fullPath);
    }
  }
  return files;
}

function compareSuiteIds(left, right) {
  if (left === ROOT_SUITE_ID) return right === ROOT_SUITE_ID ? 0 : -1;
  if (right === ROOT_SUITE_ID) return 1;
  return left.localeCompare(right);
}

function compactTargetPaths(paths) {
  const compacted = [];
  const unique = [...new Set(paths.map((filePath) => path.resolve(filePath)))].sort((left, right) => {
    const depthDiff = left.split(path.sep).length - right.split(path.sep).length;
    return depthDiff || normalizePath(left).localeCompare(normalizePath(right));
  });

  for (const target of unique) {
    if (compacted.some((selected) => isSameOrDescendant(target, selected))) {
      continue;
    }
    compacted.push(target);
  }
  return compacted;
}

function isSameOrDescendant(candidate, selected) {
  const relative = path.relative(selected, candidate);
  return relative === "" || (
    Boolean(relative) &&
    !relative.startsWith("..") &&
    !path.isAbsolute(relative)
  );
}

function relativeToRoot(root, filePath) {
  return normalizePath(path.relative(root, filePath));
}

function normalizePath(filePath) {
  return String(filePath || "").replace(/\\/g, "/");
}

module.exports = {
  ROOT_SUITE_ID,
  buildSuiteTree,
  buildPytestTargets,
  discoverConventionSuites,
  generatePytestFiles,
};
