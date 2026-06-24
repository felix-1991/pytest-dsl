const fs = require("node:fs");
const path = require("node:path");
const { execFile } = require("node:child_process");

const { resolveAllureRuntime } = require("./allureEnvService");
const {
  isExecutableAvailable,
  mergeEnvironment,
  resolvePythonTargets,
} = require("./pythonEnvService");
const { readMetadata, updateRuntimeMetadata } = require("./metadataStore");

const PYTHON_PROBE_TIMEOUT_MS = 5000;
const PYTHON_PROBE_SCRIPT = [
  "import sys",
  "if sys.version_info < (3, 9):",
  "    raise RuntimeError(f'Python 3.9 or newer is required; current Python is {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
  "import pytest, pytest_dsl",
  "print(sys.executable)",
].join("\n");

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
        action: pythonInstallAction(),
      };
    }
    return {
      available: false,
      command: null,
      args: [],
      source: null,
      reason: "python-not-found",
      message: error.message,
      action: pythonInstallAction(),
    };
  }

  const configured = targets.find((target) => target.configured);
  const checked = targets.map((target) => describePythonTarget(target, env, options));
  const availableTargets = checked.filter((target) => target.available);

  if (configured && !isExecutableAvailable(configured.command, env, options)) {
    return {
      available: false,
      command: configured.command,
      args: configured.args,
      source: configured.source,
      reason: "python-not-found",
      message: `Configured Python executable does not exist: ${configured.command}`,
      detail: pythonNotFoundDetail(checked),
      action: pythonInstallAction(),
      checked,
    };
  }

  if (!availableTargets.length) {
    return {
      available: false,
      command: null,
      args: [],
      source: null,
      reason: "python-not-found",
      message: "No Python executable was found. Choose one in Configuration > Runtime.",
      detail: pythonNotFoundDetail(checked),
      action: pythonInstallAction(),
      checked,
    };
  }

  const probeTargets = configured
    ? availableTargets.filter((target) => target.configured)
    : availableTargets;
  const failedProbes = [];
  for (const target of probeTargets) {
    const probeResult = await runPythonDependencyProbe(target, projectRoot, env, options);
    annotateProbeResult(target, probeResult);
    if (probeResult.status === "ok") {
      return {
        available: true,
        command: target.command,
        args: target.args,
        source: target.source,
        reason: null,
        message: probeResult.executable || target.command,
        detail: `Command: ${runtimeCommand(target)}\nSource: ${runtimeSourceLabel(target.source)}`,
        checked,
      };
    }
    failedProbes.push({ target, probeResult });
  }

  const failed = failedProbes[0];
  if (failed && failed.probeResult.status === "version-unsupported") {
    const message = `Python 3.9 or newer is required for ${runtimeCommand(failed.target)}.`;
    return {
      available: false,
      command: failed.target.command,
      args: failed.target.args,
      source: failed.target.source,
      reason: "python-version-unsupported",
      message,
      detail: pythonProbeDetail(failed.target, failed.probeResult, checked),
      action: pythonInstallAction(),
      checked,
    };
  }
  if (failed && failed.probeResult.status === "missing") {
    const message = `Python dependencies are missing in ${runtimeCommand(failed.target)}: ${failed.probeResult.detail || "pytest or pytest_dsl"}`;
    return {
      available: false,
      command: failed.target.command,
      args: failed.target.args,
      source: failed.target.source,
      reason: "python-dependency-missing",
      message,
      detail: pythonProbeDetail(failed.target, failed.probeResult, checked),
      action: pythonInstallAction(),
      checked,
    };
  }
  if (failed) {
    const message = pythonProbeMessage(failed.target, failed.probeResult);
    return {
      available: false,
      command: failed.target.command,
      args: failed.target.args,
      source: failed.target.source,
      reason: "python-probe-failed",
      message,
      detail: pythonProbeDetail(failed.target, failed.probeResult, checked),
      action: pythonProbeAction(failed.target, failed.probeResult),
      signal: failed.probeResult.signal || null,
      code: failed.probeResult.code === undefined ? null : failed.probeResult.code,
      checked,
    };
  }

  const available = availableTargets[0];
  return {
    available: false,
    command: available.command,
    args: available.args,
    source: available.source,
    reason: "python-probe-failed",
    message: `Python probe failed: ${runtimeCommand(available)} was not tested.`,
    detail: pythonProbeDetail(available, { status: "error", detail: "Probe was not run." }, checked),
    action: "Open the console details, fix the interpreter error, or choose another Python interpreter.",
    checked,
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
          if (/Python 3\.9 or newer is required/i.test(combined)) {
            resolve({ status: "version-unsupported", detail: singleLine(combined) });
            return;
          }
          if (/ModuleNotFoundError|ImportError|No module named/i.test(combined)) {
            resolve({ status: "missing", detail: "pytest-dsl" });
            return;
          }
          if (error.signal) {
            resolve({
              status: "error",
              detail: `Python was terminated by signal ${error.signal}.`,
              signal: error.signal,
              code: error.code,
              stdout: stdout || "",
              stderr: stderr || "",
            });
            return;
          }
          resolve({
            status: "error",
            detail: error.message,
            code: error.code,
            stdout: stdout || "",
            stderr: stderr || "",
          });
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
  const normalized = resolveRuntimeExecutableSelection(kind, executablePath);
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

function resolveRuntimeExecutableSelection(kind, selectedPath) {
  const normalized = path.normalize(String(selectedPath || "").trim());
  if (kind !== "python" || !normalized) {
    return normalized;
  }
  try {
    if (!fs.statSync(normalized).isDirectory()) {
      return normalized;
    }
  } catch (_error) {
    return normalized;
  }
  const executable = pythonExecutableInEnvironment(normalized);
  if (executable) {
    return executable;
  }
  throw new Error(
    "Selected Python directory does not contain a Python interpreter. " +
    "Choose a Python executable file, a virtualenv directory, or a project directory containing .venv or venv.",
  );
}

function pythonExecutableInEnvironment(environmentRoot) {
  const candidates = [
    ...pythonExecutableCandidates(environmentRoot),
    ...pythonExecutableCandidates(path.join(environmentRoot, ".venv")),
    ...pythonExecutableCandidates(path.join(environmentRoot, "venv")),
  ];
  return candidates.find((candidate) => {
    try {
      return fs.statSync(candidate).isFile();
    } catch (_error) {
      return false;
    }
  }) || null;
}

function pythonExecutableCandidates(environmentRoot) {
  return [
    path.join(environmentRoot, "bin", "python"),
    path.join(environmentRoot, "bin", "python3"),
    path.join(environmentRoot, "Scripts", "python.exe"),
    path.join(environmentRoot, "Scripts", "python"),
    path.join(environmentRoot, "python.exe"),
    path.join(environmentRoot, "python"),
  ];
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

function describePythonTarget(target, env, options) {
  return {
    command: target.command,
    args: [...target.args],
    source: target.source,
    configured: target.configured,
    available: isExecutableAvailable(target.command, env, options),
  };
}

function annotateProbeResult(target, probeResult) {
  target.probeStatus = probeResult.status;
  if (probeResult.detail) {
    target.probeDetail = probeResult.detail;
  }
  if (probeResult.signal) {
    target.probeSignal = probeResult.signal;
  }
  if (probeResult.code !== null && probeResult.code !== undefined) {
    target.probeCode = probeResult.code;
  }
}

function pythonNotFoundDetail(checked) {
  return [
    "Checked Python candidates:",
    ...checked.map((target) => `- ${runtimeCommand(target)} [${runtimeSourceLabel(target.source)}]: ${target.available ? "found" : "not executable"}`),
  ].join("\n");
}

function pythonProbeMessage(target, probeResult) {
  if (probeResult.signal) {
    return `Python probe failed: ${runtimeCommand(target)} was terminated by signal ${probeResult.signal}.`;
  }
  return `Python probe failed: ${probeResult.detail || "unknown error"}`;
}

function pythonProbeDetail(target, probeResult, checked) {
  const lines = [
    `Command: ${runtimeCommand(target)}`,
    `Source: ${runtimeSourceLabel(target.source)}`,
  ];
  if (probeResult.signal) {
    lines.push(`Exit signal: ${probeResult.signal}`);
  }
  if (probeResult.code !== null && probeResult.code !== undefined) {
    lines.push(`Exit code: ${probeResult.code}`);
  }
  if (probeResult.detail) {
    lines.push(`Detail: ${probeResult.detail}`);
  }
  if (probeResult.stderr) {
    lines.push(`stderr: ${singleLine(probeResult.stderr)}`);
  }
  if (probeResult.stdout) {
    lines.push(`stdout: ${singleLine(probeResult.stdout)}`);
  }
  lines.push("Checked Python candidates:");
  checked.forEach((candidate) => {
    lines.push(`- ${runtimeCommand(candidate)} [${runtimeSourceLabel(candidate.source)}]: ${candidateProbeSummary(candidate)}`);
  });
  return lines.join("\n");
}

function candidateProbeSummary(candidate) {
  if (!candidate.available) {
    return "not executable";
  }
  if (candidate.probeStatus === "ok") {
    return "probe ok";
  }
  if (candidate.probeStatus === "missing") {
    return `dependencies missing${candidate.probeDetail ? ` (${singleLine(candidate.probeDetail)})` : ""}`;
  }
  if (candidate.probeStatus === "version-unsupported") {
    return `version unsupported${candidate.probeDetail ? ` (${singleLine(candidate.probeDetail)})` : ""}`;
  }
  if (candidate.probeStatus === "error") {
    const parts = ["probe failed"];
    if (candidate.probeSignal) {
      parts.push(`signal ${candidate.probeSignal}`);
    }
    if (candidate.probeCode !== null && candidate.probeCode !== undefined) {
      parts.push(`code ${candidate.probeCode}`);
    }
    if (candidate.probeDetail) {
      parts.push(singleLine(candidate.probeDetail));
    }
    return parts.join(", ");
  }
  return "found";
}

function pythonProbeAction(target, probeResult) {
  if (probeResult.signal === "SIGKILL") {
    if (target.source === "project-venv") {
      return "Rebuild the project virtualenv, or choose another working Python interpreter in Configuration > Runtime.";
    }
    return "Verify this Python binary can run from Terminal, or choose another interpreter in Configuration > Runtime.";
  }
  return pythonInstallAction();
}

function pythonInstallAction() {
  return "Install Python 3.9 or newer, then install pytest-dsl in that interpreter: pip install pytest-dsl.";
}

function runtimeCommand(target) {
  return [target.command, ...(target.args || [])].filter(Boolean).join(" ");
}

function runtimeSourceLabel(source) {
  const labels = {
    "project-config": "project configuration",
    "project-venv": "project virtualenv",
    environment: "environment variable",
    path: "PATH",
  };
  return labels[source] || source || "unknown";
}

function singleLine(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

module.exports = {
  getRuntimeStatus,
  resetRuntimeExecutable,
  saveRuntimeExecutable,
};
