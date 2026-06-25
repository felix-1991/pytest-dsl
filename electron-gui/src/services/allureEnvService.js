const fs = require("node:fs");
const path = require("node:path");
const { execFile } = require("node:child_process");

const { readMetadata } = require("./metadataStore");
const {
  findExecutableInPath,
  isExecutableAvailable,
  runtimePathEntries,
  withRuntimePathEnv,
} = require("./runtimePathService");

const ALLURE_VERSION_TIMEOUT_MS = 15000;

function resolveAllureCandidates(projectRoot, env = process.env, options = {}) {
  const root = assertProjectRoot(projectRoot);
  const platform = options.platform || process.platform;
  const metadata = readMetadata(root);
  const configured = (options.allureExecutable || env.PYTEST_DSL_ALLURE || metadata.runtime.allureExecutable || "")
    .toString()
    .trim();
  const guiAllure = firstExistingExecutable(
    allureExecutableNames(platform).map((name) => path.resolve(__dirname, "..", "..", "node_modules", ".bin", name)),
    env,
    platform,
  );
  const projectAllure = firstExistingExecutable(
    allureExecutableNames(platform).map((name) => path.join(root, "node_modules", ".bin", name)),
    env,
    platform,
  );
  const candidates = [];

  if (configured) {
    candidates.push(allureTarget(configured, [], "project-config", true, platform));
    return candidates;
  }

  if (projectAllure) {
    candidates.push(allureTarget(projectAllure, [], "project-node-modules", false, platform));
  }
  if (guiAllure) {
    candidates.push(allureTarget(guiAllure, [], "studio-node-modules", false, platform));
  }
  const pathAllure = findExecutableInPath("allure", env, options);
  if (pathAllure) {
    candidates.push(allureTarget(pathAllure, [], "path", false, platform));
  }
  return candidates;
}

async function resolveAllureRuntime(projectRoot, env = process.env, options = {}) {
  const candidates = resolveAllureCandidates(projectRoot, env, options);
  const configured = candidates.find((candidate) => candidate.configured);

  if (configured && !isExecutableAvailable(configured.command, env, options)) {
    return unavailable(
      "allure-config-invalid",
      `Configured Allure executable does not exist: ${configured.command}`,
      configured,
      null,
      `Command: ${configured.command}\nSource: project configuration`,
      "Install Allure 3 with npm install -g allure, or choose a valid Allure 3 executable in Configuration > Runtime.",
      candidates,
    );
  }

  const versionDetector = typeof options.allureVersionDetector === "function"
    ? options.allureVersionDetector
    : detectAllureVersion;

  for (const candidate of candidates) {
    if (!isExecutableAvailable(candidate.command, env, options)) {
      continue;
    }
    let version = null;
    let versionError = null;
    try {
      version = await versionDetector(candidate, projectRoot, env, options);
    } catch (error) {
      versionError = error;
    }
    if (!version) {
      if (candidate.configured) {
        return unavailable(
          "allure-version-unreadable",
          "Unable to read configured Allure version",
          candidate,
          null,
          allureProbeDetail(candidate, versionError),
          "Install Allure 3 with npm install -g allure, choose an Allure 3 executable, or verify this command prints a semantic version with --version.",
          candidates,
        );
      }
      continue;
    }
    const versionText = String(version);
    const major = Number(versionText.split(".")[0]);
    if (!Number.isFinite(major)) {
      if (candidate.configured) {
        return unavailable(
          "allure-version-unreadable",
          "Unable to read configured Allure version",
          candidate,
          null,
          allureProbeDetail(candidate),
          "Install Allure 3 with npm install -g allure, choose an Allure 3 executable, or verify this command prints a semantic version with --version.",
          candidates,
        );
      }
      continue;
    }
    if (major < 3) {
      if (candidate.configured) {
        return unavailable(
          "allure-version-unsupported",
          `Pytest DSL Studio requires Allure 3; configured version is ${versionText}`,
          candidate,
          versionText,
          `Command: ${runtimeCommand(candidate)}\nSource: ${runtimeSourceLabel(candidate.source)}\nDetected version: ${versionText}`,
          "Install Allure 3 with npm install -g allure or choose an Allure 3 executable in Configuration > Runtime.",
          candidates,
        );
      }
      continue;
    }
    return {
      available: true,
      command: candidate.command,
      args: candidate.args,
      shell: candidate.shell,
      source: candidate.source,
      version: versionText,
      reason: null,
      message: `Allure ${versionText}`,
      detail: `Command: ${runtimeCommand(candidate)}\nSource: ${runtimeSourceLabel(candidate.source)}`,
      checked: describeAllureCandidates(candidates),
    };
  }

  return unavailable(
    "allure-not-found",
    "Allure 3 was not found. Choose it in Configuration > Runtime.",
    null,
    null,
    allureNotFoundDetail(projectRoot, env, options),
    "Install Allure 3 with npm install -g allure, choose its executable, or restart Studio after making Allure available on PATH.",
    candidates,
  );
}

function unavailable(
  reason,
  message,
  candidate = null,
  version = null,
  detail = "",
  action = "",
  candidates = [],
) {
  return {
    available: false,
    command: candidate ? candidate.command : null,
    args: candidate ? candidate.args : [],
    source: candidate ? candidate.source : null,
    version,
    reason,
    message,
    detail,
    action,
    checked: describeAllureCandidates(candidates),
  };
}

function detectAllureVersion(candidate, cwd, env, options = {}) {
  return new Promise((resolve) => {
    const execEnv = withRuntimePathEnv(env, options);
    let child;
    try {
      child = execFile(
        candidate.command,
        [...candidate.args, "--version"],
        {
          cwd,
          env: execEnv,
          timeout: ALLURE_VERSION_TIMEOUT_MS,
          windowsHide: true,
          shell: candidate.shell || false,
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
    } catch (_error) {
      resolve(null);
      return;
    }
    child.on("error", () => resolve(null));
  });
}

function allureTarget(command, args, source, configured, platform = process.platform) {
  return {
    command,
    args: [...args],
    source,
    configured,
    shell: shouldRunAllureThroughShell(command, platform),
  };
}

function shouldRunAllureThroughShell(command, platform = process.platform) {
  return platform === "win32" && /\.(?:cmd|bat)$/i.test(String(command || ""));
}

function allureProbeDetail(candidate, error = null) {
  return [
    `Command: ${runtimeCommand(candidate)}`,
    `Source: ${runtimeSourceLabel(candidate.source)}`,
    error ? `Detail: ${singleLine(error.message || error)}` : "",
  ].filter(Boolean).join("\n");
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

function allureExecutableNames(platform = process.platform) {
  if (platform === "win32") {
    return ["allure.cmd", "allure.bat", "allure.exe", "allure"];
  }
  return ["allure"];
}

function firstExistingExecutable(candidates, env, platform) {
  return candidates.find((candidate) => isExecutableAvailable(candidate, env, { platform })) || null;
}

function allureNotFoundDetail(projectRoot, env, options) {
  const locations = searchedAllureLocations(projectRoot, env, options);
  const shown = locations.slice(0, 12);
  const lines = [
    "Checked Allure locations:",
    ...shown.map((location) => `- ${location}`),
  ];
  if (locations.length > shown.length) {
    lines.push(`- ... ${locations.length - shown.length} more`);
  }
  return lines.join("\n");
}

function searchedAllureLocations(projectRoot, env, options) {
  const root = assertProjectRoot(projectRoot);
  const platform = options.platform || process.platform;
  const names = allureExecutableNames(platform);
  const locations = [];
  names.forEach((name) => locations.push(path.join(root, "node_modules", ".bin", name)));
  names.forEach((name) => locations.push(path.resolve(__dirname, "..", "..", "node_modules", ".bin", name)));
  for (const directory of runtimePathEntries(env, options)) {
    names.forEach((name) => locations.push(path.join(directory, name)));
  }
  return dedupeStrings(locations, platform);
}

function describeAllureCandidates(candidates) {
  return candidates.map((candidate) => ({
    command: candidate.command,
    args: [...candidate.args],
    shell: candidate.shell || false,
    source: candidate.source,
    configured: candidate.configured,
  }));
}

function runtimeCommand(candidate) {
  return [candidate.command, ...(candidate.args || [])].filter(Boolean).join(" ");
}

function runtimeSourceLabel(source) {
  const labels = {
    "project-config": "project configuration",
    "project-node-modules": "project node_modules",
    "studio-node-modules": "Studio bundled node_modules",
    path: "PATH",
  };
  return labels[source] || source || "unknown";
}

function singleLine(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function dedupeStrings(values, platform) {
  const seen = new Set();
  return values.filter((value) => {
    const key = platform === "win32" ? value.toLowerCase() : value;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

module.exports = {
  detectAllureVersion,
  resolveAllureCandidates,
  resolveAllureRuntime,
};
