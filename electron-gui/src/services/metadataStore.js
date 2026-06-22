const fs = require("node:fs");
const path = require("node:path");

const METADATA_DIR = ".pytest-dsl-gui";
const METADATA_FILE = "metadata.json";

function metadataPath(projectRoot) {
  return path.join(projectRoot, METADATA_DIR, METADATA_FILE);
}

function defaultRuntimeMetadata() {
  return {
    pythonExecutable: null,
    allureExecutable: null
  };
}

function normalizeRuntimeMetadata(value) {
  const normalizeExecutable = (executable) => {
    if (typeof executable !== "string") {
      return null;
    }
    return executable.trim() || null;
  };

  return {
    pythonExecutable: normalizeExecutable(value && value.pythonExecutable),
    allureExecutable: normalizeExecutable(value && value.allureExecutable)
  };
}

function defaultMetadata() {
  return {
    version: 1,
    lastOpenedFile: null,
    recentFiles: [],
    layout: {
      leftWidth: 308,
      rightWidth: 392
    },
    runtime: defaultRuntimeMetadata(),
    updatedAt: null
  };
}

function readMetadata(projectRoot) {
  const filePath = metadataPath(projectRoot);
  if (!fs.existsSync(filePath)) {
    return defaultMetadata();
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, "utf8"));
    return normalizeMetadata(parsed);
  } catch {
    return defaultMetadata();
  }
}

function writeMetadata(projectRoot, metadata) {
  const filePath = metadataPath(projectRoot);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const normalized = normalizeMetadata({
    ...metadata,
    updatedAt: new Date().toISOString()
  });
  fs.writeFileSync(filePath, `${JSON.stringify(normalized, null, 2)}\n`, "utf8");
  return normalized;
}

function recordOpenedFile(projectRoot, relativePath) {
  const current = readMetadata(projectRoot);
  const recentFiles = [
    relativePath,
    ...current.recentFiles.filter((item) => item !== relativePath)
  ].slice(0, 10);

  return writeMetadata(projectRoot, {
    ...current,
    lastOpenedFile: relativePath,
    recentFiles
  });
}

function updateRuntimeMetadata(projectRoot, updates) {
  const current = readMetadata(projectRoot);
  const runtimeUpdates = updates && typeof updates === "object" ? updates : {};
  const runtime = { ...current.runtime };

  for (const field of ["pythonExecutable", "allureExecutable"]) {
    if (Object.prototype.hasOwnProperty.call(runtimeUpdates, field)) {
      runtime[field] = runtimeUpdates[field];
    }
  }

  return writeMetadata(projectRoot, {
    ...current,
    runtime
  });
}

function normalizeMetadata(value) {
  const base = defaultMetadata();
  const layout = value && typeof value.layout === "object" ? value.layout : {};
  return {
    ...base,
    ...(value && typeof value === "object" ? value : {}),
    version: 1,
    recentFiles: Array.isArray(value && value.recentFiles) ? value.recentFiles : [],
    layout: {
      ...base.layout,
      ...layout
    },
    runtime: normalizeRuntimeMetadata(value && value.runtime)
  };
}

module.exports = {
  METADATA_DIR,
  metadataPath,
  readMetadata,
  writeMetadata,
  recordOpenedFile,
  updateRuntimeMetadata
};
