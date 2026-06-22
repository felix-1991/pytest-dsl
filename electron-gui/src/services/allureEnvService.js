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
  // Check common package manager locations (Electron apps may not inherit full PATH)
  // This can be disabled via options.skipCommonPaths for testing
  if (!options.skipCommonPaths) {
    const commonAllurePaths = getCommonAllurePaths();
    for (const allurePath of commonAllurePaths) {
      if (fs.existsSync(allurePath)) {
        const alreadyAdded = candidates.some((c) => c.command === allurePath);
        if (!alreadyAdded) {
          candidates.push({
            command: allurePath,
            args: [],
            source: "common-path",
            configured: false,
          });
        }
      }
    }
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

// Get common paths where Allure might be installed, based on platform
function getCommonAllurePaths() {
  if (process.platform === "win32") {
    // Windows: Check common installation locations
    const paths = [];
    // Chocolatey installation
    const chocolateyBin = path.join(process.env.ChocolateyInstall || "C:\\ProgramData\\chocolatey", "bin");
    paths.push(path.join(chocolateyBin, "allure.cmd"));
    paths.push(path.join(chocolateyBin, "allure.bat"));
    // Scoop installation (user-local)
    const scoopShim = path.join(process.env.USERPROFILE || "", "scoop", "shims");
    paths.push(path.join(scoopShim, "allure.cmd"));
    paths.push(path.join(scoopShim, "allure.bat"));
    // Common install directories
    paths.push("C:\\allure\\bin\\allure.cmd");
    paths.push("C:\\allure\\bin\\allure.bat");
    return paths.filter(Boolean);
  }
  // macOS/Linux: Check common homebrew and system paths
  return [
    "/opt/homebrew/bin/allure",
    "/usr/local/bin/allure",
    "/usr/bin/allure",
  ];
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
    // Only enhance PATH for absolute-path commands that might have shebangs needing node
    // For relative commands like "allure" from PATH, use the original env
    const needsPathEnhancement = path.isAbsolute(candidate.command);
    const execEnv = needsPathEnhancement ? enhancePathForExecutables(env) : env;
    const child = execFile(
      candidate.command,
      [...candidate.args, "--version"],
      {
        cwd,
        env: execEnv,
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

// Enhance PATH with common locations where Node.js and other tools may be installed
// This is needed because Electron apps launched from Finder/Start Menu don't inherit the shell's PATH
function enhancePathForExecutables(env) {
  if (!env || typeof env !== "object") {
    env = {};
  }
  const commonPaths = getCommonExecutablePaths();
  const separator = process.platform === "win32" ? ";" : ":";
  // Handle Windows case-insensitive PATH key
  const pathKey = Object.keys(env).find((k) => k.toLowerCase() === "path") || "PATH";
  const currentPath = env[pathKey] || "";
  const pathParts = currentPath.split(separator).filter(Boolean);
  const newPathParts = [...pathParts];
  const pathSet = new Set(pathParts.map((p) => p.toLowerCase()));
  for (const p of commonPaths) {
    if (!pathSet.has(p.toLowerCase()) && fs.existsSync(p)) {
      newPathParts.unshift(p);
      pathSet.add(p.toLowerCase());
    }
  }
  return {
    ...env,
    [pathKey]: newPathParts.join(separator),
  };
}

// Get common paths where executables (like Node.js) might be installed, based on platform
function getCommonExecutablePaths() {
  if (process.platform === "win32") {
    // Windows: Check common Node.js and tool installation locations
    const paths = [];
    // Node.js default installation
    paths.push("C:\\Program Files\\nodejs");
    paths.push("C:\\Program Files (x86)\\nodejs");
    // User-local npm global
    const appData = process.env.APPDATA || "";
    if (appData) {
      paths.push(path.join(appData, "npm"));
      paths.push(path.join(appData, "Roaming", "npm"));
    }
    // Chocolatey
    const chocolateyBin = path.join(process.env.ChocolateyInstall || "C:\\ProgramData\\chocolatey", "bin");
    paths.push(chocolateyBin);
    // Scoop
    const scoopShim = path.join(process.env.USERPROFILE || "", "scoop", "shims");
    paths.push(scoopShim);
    return paths.filter(Boolean);
  }
  // macOS/Linux: Check common homebrew and system paths
  return [
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    "/usr/local/bin",
    "/usr/local/sbin",
    "/usr/bin",
    "/bin",
  ];
}

module.exports = {
  detectAllureVersion,
  resolveAllureCandidates,
  resolveAllureRuntime,
};
