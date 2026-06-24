const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const SHELL_PATH_TIMEOUT_MS = 1000;
const SHELL_PATH_MAX_BUFFER = 8192;

const shellPathCache = new Map();

function runtimePathEntries(env = process.env, options = {}) {
  const normalizedEnv = isPlainObject(env) ? env : {};
  const platform = platformFor(options);
  const entries = [];

  appendPathValue(entries, environmentValue(normalizedEnv, "PATH", platform), platform);
  appendPathValue(entries, environmentValue(normalizedEnv, "PYTEST_DSL_RUNTIME_PATH", platform), platform);

  if (typeof options.shellPathProvider === "function") {
    appendPathValue(entries, options.shellPathProvider(normalizedEnv, platform), platform);
  } else if (shouldDiscoverShellPath(platform, options)) {
    appendPathValue(entries, discoverLoginShellPath(normalizedEnv), platform);
  }

  return dedupePathEntries(entries, platform);
}

function withRuntimePathEnv(env = process.env, options = {}) {
  const normalizedEnv = isPlainObject(env) ? env : {};
  const platform = platformFor(options);
  const entries = runtimePathEntries(normalizedEnv, options);
  if (!entries.length) {
    return { ...normalizedEnv };
  }
  const pathKey = pathEnvironmentKey(normalizedEnv, platform);
  return {
    ...normalizedEnv,
    [pathKey]: entries.join(pathDelimiter(platform)),
  };
}

function findExecutableInPath(command, env = process.env, options = {}) {
  const normalized = normalizeCommand(command);
  if (!normalized || isPathCommand(normalized)) {
    return isExecutableFile(normalized, env, platformFor(options)) ? normalized : null;
  }

  const platform = platformFor(options);
  const names = executableNames(normalized, env, platform);
  for (const directory of runtimePathEntries(env, options)) {
    for (const name of names) {
      const candidate = path.join(directory, name);
      if (isExecutableFile(candidate, env, platform)) {
        return candidate;
      }
    }
  }
  return null;
}

function isExecutableAvailable(command, env = process.env, options = {}) {
  const normalized = normalizeCommand(command);
  if (!normalized) {
    return false;
  }
  const platform = platformFor(options);
  if (isPathCommand(normalized)) {
    return isExecutableFile(normalized, env, platform);
  }
  return Boolean(findExecutableInPath(normalized, env, options));
}

function isExecutableFile(filePath, env = process.env, platform = process.platform) {
  const normalized = normalizeCommand(filePath);
  if (!normalized) {
    return false;
  }
  try {
    if (!fs.statSync(normalized).isFile()) {
      return false;
    }
    if (platform === "win32") {
      const extension = normalizeWindowsExtension(path.win32.extname(normalized));
      return Boolean(extension && windowsExecutableExtensions(env, platform).includes(extension));
    }
    fs.accessSync(normalized, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function executableNames(command, env = process.env, platform = process.platform) {
  const normalized = normalizeCommand(command);
  if (!normalized) {
    return [];
  }
  if (platform !== "win32") {
    return [normalized];
  }

  const extensions = windowsExecutableExtensions(env, platform);
  const commandExtension = normalizeWindowsExtension(path.win32.extname(normalized));
  if (commandExtension) {
    return extensions.includes(commandExtension) ? [normalized] : [];
  }

  const names = [];
  for (const extension of extensions) {
    names.push(`${normalized}${extension}`);
    names.push(`${normalized}${extension.toUpperCase()}`);
  }
  return [...new Set(names)];
}

function windowsExecutableExtensions(env = process.env, platform = process.platform) {
  const pathExt = environmentValue(env, "PATHEXT", platform) || ".EXE;.CMD;.BAT;.COM";
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

function environmentValue(env = process.env, name, platform = process.platform) {
  if (!isPlainObject(env)) {
    return "";
  }
  if (platform === "win32") {
    const expected = String(name).toLowerCase();
    const entry = Object.entries(env).find(([key, value]) => (
      key.toLowerCase() === expected && value !== null && value !== undefined && value !== ""
    ));
    return entry ? entry[1] : "";
  }
  const value = env[name];
  return value === null || value === undefined ? "" : value;
}

function pathEnvironmentKey(env = process.env, platform = process.platform) {
  if (!isPlainObject(env)) {
    return "PATH";
  }
  if (platform === "win32") {
    return "PATH";
  }
  return "PATH";
}

function pathDelimiter(platform = process.platform) {
  return platform === "win32" ? ";" : path.delimiter;
}

function shouldDiscoverShellPath(platform, options) {
  return platform !== "win32" &&
    !options.skipCommonPaths &&
    !options.skipShellPathDiscovery;
}

function discoverLoginShellPath(env = process.env) {
  for (const shell of shellCandidates(env)) {
    const home = environmentValue(env, "HOME", process.platform) || os.homedir() || process.cwd();
    const cacheKey = `${shell}\0${home}`;
    if (shellPathCache.has(cacheKey)) {
      const cached = shellPathCache.get(cacheKey);
      if (cached) {
        return cached;
      }
      continue;
    }
    try {
      const output = execFileSync(
        shell,
        ["-lc", "printf '%s' \"$PATH\""],
        {
          cwd: home,
          env: { ...process.env, ...env },
          encoding: "utf8",
          timeout: SHELL_PATH_TIMEOUT_MS,
          maxBuffer: SHELL_PATH_MAX_BUFFER,
          stdio: ["ignore", "pipe", "ignore"],
        },
      ).trim();
      shellPathCache.set(cacheKey, output);
      if (output) {
        return output;
      }
    } catch (_error) {
      shellPathCache.set(cacheKey, "");
    }
  }
  return "";
}

function shellCandidates(env = process.env) {
  const candidates = [];
  appendShellCandidate(candidates, environmentValue(env, "SHELL", process.platform));
  appendShellCandidate(candidates, process.env.SHELL);
  for (const shell of shellsFromEtc()) {
    appendShellCandidate(candidates, shell);
  }
  for (const shell of ["/bin/zsh", "/bin/bash", "/bin/sh"]) {
    appendShellCandidate(candidates, shell);
  }
  return candidates;
}

function shellsFromEtc() {
  try {
    return fs.readFileSync("/etc/shells", "utf8")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"));
  } catch (_error) {
    return [];
  }
}

function appendShellCandidate(candidates, shell) {
  const normalized = normalizeCommand(shell);
  if (!normalized || !path.isAbsolute(normalized)) {
    return;
  }
  if (!/^(?:ba|z|k|da)?sh$/.test(path.basename(normalized))) {
    return;
  }
  if (!isExecutableFile(normalized, process.env, process.platform)) {
    return;
  }
  if (!candidates.includes(normalized)) {
    candidates.push(normalized);
  }
}

function appendPathValue(entries, value, platform) {
  String(value || "")
    .split(pathDelimiter(platform))
    .map((entry) => entry.trim())
    .filter(Boolean)
    .forEach((entry) => entries.push(entry));
}

function dedupePathEntries(entries, platform) {
  const seen = new Set();
  return entries.filter((entry) => {
    const key = platform === "win32" ? entry.toLowerCase() : entry;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function isPathCommand(command) {
  return path.isAbsolute(command) ||
    path.win32.isAbsolute(command) ||
    command.includes("/") ||
    command.includes("\\");
}

function normalizeCommand(value) {
  if (value === null || value === undefined) {
    return null;
  }
  return String(value).trim() || null;
}

function platformFor(options = {}) {
  return options && options.platform ? options.platform : process.platform;
}

function isPlainObject(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

module.exports = {
  environmentValue,
  executableNames,
  findExecutableInPath,
  isExecutableAvailable,
  isExecutableFile,
  runtimePathEntries,
  withRuntimePathEnv,
};
