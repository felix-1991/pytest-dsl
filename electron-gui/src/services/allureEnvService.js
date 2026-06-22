const fs = require("node:fs");
const path = require("node:path");
const { execFile } = require("node:child_process");

const { isExecutableAvailable } = require("./pythonEnvService");
const { readMetadata } = require("./metadataStore");

const ALLURE_VERSION_TIMEOUT_MS = 3000;

function executableName(name) {
  return process.platform === "win32" ? `${name}.cmd` : name;
}

function resolveAllureCandidates(projectRoot, env = process.env, options = {}) {
  const root = assertProjectRoot(projectRoot);
  const metadata = readMetadata(root);
  const configured = (options.allureExecutable || env.PYTEST_DSL_ALLURE || metadata.runtime.allureExecutable || "")
    .toString()
    .trim();
  const guiAllure = path.resolve(__dirname, "..", "..", "node_modules", ".bin", executableName("allure"));
  const projectAllure = path.join(root, "node_modules", ".bin", executableName("allure"));
  const candidates = [];

  if (configured) {
    candidates.push({
      command: configured,
      args: [],
      source: "project-config",
      configured: true,
    });
    return candidates;
  }

  if (fs.existsSync(projectAllure)) {
    candidates.push({
      command: projectAllure,
      args: [],
      source: "project-node-modules",
      configured: false,
    });
  }
  if (fs.existsSync(guiAllure)) {
    candidates.push({
      command: guiAllure,
      args: [],
      source: "studio-node-modules",
      configured: false,
    });
  }
  if (isExecutableAvailable("allure", env)) {
    candidates.push({
      command: "allure",
      args: [],
      source: "path",
      configured: false,
    });
  }
  return candidates;
}

async function resolveAllureRuntime(projectRoot, env = process.env, options = {}) {
  const candidates = resolveAllureCandidates(projectRoot, env, options);
  const configured = candidates.find((candidate) => candidate.configured);

  if (configured && !isExecutableAvailable(configured.command, env)) {
    return unavailable(
      "allure-config-invalid",
      `Configured Allure executable does not exist: ${configured.command}`,
      configured,
    );
  }

  const versionDetector = typeof options.allureVersionDetector === "function"
    ? options.allureVersionDetector
    : detectAllureVersion;

  for (const candidate of candidates) {
    if (!isExecutableAvailable(candidate.command, env)) {
      continue;
    }
    const version = await versionDetector(candidate, projectRoot, env);
    if (!version) {
      if (candidate.configured) {
        return unavailable(
          "allure-version-unreadable",
          "Unable to read configured Allure version",
          candidate,
        );
      }
      continue;
    }
    const major = Number(version.split(".")[0]);
    if (major < 3) {
      if (candidate.configured) {
        return unavailable(
          "allure-version-unsupported",
          `Pytest DSL Studio requires Allure 3; configured version is ${version}`,
          candidate,
          version,
        );
      }
      continue;
    }
    return {
      available: true,
      command: candidate.command,
      args: candidate.args,
      source: candidate.source,
      version,
      reason: null,
      message: `Allure ${version}`,
    };
  }

  return unavailable(
    "allure-not-found",
    "Allure 3 was not found. Choose it in Configuration > Runtime.",
  );
}

function unavailable(reason, message, candidate = null, version = null) {
  return {
    available: false,
    command: candidate ? candidate.command : null,
    args: candidate ? candidate.args : [],
    source: candidate ? candidate.source : null,
    version,
    reason,
    message,
  };
}

function detectAllureVersion(candidate, cwd, env) {
  return new Promise((resolve) => {
    const child = execFile(
      candidate.command,
      [...candidate.args, "--version"],
      {
        cwd,
        env,
        timeout: ALLURE_VERSION_TIMEOUT_MS,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        if (error) {
          resolve(null);
          return;
        }
        const text = `${stdout || ""}\n${stderr || ""}`;
        const match = text.match(/(\d+)\.(\d+)\.(\d+)/);
        resolve(match ? `${match[1]}.${match[2]}.${match[3]}` : null);
      },
    );
    child.on("error", () => resolve(null));
  });
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

module.exports = {
  detectAllureVersion,
  resolveAllureCandidates,
  resolveAllureRuntime,
};
