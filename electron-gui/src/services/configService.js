const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const IGNORED_CONFIG_DIRS = new Set([
  ".git",
  ".pytest-dsl-gui",
  ".venv",
  "__pycache__",
  "node_modules",
  "dist",
  "build",
  ".pytest_cache"
]);

let yaml = null;
try {
  yaml = require("js-yaml");
} catch {
  yaml = null;
}

function loadProjectConfig(projectRoot) {
  const root = path.resolve(projectRoot);
  const configDir = path.join(root, "config");
  const sources = [];
  const errors = [];
  const files = listConfigFiles(root);

  for (const filePath of files) {
    const fileName = path.basename(filePath);
    const relativePath = path.relative(root, filePath).replace(/\\/g, "/");
    const raw = fs.readFileSync(filePath, "utf8");
    const defaultSelected = isDefaultConfigPath(relativePath);

    try {
      const data = parseYaml(raw) || {};
      sources.push({
        relativePath,
        fileName,
        defaultSelected,
        ok: true,
        data,
        raw
      });
    } catch (error) {
      const message = error && error.message ? error.message : String(error);
      sources.push({
        relativePath,
        fileName,
        defaultSelected,
        ok: false,
        data: null,
        raw,
        error: message
      });
      errors.push({ relativePath, message });
    }
  }

  const selectedPaths = sources
    .filter((source) => source.ok && source.defaultSelected)
    .map((source) => source.relativePath);
  const merged = mergeConfigSources(sources, selectedPaths);
  const signature = buildConfigSignature(sources);

  return { configDir, sources, selectedPaths, errors, merged, signature };
}

function buildConfigSignature(sources) {
  const hash = crypto.createHash("sha256");
  sources
    .slice()
    .sort((left, right) => left.relativePath.localeCompare(right.relativePath))
    .forEach((source) => {
      hash.update(source.relativePath);
      hash.update("\0");
      hash.update(source.ok ? "ok" : "error");
      hash.update("\0");
      hash.update(source.raw || "");
      hash.update("\0");
      hash.update(source.error || "");
      hash.update("\0");
    });
  return hash.digest("hex");
}

function listConfigFiles(projectRoot) {
  const files = [];
  walkConfigFiles(projectRoot, path.join(projectRoot, "config"), files);
  return files.sort((left, right) => {
    const leftRelative = path.relative(projectRoot, left).replace(/\\/g, "/");
    const rightRelative = path.relative(projectRoot, right).replace(/\\/g, "/");
    const leftDefault = isDefaultConfigPath(leftRelative);
    const rightDefault = isDefaultConfigPath(rightRelative);
    if (leftDefault !== rightDefault) {
      return leftDefault ? -1 : 1;
    }
    return leftRelative.localeCompare(rightRelative);
  });
}

function walkConfigFiles(projectRoot, directory, files) {
  if (!fs.existsSync(directory) || !fs.statSync(directory).isDirectory()) {
    return;
  }

  const entries = fs.readdirSync(directory, { withFileTypes: true })
    .sort((left, right) => left.name.localeCompare(right.name));

  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (!shouldSkipConfigDir(entry.name)) {
        walkConfigFiles(projectRoot, fullPath, files);
      }
      continue;
    }
    if (entry.isFile() && /\.(ya?ml)$/i.test(entry.name)) {
      files.push(fullPath);
    }
  }
}

function shouldSkipConfigDir(name) {
  return IGNORED_CONFIG_DIRS.has(name) || name.startsWith(".");
}

function isDefaultConfigPath(relativePath) {
  const parts = normalizeRelative(relativePath).split("/");
  return parts.length === 2 && parts[0] === "config" && /\.(ya?ml)$/i.test(parts[1]);
}

function mergeConfigSources(sources, selectedPaths = null) {
  const selectedSet = selectedPaths ? new Set(selectedPaths) : null;
  const merged = {};

  sources.forEach((source) => {
    if (!source.ok || !isPlainObject(source.data)) {
      return;
    }
    if (selectedSet && !selectedSet.has(source.relativePath)) {
      return;
    }
    Object.assign(merged, source.data);
  });

  return merged;
}

function normalizeRelative(relativePath) {
  return String(relativePath || "").replace(/\\/g, "/");
}

function parseYaml(raw) {
  if (yaml) {
    return yaml.load(raw);
  }
  return parseSimpleYaml(raw);
}

function parseSimpleYaml(raw) {
  const root = {};
  const stack = [{ indent: -1, value: root, parent: null, key: null, empty: false }];
  const lines = raw.replace(/\r\n/g, "\n").split("\n");

  lines.forEach((line, index) => {
    if (!line.trim() || line.trimStart().startsWith("#")) {
      return;
    }
    if (line.includes("\t")) {
      throw new Error(`Unsupported tab indentation at line ${index + 1}`);
    }

    const indent = line.match(/^ */)[0].length;
    if (indent % 2 !== 0) {
      throw new Error(`Invalid indentation at line ${index + 1}`);
    }

    const trimmed = stripInlineComment(line.trim());
    if (!trimmed) {
      return;
    }

    while (stack.length > 1 && stack[stack.length - 1].indent >= indent) {
      stack.pop();
    }

    let frame = stack[stack.length - 1];
    if (frame.empty && indent > frame.indent) {
      if (trimmed.startsWith("- ")) {
        const replacement = [];
        frame.parent[frame.key] = replacement;
        frame.value = replacement;
      }
      frame.empty = false;
    }

    frame = stack[stack.length - 1];
    const parent = frame.value;

    if (trimmed.startsWith("- ")) {
      if (!Array.isArray(parent)) {
        throw new Error(`List item without list parent at line ${index + 1}`);
      }
      const body = trimmed.slice(2).trim();
      const inlinePair = body.match(/^([^:]+):\s*(.*)$/);
      if (inlinePair) {
        const item = {};
        item[inlinePair[1].trim()] = parseScalar(inlinePair[2].trim());
        parent.push(item);
        stack.push({ indent, value: item, parent, key: parent.length - 1, empty: false });
      } else {
        parent.push(parseScalar(body));
      }
      return;
    }

    if (!isPlainObject(parent)) {
      throw new Error(`Mapping entry without map parent at line ${index + 1}`);
    }

    const pair = trimmed.match(/^([^:]+):\s*(.*)$/);
    if (!pair) {
      throw new Error(`Invalid YAML mapping at line ${index + 1}`);
    }

    const key = unquote(pair[1].trim());
    const rest = pair[2].trim();
    if (!rest) {
      const child = {};
      parent[key] = child;
      stack.push({ indent, value: child, parent, key, empty: true });
    } else {
      parent[key] = parseScalar(rest);
    }
  });

  return root;
}

function parseScalar(value) {
  if (value === "") return "";
  if (value === "true") return true;
  if (value === "false") return false;
  if (value === "null" || value === "None" || value === "~") return null;
  if (/^-?\d+(\.\d+)?$/.test(value)) return Number(value);
  if ((value.startsWith("\"") && value.endsWith("\"")) ||
      (value.startsWith("'") && value.endsWith("'"))) {
    return unquote(value);
  }
  return value;
}

function stripInlineComment(value) {
  let quote = null;
  for (let index = 0; index < value.length; index += 1) {
    const char = value[index];
    if ((char === "\"" || char === "'") && value[index - 1] !== "\\") {
      quote = quote === char ? null : (quote || char);
    }
    if (char === "#" && !quote && /\s/.test(value[index - 1] || " ")) {
      return value.slice(0, index).trimEnd();
    }
  }
  return value;
}

function unquote(value) {
  if ((value.startsWith("\"") && value.endsWith("\"")) ||
      (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1);
  }
  return value;
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

module.exports = {
  loadProjectConfig,
  listConfigFiles,
  mergeConfigSources,
  buildConfigSignature,
  parseYaml,
  parseSimpleYaml
};
