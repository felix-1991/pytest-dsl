const fs = require("node:fs");
const path = require("node:path");
const { execFile } = require("node:child_process");

const { resolveAllureRuntime } = require("./allureEnvService");
const {
  mergeEnvironment,
  resolvePythonTargets,
} = require("./pythonEnvService");
const { readMetadata, updateRuntimeMetadata } = require("./metadataStore");

const PYTHON_PROBE_TIMEOUT_MS = 5000;
const PYTHON_PROBE_SCRIPT = "import pytest, pytest_dsl, sys; print(sys.executable)";

async function getRuntimeStatus(options = {}) {
  const projectRoot = assertProjectRoot(options.projectRoot);
  const env = runtimeEnv(options.env, options.platform);

  const [python, allure] = await Promise.all([
    probePythonStatus(projectRoot, env, options),
    probeAllureStatus(projectRoot, env, options),
  ]);

  return {
    projectRoot,
    config: readMetadata(projectRoot).runtime,
    python,
    allure,
  };
}

async function probePythonStatus(projectRoot, env, options) {
  let targets;
  try {
    targets = resolvePythonTargets(projectRoot, env, options);
  } catch (error) {
    // Configured python is missing or invalid
    const metadata = readMetadata(projectRoot);
    const configured = metadata.runtime.pythonExecutable;
    if (configured) {
      return {
        available: false,
        command: configured,
        args: [],
        source: "project-config",
        reason: "python-not-found",
        message: `Configured Python executable does not exist: ${configured}`,
      };
    }
    return {
      available: false,
      command: null,
      args: [],
      source: null,
      reason: "python-not-found",
      message: error.message,
    };
  }

  const configured = targets.find((target) => target.configured);
  const available = targets.find((target) => (
    isExecutablePathAvailable(target.command, env, options.platform)
  ));

  if (configured && !isExecutablePathAvailable(configured.command, env, options.platform)) {
    return {
      available: false,
      command: configured.command,
      args: configured.args,
      source: configured.source,
      reason: "python-not-found",
      message: `Configured Python executable does not exist: ${configured.command}`,
    };
  }

  if (!available) {
    return {
      available: false,
      command: null,
      args: [],
      source: null,
      reason: "python-not-found",
      message: "No Python executable was found. Choose one in Configuration > Runtime.",
    };
  }

  const probeResult = await runPythonDependencyProbe(available, projectRoot, env, options);
  if (probeResult.status === "missing") {
    return {
      available: false,
      command: available.command,
      args: available.args,
      source: available.source,
      reason: "python-dependency-missing",
      message: `Python is available but required dependencies are missing: ${probeResult.detail || "pytest or pytest_dsl"}`,
    };
  }
  if (probeResult.status === "error") {
    return {
      available: false,
      command: available.command,
      args: available.args,
      source: available.source,
      reason: "python-probe-failed",
      message: probeResult.detail || "Python probe failed",
    };
  }
  return {
    available: true,
    command: available.command,
    args: available.args,
    source: available.source,
    reason: null,
    message: probeResult.executable || available.command,
  };
}

function runPythonDependencyProbe(target, projectRoot, env, options) {
  if (typeof options.pythonDependencyProbe === "function") {
    return Promise.resolve(options.pythonDependencyProbe(target, projectRoot, env));
  }
  return runPythonProbeAsync(target, projectRoot, env, options);
}

function runPythonProbeAsync(target, projectRoot, env, options) {
  return new Promise((resolve) => {
    const child = execFile(
      target.command,
      [...target.args, "-c", PYTHON_PROBE_SCRIPT],
      {
        cwd: projectRoot,
        env,
        timeout: PYTHON_PROBE_TIMEOUT_MS,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        if (error) {
          const combined = `${stdout || ""}\n${stderr || ""}`;
          if (/ModuleNotFoundError|ImportError|No module named/i.test(combined)) {
            resolve({ status: "missing", detail: "pytest or pytest_dsl" });
            return;
          }
          if (error.signal) {
            resolve({
              status: "error",
              detail: `Python was terminated by signal ${error.signal}. This may be caused by macOS security restrictions or the Python binary being quarantined.`,
            });
            return;
          }
          resolve({ status: "error", detail: error.message });
          return;
        }
        const executable = (stdout || "").trim().split("\n").pop();
        resolve({ status: "ok", executable });
      },
    );
    child.on("error", (error) => {
      resolve({ status: "error", detail: error.message });
    });
  });
}

async function probeAllureStatus(projectRoot, env, options) {
  if (typeof options.allureRuntimeProbe === "function") {
    return options.allureRuntimeProbe(projectRoot, env, options);
  }
  return resolveAllureRuntime(projectRoot, env, options);
}

function saveRuntimeExecutable(projectRoot, kind, executablePath) {
  const root = assertProjectRoot(projectRoot);
  const field = runtimeField(kind);
  const normalized = path.normalize(String(executablePath || "").trim());
  if (!path.isAbsolute(normalized)) {
    throw new Error("Runtime executable must use an absolute path");
  }
  if (!fs.existsSync(normalized) || !fs.statSync(normalized).isFile()) {
    throw new Error(`Runtime executable does not exist: ${normalized}`);
  }
  return updateRuntimeMetadata(root, { [field]: normalized });
}

function resetRuntimeExecutable(projectRoot, kind) {
  const root = assertProjectRoot(projectRoot);
  return updateRuntimeMetadata(root, { [runtimeField(kind)]: null });
}

function runtimeField(kind) {
  if (kind === "python") return "pythonExecutable";
  if (kind === "allure") return "allureExecutable";
  throw new Error(`Unsupported runtime kind: ${kind}`);
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

function runtimeEnv(extraEnv, platform = process.platform) {
  return mergeEnvironment(process.env, extraEnv, platform);
}

function isExecutablePathAvailable(command, env = process.env, platform = process.platform) {
  if (!command || typeof command !== "string") return false;
  if (path.isAbsolute(command)) {
    try {
      return fs.existsSync(command) && fs.statSync(command).isFile();
    } catch (_error) {
      return false;
    }
  }
  const pathValue = env.PATH || env.Path || "";
  if (!pathValue) return false;
  const separator = platform === "win32" ? ";" : ":";
  const pathExt = platform === "win32"
    ? (env.PATHEXT || ".EXE;.CMD;.BAT").toLowerCase().split(";")
    : [""];
  const dirs = pathValue.split(separator).filter(Boolean);
  for (const dir of dirs) {
    for (const ext of pathExt) {
      const candidate = path.join(dir, command + ext);
      try {
        if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
          return true;
        }
      } catch (_error) {
        // continue
      }
    }
  }
  return false;
}

module.exports = {
  getRuntimeStatus,
  resetRuntimeExecutable,
  saveRuntimeExecutable,
};
