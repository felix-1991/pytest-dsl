const fs = require("node:fs");
const path = require("node:path");

const { readMetadata } = require("./metadataStore");

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
        `Configured Python executable does not exist: ${configured}. ` +
        "Choose a Python interpreter in Configuration > Runtime.",
      );
    }
    return [pythonTarget(configured, [], "project-config", true)];
  }

  const targets = [];
  addTarget(targets, normalizedEnv.PYTEST_DSL_PYTHON, [], "environment");
  addTarget(targets, normalizedEnv.PYTHON, [], "environment");

  const venvPython = findProjectVenvPython(projectRoot, platform);
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

function findProjectVenvPython(projectRoot, platform = process.platform) {
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

  return candidates.find((candidate) => isUsableFile(candidate, platform)) || null;
}

function isExecutableAvailable(command, env = process.env, platform = process.platform) {
  const normalized = normalizeCommand(command);
  if (!normalized) {
    return false;
  }

  if (isPathCommand(normalized)) {
    return isUsableFile(normalized, platform);
  }

  const normalizedEnv = env && typeof env === "object" ? env : {};
  const pathValue = normalizedEnv.PATH || normalizedEnv.Path || normalizedEnv.path || "";
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
      isUsableFile(path.join(directory, name), platform)
    )));
}

function executableNames(command, env, platform) {
  if (platform !== "win32") {
    return [command];
  }
  if (path.win32.extname(command)) {
    return [command];
  }

  const extensions = String(env.PATHEXT || ".EXE;.CMD;.BAT;.COM")
    .split(";")
    .map((extension) => extension.trim())
    .filter(Boolean);
  const names = [command];
  for (const extension of extensions) {
    names.push(`${command}${extension}`);
    names.push(`${command}${extension.toLowerCase()}`);
    names.push(`${command}${extension.toUpperCase()}`);
  }
  return [...new Set(names)];
}

function isPathCommand(command) {
  return path.isAbsolute(command) ||
    path.win32.isAbsolute(command) ||
    command.includes("/") ||
    command.includes("\\");
}

function isUsableFile(filePath, platform) {
  try {
    if (!fs.statSync(filePath).isFile()) {
      return false;
    }
    if (platform !== "win32") {
      fs.accessSync(filePath, fs.constants.X_OK);
    }
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
    const command = platform === "win32" ? target.command.toLowerCase() : target.command;
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
  resolvePythonCommand,
  resolvePythonCommands,
  resolvePythonTarget,
  resolvePythonTargets,
};
