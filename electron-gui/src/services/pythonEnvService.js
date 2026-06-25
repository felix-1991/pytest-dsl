const path = require("node:path");
const { execFileSync } = require("node:child_process");

const { readMetadata } = require("./metadataStore");
const {
  findExecutableInPath,
  isExecutableAvailable: isRuntimeExecutableAvailable,
  isExecutableFile,
} = require("./runtimePathService");

const WINDOWS_CANONICAL_ENV_KEYS = new Map([
  ["path", "PATH"],
  ["pathext", "PATHEXT"],
  ["pythonpath", "PYTHONPATH"],
]);

const PYTHON_RUNTIME_PROBE_TIMEOUT_MS = 15000;
const PYTHON_RUNTIME_PROBE_SCRIPT = [
  "import sys",
  "if sys.version_info < (3, 9):",
  "    raise RuntimeError(f'Python 3.9 or newer is required; current Python is {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
  "import pytest, pytest_dsl",
  "print(sys.executable)",
].join("\n");
const PYTHON_PROCESS_ENV = {
  PYTHONUNBUFFERED: "1",
  PYTHONIOENCODING: "utf-8",
  PYTHONUTF8: "1",
};

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

function withPythonProcessEnv(env = {}, platform = process.platform) {
  return mergeEnvironment(env, PYTHON_PROCESS_ENV, platform);
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

  const venv = targets.find((target) => target.source === "project-venv");
  const environmentCommand = normalizeCommand(normalizedEnv.PYTEST_DSL_PYTHON) ||
    normalizeCommand(normalizedEnv.PYTHON);
  if (venv) {
    return [venv.command, environmentCommand].filter(Boolean);
  }
  if (environmentCommand) {
    return [environmentCommand];
  }

  return [venv && venv.command, "python", "python3"].filter(Boolean);
}

function resolvePythonTarget(projectRoot, env = process.env, options = {}) {
  const normalizedOptions = normalizeOptions(options);
  const platform = normalizedOptions.platform || process.platform;
  const targets = resolvePythonTargets(projectRoot, env, normalizedOptions);
  const selected = targets.find((target) => (
    isExecutableAvailable(target.command, env, normalizedOptions)
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

function resolvePythonRuntimeTarget(projectRoot, env = process.env, options = {}) {
  const normalizedOptions = normalizeOptions(options);
  let targets;
  try {
    targets = resolvePythonTargets(projectRoot, env, normalizedOptions);
  } catch (error) {
    const configured = configuredPython(projectRoot, normalizedOptions);
    throw pythonRuntimeUnavailableError([{
      target: pythonTarget(configured || "Python", [], "project-config", true),
      status: "not-executable",
      detail: error.message,
    }]);
  }
  const configured = targets.find((target) => target.configured);
  const candidates = configured ? targets.filter((target) => target.configured) : targets;
  const failures = [];

  for (const target of candidates) {
    if (!isExecutableAvailable(target.command, env, normalizedOptions)) {
      failures.push({ target, status: "not-executable", detail: "not executable" });
      continue;
    }
    const probe = runPythonRuntimeProbeSync(target, projectRoot, env, normalizedOptions);
    if (probe.status === "ok") {
      return {
        ...target,
        executable: probe.executable || target.command,
      };
    }
    failures.push({ target, ...probe });
  }

  throw pythonRuntimeUnavailableError(failures);
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
  const venvPythons = findProjectVenvPythons(projectRoot, platform, normalizedEnv);
  venvPythons.forEach((venvPython) => addTarget(targets, venvPython, [], "project-venv"));
  addTarget(targets, normalizedEnv.PYTEST_DSL_PYTHON, [], "environment");
  addTarget(targets, normalizedEnv.PYTHON, [], "environment");

  if (platform === "win32") {
    addPathTarget(targets, "python", [], normalizedEnv, normalizedOptions);
    addPathTarget(targets, "py", ["-3"], normalizedEnv, normalizedOptions);
  } else {
    addPathTarget(targets, "python3", [], normalizedEnv, normalizedOptions);
    addPathTarget(targets, "python", [], normalizedEnv, normalizedOptions);
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

function findProjectVenvPythons(projectRoot, platform = process.platform, env = process.env) {
  if (!projectRoot) {
    return [];
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

  return candidates.filter((candidate) => isExecutableFile(candidate, env, platform));
}

function addTarget(targets, command, args, source) {
  const normalized = normalizeCommand(command);
  if (normalized) {
    targets.push(pythonTarget(normalized, args, source, false));
  }
}

function addPathTarget(targets, command, args, env, options) {
  addTarget(
    targets,
    findExecutableInPath(command, env, options) || command,
    args,
    "path",
  );
}

function isExecutableAvailable(command, env = process.env, platformOrOptions = process.platform) {
  const options = typeof platformOrOptions === "object" && platformOrOptions !== null
    ? platformOrOptions
    : { platform: platformOrOptions };
  return isRuntimeExecutableAvailable(command, env, options);
}

function runPythonRuntimeProbeSync(target, projectRoot, env = process.env, options = {}) {
  const probeEnv = withPythonProcessEnv(
    env,
    normalizeOptions(options).platform || process.platform,
  );
  try {
    const stdout = execFileSync(
      target.command,
      [...target.args, "-c", PYTHON_RUNTIME_PROBE_SCRIPT],
      {
        cwd: projectRoot || process.cwd(),
        env: probeEnv,
        encoding: "utf8",
        timeout: options.pythonRuntimeProbeTimeoutMs || PYTHON_RUNTIME_PROBE_TIMEOUT_MS,
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    return { status: "ok", executable: String(stdout || "").trim().split(/\r?\n/).pop() };
  } catch (error) {
    const combined = `${error.stdout || ""}\n${error.stderr || ""}\n${error.message || ""}`;
    if (/Python 3\.9 or newer is required/i.test(combined)) {
      return { status: "version-unsupported", detail: singleLine(combined) };
    }
    if (/ModuleNotFoundError|ImportError|No module named/i.test(combined)) {
      return { status: "missing", detail: "pytest-dsl" };
    }
    return {
      status: "error",
      detail: singleLine(combined) || "Python probe failed",
      signal: error.signal || null,
      code: error.status === undefined ? error.code : error.status,
    };
  }
}

function pythonRuntimeUnavailableError(failures) {
  const first = failures.find((failure) => failure.status !== "not-executable") || failures[0] || {};
  const target = first.target ? [first.target.command, ...(first.target.args || [])].filter(Boolean).join(" ") : "Python";
  const detail = first.detail ? ` 当前检测到的问题: ${singleLine(first.detail)}。` : "";
  const error = new Error(
    `Python 运行环境不可用。需要 Python 3.9 及以上，并安装 pytest-dsl。请执行: pip install pytest-dsl。${detail}命令: ${target}`,
  );
  error.code = "PYTHON_RUNTIME_UNAVAILABLE";
  error.runtimeKind = "python";
  error.runtimeReason = first.status || "python-runtime-unavailable";
  error.checked = failures.map((failure) => ({
    command: failure.target && failure.target.command,
    args: failure.target && failure.target.args,
    status: failure.status,
    detail: failure.detail,
  }));
  return error;
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

function singleLine(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function normalizeOptions(options) {
  return options && typeof options === "object" ? options : {};
}

module.exports = {
  isExecutableAvailable,
  mergeEnvironment,
  resolvePythonCommand,
  resolvePythonCommands,
  resolvePythonRuntimeTarget,
  resolvePythonTarget,
  resolvePythonTargets,
  withPythonProcessEnv,
};
