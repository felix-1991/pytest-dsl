const fs = require("node:fs");
const path = require("node:path");

const { readMetadata } = require("./metadataStore");

const WINDOWS_CANONICAL_ENV_KEYS = new Map([
  ["path", "PATH"],
  ["pathext", "PATHEXT"],
  ["pythonpath", "PYTHONPATH"],
]);

function mergeEnvironment(base = {}, overrides = {}, platform = process.platform) {
  const normalizedBase = base && typeof base === "object" ? base : {};
  const normalizedOverrides = overrides && typeof overrides === "object" ? overrides : {};
  if (platform !== "win32") {
    return { ...normalizedBase, ...normalizedOverrides };
  }

  const merged = {};
  for (const [key, value] of [
    ...Object.entries(normalizedBase),
    ...Object.entries(normalizedOverrides),
  ]) {
    const normalizedKey = key.toLowerCase();
    for (const existingKey of Object.keys(merged)) {
      if (existingKey.toLowerCase() === normalizedKey) {
        delete merged[existingKey];
      }
    }
    merged[WINDOWS_CANONICAL_ENV_KEYS.get(normalizedKey) || key] = value;
  }
  return merged;
}

function resolvePythonCommand(projectRoot, env = process.env, options = {}) {
  const commands = resolvePythonCommands(projectRoot, env, options);
  return options && options.all ? commands : commands[0];
}

function resolvePythonCommands(projectRoot, env = process.env, options = {}) {
  const normalizedEnv = env && typeof env === "object" ? env : {};
  const normalizedOptions = normalizeOptions(options);
  const targets = resolvePythonTargets(projectRoot, normalizedEnv, normalizedOptions);
  const configured = targets.find((target) => target.configured);
  if (configured) {
    return [configured.command];
  }

  const environmentCommand = normalizeCommand(normalizedEnv.PYTEST_DSL_PYTHON) ||
    normalizeCommand(normalizedEnv.PYTHON);
  if (environmentCommand) {
    return [environmentCommand];
  }

  const venv = targets.find((target) => target.source === "project-venv");
  return [venv && venv.command, "python", "python3"].filter(Boolean);
}

function resolvePythonTarget(projectRoot, env = process.env, options = {}) {
  const normalizedOptions = normalizeOptions(options);
  const platform = normalizedOptions.platform || process.platform;
  const targets = resolvePythonTargets(projectRoot, env, normalizedOptions);
  const selected = targets.find((target) => (
    isExecutableAvailable(target.command, env, platform)
  ));

  if (selected) {
    return selected;
  }

  const checked = targets
    .map((target) => [target.command, ...target.args].join(" "))
    .join(", ");
  throw new Error(
    `No usable Python executable was found. Checked: ${checked}. ` +
    "Choose a Python interpreter in Configuration > Runtime.",
  );
}

function resolvePythonTargets(projectRoot, env = process.env, options = {}) {
  const normalizedEnv = env && typeof env === "object" ? env : {};
  const normalizedOptions = normalizeOptions(options);
  const platform = normalizedOptions.platform || process.platform;
  const configured = configuredPython(projectRoot, normalizedOptions);

  if (configured) {
    if (!isExecutableAvailable(configured, normalizedEnv, platform)) {
      throw new Error(
        `Configured Python executable does not exist or is not executable: ${configured}. ` +
        "Choose a Python interpreter in Configuration > Runtime.",
      );
    }
    return [pythonTarget(configured, [], "project-config", true)];
  }

  const targets = [];
  addTarget(targets, normalizedEnv.PYTEST_DSL_PYTHON, [], "environment");
  addTarget(targets, normalizedEnv.PYTHON, [], "environment");

  const venvPython = findProjectVenvPython(projectRoot, platform, normalizedEnv);
  addTarget(targets, venvPython, [], "project-venv");

  if (platform === "win32") {
    addTarget(targets, "python", [], "path");
    addTarget(targets, "py", ["-3"], "path");
  } else {
    addTarget(targets, "python3", [], "path");
    addTarget(targets, "python", [], "path");
  }

  return dedupeTargets(targets, platform);
}

function configuredPython(projectRoot, options) {
  if (Object.prototype.hasOwnProperty.call(options, "pythonExecutable")) {
    return normalizeCommand(options.pythonExecutable);
  }
  if (!projectRoot) {
    return null;
  }
  const metadata = readMetadata(projectRoot);
  return normalizeCommand(metadata && metadata.runtime && metadata.runtime.pythonExecutable);
}

function findProjectVenvPython(projectRoot, platform = process.platform, env = process.env) {
  if (!projectRoot) {
    return null;
  }

  const root = path.resolve(projectRoot);
  const candidates = platform === "win32"
    ? [
        path.join(root, ".venv", "Scripts", "python.exe"),
        path.join(root, "venv", "Scripts", "python.exe"),
      ]
    : [
        path.join(root, ".venv", "bin", "python"),
        path.join(root, "venv", "bin", "python"),
      ];

  return candidates.find((candidate) => isUsableFile(candidate, platform, env)) || null;
}

function isExecutableAvailable(command, env = process.env, platform = process.platform) {
  const normalized = normalizeCommand(command);
  if (!normalized) {
    return false;
  }

  const normalizedEnv = env && typeof env === "object" ? env : {};
  if (isPathCommand(normalized)) {
    return isUsableFile(normalized, platform, normalizedEnv);
  }

  const pathValue = environmentValue(normalizedEnv, "PATH");
  if (!pathValue) {
    return false;
  }

  const delimiter = platform === "win32" ? ";" : path.delimiter;
  const names = executableNames(normalized, normalizedEnv, platform);
  return String(pathValue)
    .split(delimiter)
    .map((directory) => directory.trim())
    .filter(Boolean)
    .some((directory) => names.some((name) => (
      isUsableFile(path.join(directory, name), platform, normalizedEnv)
    )));
}

function executableNames(command, env, platform) {
  if (platform !== "win32") {
    return [command];
  }
  const extensions = windowsExecutableExtensions(env);
  const commandExtension = normalizeWindowsExtension(path.win32.extname(command));
  if (commandExtension) {
    return extensions.includes(commandExtension) ? [command] : [];
  }

  const names = [];
  for (const extension of extensions) {
    names.push(`${command}${extension}`);
    names.push(`${command}${extension.toUpperCase()}`);
  }
  return [...new Set(names)];
}

function windowsExecutableExtensions(env) {
  const pathExt = environmentValue(env, "PATHEXT") || ".EXE;.CMD;.BAT;.COM";
  return [...new Set(String(pathExt)
    .split(";")
    .map(normalizeWindowsExtension)
    .filter(Boolean))];
}

function normalizeWindowsExtension(extension) {
  const normalized = String(extension || "").trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  return normalized.startsWith(".") ? normalized : `.${normalized}`;
}

function environmentValue(env, name) {
  const expected = name.toLowerCase();
  const entry = Object.entries(env).find(([key, value]) => (
    key.toLowerCase() === expected && value !== null && value !== undefined && value !== ""
  ));
  return entry ? entry[1] : "";
}

function isPathCommand(command) {
  return path.isAbsolute(command) ||
    path.win32.isAbsolute(command) ||
    command.includes("/") ||
    command.includes("\\");
}

function isUsableFile(filePath, platform, env = process.env) {
  try {
    if (!fs.statSync(filePath).isFile()) {
      return false;
    }
    if (platform === "win32") {
      const extension = normalizeWindowsExtension(path.win32.extname(filePath));
      return Boolean(extension && windowsExecutableExtensions(env).includes(extension));
    }
    fs.accessSync(filePath, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function addTarget(targets, command, args, source) {
  const normalized = normalizeCommand(command);
  if (normalized) {
    targets.push(pythonTarget(normalized, args, source, false));
  }
}

function pythonTarget(command, args, source, configured) {
  return {
    command,
    args: [...args],
    source,
    configured,
  };
}

function dedupeTargets(targets, platform) {
  const seen = new Set();
  return targets.filter((target) => {
    const command = platform === "win32"
      ? path.win32.normalize(target.command).toLowerCase()
      : target.command;
    const key = JSON.stringify([command, target.args]);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function normalizeCommand(value) {
  if (value === null || value === undefined) {
    return null;
  }
  return String(value).trim() || null;
}

function normalizeOptions(options) {
  return options && typeof options === "object" ? options : {};
}

module.exports = {
  isExecutableAvailable,
  mergeEnvironment,
  resolvePythonCommand,
  resolvePythonCommands,
  resolvePythonTarget,
  resolvePythonTargets,
};
