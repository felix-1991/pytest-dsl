const fs = require("node:fs");
const http = require("node:http");
const https = require("node:https");
const path = require("node:path");
const { spawn, execFile } = require("node:child_process");
const { randomUUID } = require("node:crypto");

const {
  isExecutableAvailable,
  mergeEnvironment,
  resolvePythonTarget,
} = require("./pythonEnvService");
const { buildPytestTargets } = require("./suiteService");

const runningBuilds = new Map();
const URL_PATTERN = /(https?:\/\/[^\s'"]+)/;
const ALLURE_VERSION_TIMEOUT_MS = 3000;
const ALLURE_REPORT_READY_TIMEOUT_MS = 1500;
const ALLURE_REPORT_READY_INTERVAL_MS = 100;
const ALLURE_REPORT_COMPLETION_WAIT_MS = 2500;
const ALLURE_EXPORT_TIMEOUT_MS = 60000;

function createBuildPlan(
  options = {},
  env = executionEnv(options.env, options.platform),
) {
  const projectRoot = assertProjectRoot(options.projectRoot);
  const buildId = sanitizeId(options.buildId || options.taskId || randomUUID());
  const yamlVars = normalizeYamlVars(options.yamlVars);
  const selectedSuiteIds = normalizeSelectedSuiteIds(options.selectedSuiteIds);
  const selectedFiles = options.selectedFiles || null;
  const targets = buildPytestTargets(projectRoot, selectedSuiteIds, selectedFiles);
  const buildRelativeDir = normalizePath(path.join(".pytest-dsl-gui", "builds", buildId));
  const resultsRelativeDir = normalizePath(path.join(buildRelativeDir, "allure-results"));
  const reportRelativeDir = normalizePath(path.join(buildRelativeDir, "allure-report"));
  const buildDir = path.join(projectRoot, buildRelativeDir);
  const allureResultsDir = path.join(projectRoot, resultsRelativeDir);
  const allureReportDir = path.join(projectRoot, reportRelativeDir);
  const args = [
    ...targets,
    "--alluredir",
    resultsRelativeDir,
    ...yamlArgs(yamlVars),
  ];

  return {
    buildId,
    taskId: buildId,
    mode: "build",
    cwd: projectRoot,
    command: commandForPytest(options, env),
    args,
    displayCommand: displayBuildCommand(targets, resultsRelativeDir, yamlVars),
    buildDir,
    buildRelativeDir,
    allureResultsDir,
    allureResultsRelativeDir: resultsRelativeDir,
    allureReportDir,
    allureReportRelativeDir: reportRelativeDir,
    stdoutPath: path.join(buildDir, "stdout.log"),
    stderrPath: path.join(buildDir, "stderr.log"),
    manifestPath: path.join(buildDir, "build.json"),
    source: {
      kind: "build",
      selectedSuiteIds,
      selectedFiles,
      targets,
      label: targets.length > 0 ? targets.join(" ") : "no targets",
    },
  };
}

async function startBuildTask(options = {}, callbacks = {}) {
  const env = executionEnv(options.env, options.platform);
  const plan = createBuildPlan(options, env);
  const startedAt = Date.now();

  if (runningBuilds.has(plan.buildId)) {
    throw new Error(`Build task is already running: ${plan.buildId}`);
  }

  const spawnTarget = options.pytestCommandOverride
    ? options.pytestCommandOverride
    : resolvePytestSpawnTarget(plan, options, env);

  prepareBuildDirectories(plan);
  writeManifest(plan, {
    buildId: plan.buildId,
    status: "running",
    startedAt: new Date(startedAt).toISOString(),
    command: plan.displayCommand,
    source: plan.source,
    allureResultsDir: plan.allureResultsDir,
    allureReportDir: plan.allureReportDir,
    reportUrl: null,
  });

  let resolveCompletion;
  const completion = new Promise((resolve) => {
    resolveCompletion = resolve;
  });
  const task = {
    plan,
    buildChild: null,
    reportChild: null,
    reportUrl: null,
    stopped: false,
    killTimer: null,
    stdoutBuffer: "",
    reportBuffer: "",
    reportReadyPending: false,
    reportReadyResolved: false,
    reportReadyWaiters: [],
    buildFinished: false,
    buildExitCode: null,
    buildSignal: null,
    completionSettled: false,
    resolveCompletion,
    startedAt,
    callbacks,
  };
  runningBuilds.set(plan.buildId, task);

  emit(callbacks, {
    type: "build-started",
    taskId: plan.buildId,
    buildId: plan.buildId,
    mode: "build",
    command: plan.displayCommand,
    source: plan.source,
    allureResultsDir: plan.allureResultsDir,
    allureReportDir: plan.allureReportDir,
  });

  try {
    await maybeStartAllureWatch(task, options, env, callbacks);
  } catch (error) {
    const text = `${error.message}\n`;
    fs.appendFileSync(plan.stderrPath, text);
    emit(callbacks, {
      type: "stderr",
      taskId: plan.buildId,
      buildId: plan.buildId,
      text,
    });
    task.buildFinished = true;
    task.buildExitCode = 1;
    settleBuildCompletion(task);
    return completion;
  }

  if (task.stopped) {
    task.buildFinished = true;
    settleBuildCompletion(task);
    return completion;
  }

  let child;
  try {
    child = spawn(spawnTarget.command, spawnTarget.args, {
      cwd: plan.cwd,
      env,
      windowsHide: true,
    });
    task.buildChild = child;
  } catch (error) {
    const text = `${error.message}\n`;
    fs.appendFileSync(plan.stderrPath, text);
    emit(callbacks, {
      type: "stderr",
      taskId: plan.buildId,
      buildId: plan.buildId,
      text,
    });
    task.buildFinished = true;
    task.buildExitCode = 1;
    settleBuildCompletion(task);
    return completion;
  }

  child.stdout.on("data", (chunk) => {
    const text = chunk.toString();
    fs.appendFileSync(plan.stdoutPath, text);
    emit(callbacks, {
      type: "stdout",
      taskId: plan.buildId,
      buildId: plan.buildId,
      text,
    });
  });

  child.stderr.on("data", (chunk) => {
    const text = chunk.toString();
    fs.appendFileSync(plan.stderrPath, text);
    emit(callbacks, {
      type: "stderr",
      taskId: plan.buildId,
      buildId: plan.buildId,
      text,
    });
  });

  child.on("error", (error) => {
    const text = `${error.message}\n`;
    fs.appendFileSync(plan.stderrPath, text);
    emit(callbacks, {
      type: "stderr",
      taskId: plan.buildId,
      buildId: plan.buildId,
      text,
    });
  });

  child.on("close", async (exitCode, signal) => {
    if (task.buildChild === child) {
      task.buildChild = null;
    }
    task.buildFinished = true;
    task.buildExitCode = exitCode;
    task.buildSignal = signal;

    if (!task.stopped) {
      await waitForReportReadyBeforeCompletion(task);
    }
    settleBuildCompletion(task);
  });

  return completion;
}

function settleBuildCompletion(task) {
  if (task.completionSettled || !task.buildFinished) {
    return;
  }
  if (task.stopped && (task.buildChild || task.reportChild)) {
    return;
  }

  task.completionSettled = true;
  const completedAt = Date.now();
  const status = task.stopped
    ? "stopped"
    : task.buildExitCode === 0 ? "passed" : "failed";
  const result = {
    taskId: task.plan.buildId,
    buildId: task.plan.buildId,
    mode: "build",
    status,
    exitCode: task.buildExitCode,
    signal: task.buildSignal,
    durationMs: completedAt - task.startedAt,
    reportUrl: task.reportUrl,
    allureResultsDir: task.plan.allureResultsDir,
    allureReportDir: task.plan.allureReportDir,
  };

  writeManifest(task.plan, {
    buildId: task.plan.buildId,
    status,
    startedAt: new Date(task.startedAt).toISOString(),
    completedAt: new Date(completedAt).toISOString(),
    durationMs: result.durationMs,
    command: task.plan.displayCommand,
    source: task.plan.source,
    exitCode: task.buildExitCode,
    signal: task.buildSignal,
    allureResultsDir: task.plan.allureResultsDir,
    allureReportDir: task.plan.allureReportDir,
    reportUrl: task.reportUrl,
  });
  emit(task.callbacks, {
    type: "build-completed",
    ...result,
  });
  task.resolveCompletion(result);
  deleteBuildIfIdle(task);
}

function stopBuildTask(buildId) {
  const normalized = sanitizeId(buildId);
  const task = runningBuilds.get(normalized);
  if (!task) {
    return { stopped: false, reason: "not-running" };
  }

  task.stopped = true;
  signalBuildChildren(task, "SIGTERM");
  if (!task.killTimer) {
    task.killTimer = setTimeout(() => {
      signalBuildChildren(task, "SIGKILL");
    }, 1500);
    if (typeof task.killTimer.unref === "function") {
      task.killTimer.unref();
    }
  }
  settleBuildCompletion(task);
  return { stopped: true, buildId: normalized };
}

function signalBuildChildren(task, signal) {
  for (const child of [task.buildChild, task.reportChild]) {
    if (isChildAlive(child)) {
      child.kill(signal);
    }
  }
}

function isChildAlive(child) {
  return Boolean(
    child && child.exitCode === null && child.signalCode === null,
  );
}

function hasRunningBuild(buildId) {
  return runningBuilds.has(sanitizeId(buildId));
}

function defaultBuildLogExportName(buildId) {
  return `pytest-dsl-build-${sanitizeExportFilePart(buildId)}.log`;
}

function defaultAllureReportExportName(buildId) {
  return `allure-report-${sanitizeExportFilePart(buildId)}.html`;
}

function exportBuildLogs(options = {}) {
  const plan = createBuildArtifactPlan(options);
  const destinationPath = assertDestinationPath(options.destinationPath);
  const manifest = assertCompletedBuildManifest(plan);
  const stdout = readOptionalTextFile(plan.stdoutPath);
  const stderr = readOptionalTextFile(plan.stderrPath);
  const content = buildLogExportContent({
    buildId: plan.buildId,
    manifest,
    stdout,
    stderr,
  });

  fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
  fs.writeFileSync(destinationPath, content, "utf8");
  patchManifest(plan, {
    logExportedAt: new Date().toISOString(),
    logExportPath: destinationPath,
  });

  return {
    buildId: plan.buildId,
    path: destinationPath,
    bytes: fs.statSync(destinationPath).size,
  };
}

async function exportAllureReportFile(options = {}) {
  const plan = createBuildArtifactPlan(options);
  const destinationPath = assertDestinationPath(options.destinationPath);
  assertCompletedBuildManifest(plan);
  assertDirectoryHasEntries(plan.allureResultsDir, "Allure results directory");

  const env = executionEnv(options.env);
  const spawnTarget = options.allureExportCommandOverride ||
    await resolveAllureExportSpawnTarget(plan, options, env);
  if (!spawnTarget) {
    throw new Error("Allure 3 executable is not available for report export");
  }

  fs.rmSync(plan.allureReportDir, { recursive: true, force: true });
  fs.mkdirSync(plan.allureReportDir, { recursive: true });
  await runAllureReportExport(spawnTarget, plan, env);

  const generatedHtml = findGeneratedReportHtml(plan.allureReportDir);
  fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
  fs.copyFileSync(generatedHtml, destinationPath);
  patchManifest(plan, {
    allureReportDir: plan.allureReportDir,
    reportExportedAt: new Date().toISOString(),
    reportExportPath: destinationPath,
  });

  return {
    buildId: plan.buildId,
    path: destinationPath,
    sourcePath: generatedHtml,
    bytes: fs.statSync(destinationPath).size,
  };
}

async function maybeStartAllureWatch(task, options, env, callbacks) {
  if (task.stopped) {
    markReportReadyResolved(task);
    return;
  }
  if (options.enableAllureWatch === false) {
    emit(callbacks, {
      type: "report-unavailable",
      taskId: task.plan.buildId,
      buildId: task.plan.buildId,
      reason: "disabled",
    });
    markReportReadyResolved(task);
    return;
  }

  const spawnTarget = options.allureCommandOverride
    ? options.allureCommandOverride
    : await resolveAllureWatchSpawnTarget(task.plan, options, env, task);
  if (task.stopped) {
    markReportReadyResolved(task);
    return;
  }
  if (!spawnTarget) {
    emit(callbacks, {
      type: "report-unavailable",
      taskId: task.plan.buildId,
      buildId: task.plan.buildId,
      reason: "allure3-unavailable",
    });
    markReportReadyResolved(task);
    return;
  }

  const child = spawn(spawnTarget.command, spawnTarget.args, {
    cwd: task.plan.cwd,
    env,
    windowsHide: true,
  });
  task.reportChild = child;

  const handleText = (text) => {
    task.reportBuffer += text;
    const match = task.reportBuffer.match(URL_PATTERN);
    if (match && !task.reportUrl && !task.reportReadyPending) {
      task.reportReadyPending = true;
      publishAllureReportReady(task, match[1], options, callbacks);
    }
  };

  child.stdout.on("data", (chunk) => handleText(chunk.toString()));
  child.stderr.on("data", (chunk) => handleText(chunk.toString()));
  child.on("error", (error) => {
    emit(callbacks, {
      type: "report-unavailable",
      taskId: task.plan.buildId,
      buildId: task.plan.buildId,
      reason: error.message,
    });
    markReportReadyResolved(task);
  });
  child.on("close", () => {
    if (task.reportChild === child) {
      task.reportChild = null;
    }
    markReportReadyResolved(task);
    settleBuildCompletion(task);
    deleteBuildIfIdle(task);
  });

  emit(callbacks, {
    type: "report-started",
    taskId: task.plan.buildId,
    buildId: task.plan.buildId,
    command: [spawnTarget.command, ...spawnTarget.args].join(" "),
  });
}

async function resolveAllureExportSpawnTarget(plan, options = {}, env = process.env) {
  const candidates = allureCandidates(plan.cwd, options, env);
  for (const candidate of candidates) {
    const major = await detectAllureMajor(candidate, plan.cwd, env);
    if (major >= 3) {
      return {
        command: candidate.command,
        args: candidate.args,
      };
    }
  }
  return null;
}

function runAllureReportExport(spawnTarget, plan, env) {
  const args = [
    ...spawnTarget.args,
    "awesome",
    "--single-file",
    "--output",
    plan.allureReportDir,
    plan.allureResultsDir,
  ];
  return new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    const child = spawn(spawnTarget.command, args, {
      cwd: plan.cwd,
      env,
      windowsHide: true,
    });
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`Allure report export timed out after ${ALLURE_EXPORT_TIMEOUT_MS}ms`));
    }, ALLURE_EXPORT_TIMEOUT_MS);
    if (typeof timer.unref === "function") {
      timer.unref();
    }

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (exitCode, signal) => {
      clearTimeout(timer);
      if (exitCode === 0) {
        resolve({ stdout, stderr });
        return;
      }
      const details = [stdout.trim(), stderr.trim()].filter(Boolean).join("\n");
      reject(new Error(`Allure report export failed with exit code ${exitCode}${signal ? ` (${signal})` : ""}${details ? `: ${details}` : ""}`));
    });
  });
}

async function publishAllureReportReady(task, rawUrl, options, callbacks) {
  const reportUrl = await resolveAllureReportUrl(rawUrl, options);
  if (task.stopped || task.reportUrl) {
    return;
  }
  task.reportUrl = reportUrl;
  patchManifest(task.plan, { reportUrl: task.reportUrl });
  emit(callbacks, {
    type: "report-ready",
    taskId: task.plan.buildId,
    buildId: task.plan.buildId,
    url: task.reportUrl,
  });
  markReportReadyResolved(task);
}

async function waitForReportReadyBeforeCompletion(task) {
  if (task.reportReadyResolved || !task.reportChild) {
    return;
  }
  await Promise.race([
    new Promise((resolve) => {
      task.reportReadyWaiters.push(resolve);
    }),
    delay(ALLURE_REPORT_COMPLETION_WAIT_MS),
  ]);
}

function markReportReadyResolved(task) {
  if (task.reportReadyResolved) {
    return;
  }
  task.reportReadyResolved = true;
  const waiters = task.reportReadyWaiters.splice(0);
  waiters.forEach((resolve) => resolve());
}

async function resolveAllureReportUrl(rawUrl, options = {}) {
  const directUrl = directAllureReportUrl(rawUrl);
  if (typeof options.allureReportReadyProbe === "function") {
    const probedUrl = await options.allureReportReadyProbe(rawUrl, directUrl);
    return directAllureReportUrl(probedUrl || directUrl);
  }
  if (options.allureCommandOverride) {
    return directUrl;
  }
  return waitForAllureReportReady(directUrl);
}

function directAllureReportUrl(rawUrl) {
  const value = String(rawUrl || "").trim();
  if (!value) {
    return "";
  }
  try {
    const parsed = new URL(value);
    const normalizedPath = parsed.pathname.replace(/\/+$/, "");
    if (!normalizedPath) {
      parsed.pathname = "/awesome/";
    } else if (normalizedPath.endsWith("/awesome")) {
      parsed.pathname = `${normalizedPath}/`;
    }
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch (_error) {
    return value;
  }
}

async function waitForAllureReportReady(reportUrl) {
  const deadline = Date.now() + ALLURE_REPORT_READY_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await canLoadReportUrl(reportUrl)) {
      return reportUrl;
    }
    await delay(ALLURE_REPORT_READY_INTERVAL_MS);
  }
  return reportUrl;
}

function canLoadReportUrl(reportUrl) {
  return new Promise((resolve) => {
    let parsed;
    try {
      parsed = new URL(reportUrl);
    } catch (_error) {
      resolve(false);
      return;
    }
    const client = parsed.protocol === "https:" ? https : http;
    const request = client.get(parsed, (response) => {
      response.resume();
      resolve(response.statusCode >= 200 && response.statusCode < 400);
    });
    request.setTimeout(ALLURE_REPORT_READY_INTERVAL_MS, () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function deleteBuildIfIdle(task) {
  if (
    runningBuilds.get(task.plan.buildId) === task &&
    task.completionSettled &&
    !task.buildChild &&
    !task.reportChild
  ) {
    if (task.killTimer) {
      clearTimeout(task.killTimer);
      task.killTimer = null;
    }
    runningBuilds.delete(task.plan.buildId);
  }
}

async function resolveAllureWatchSpawnTarget(
  plan,
  options = {},
  env = process.env,
  task = null,
) {
  const candidates = allureCandidates(plan.cwd, options, env);
  const versionDetector = typeof options.allureVersionDetector === "function"
    ? options.allureVersionDetector
    : detectAllureMajor;
  for (const candidate of candidates) {
    const major = await versionDetector(candidate, plan.cwd, env);
    if (task && task.stopped) {
      return null;
    }
    if (major >= 3) {
      return {
        command: candidate.command,
        args: [
          ...candidate.args,
          "watch",
          plan.allureResultsDir,
        ],
      };
    }
  }
  return null;
}

function allureCandidates(projectRoot, options = {}, env = process.env) {
  const configured = options.allureExecutable || env.PYTEST_DSL_ALLURE;
  const guiAllure = path.resolve(__dirname, "..", "..", "node_modules", ".bin", executableName("allure"));
  const projectAllure = path.join(projectRoot, "node_modules", ".bin", executableName("allure"));
  const candidates = [];
  if (configured) {
    candidates.push({ command: configured, args: [] });
  }
  if (fs.existsSync(guiAllure)) {
    candidates.push({ command: guiAllure, args: [] });
  }
  if (fs.existsSync(projectAllure)) {
    candidates.push({ command: projectAllure, args: [] });
  }
  if (isExecutableAvailable("allure", env)) {
    candidates.push({ command: "allure", args: [] });
  }
  return candidates;
}

function detectAllureMajor(candidate, cwd, env) {
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
        resolve(match ? Number(match[1]) : null);
      },
    );
    child.on("error", () => resolve(null));
  });
}

function resolvePytestSpawnTarget(plan, options = {}, env = {}) {
  const explicitCommand = explicitPytestCommand(options, env);
  if (explicitCommand && isExecutableAvailable(explicitCommand, env)) {
    return {
      command: explicitCommand,
      args: plan.args,
    };
  }
  const target = resolvePythonTarget(plan.cwd, env, options);
  return {
    command: target.command,
    args: [...target.args, "-m", "pytest", ...plan.args],
  };
}

function commandForPytest(options = {}, env = {}) {
  return explicitPytestCommand(options, env) || "pytest";
}

function explicitPytestCommand(options = {}, env = {}) {
  return options.pytestExecutable || env.PYTEST_DSL_PYTEST || null;
}

function displayBuildCommand(targets, resultsDir, yamlVars) {
  const targetArgs = targets.join(" ");
  const configArgs = yamlVars.length > 0
    ? ` ${yamlArgs(yamlVars).join(" ")}`
    : "";
  const prefix = targetArgs ? `pytest ${targetArgs}` : "pytest";
  return `${prefix} --alluredir ${resultsDir}${configArgs}`;
}

function prepareBuildDirectories(plan) {
  fs.mkdirSync(plan.allureResultsDir, { recursive: true });
  fs.mkdirSync(plan.allureReportDir, { recursive: true });
  fs.writeFileSync(plan.stdoutPath, "", "utf8");
  fs.writeFileSync(plan.stderrPath, "", "utf8");
}

function writeManifest(plan, data) {
  fs.mkdirSync(plan.buildDir, { recursive: true });
  fs.writeFileSync(plan.manifestPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

function patchManifest(plan, data) {
  let current = {};
  try {
    current = JSON.parse(fs.readFileSync(plan.manifestPath, "utf8"));
  } catch (_error) {
    current = {};
  }
  writeManifest(plan, {
    ...current,
    ...data,
  });
}

function createBuildArtifactPlan(options = {}) {
  const projectRoot = assertProjectRoot(options.projectRoot);
  const buildId = sanitizeId(options.buildId || options.taskId);
  const buildRelativeDir = normalizePath(path.join(".pytest-dsl-gui", "builds", buildId));
  const buildDir = path.join(projectRoot, buildRelativeDir);
  return {
    buildId,
    taskId: buildId,
    cwd: projectRoot,
    buildDir,
    buildRelativeDir,
    allureResultsDir: path.join(buildDir, "allure-results"),
    allureReportDir: path.join(buildDir, "allure-report"),
    stdoutPath: path.join(buildDir, "stdout.log"),
    stderrPath: path.join(buildDir, "stderr.log"),
    manifestPath: path.join(buildDir, "build.json"),
  };
}

function assertCompletedBuildManifest(plan) {
  const manifest = readBuildManifest(plan);
  if (manifest.status === "running") {
    throw new Error(`Build is still running: ${plan.buildId}`);
  }
  return manifest;
}

function readBuildManifest(plan) {
  if (!fs.existsSync(plan.manifestPath)) {
    throw new Error(`Build manifest does not exist: ${plan.manifestPath}`);
  }
  try {
    return JSON.parse(fs.readFileSync(plan.manifestPath, "utf8"));
  } catch (error) {
    throw new Error(`Build manifest is invalid: ${error.message}`);
  }
}

function assertDestinationPath(destinationPath) {
  const value = String(destinationPath || "").trim();
  if (!value) {
    throw new Error("destinationPath is required");
  }
  return path.resolve(value);
}

function readOptionalTextFile(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch (_error) {
    return "";
  }
}

function buildLogExportContent({ buildId, manifest, stdout, stderr }) {
  return [
    "# pytest-dsl Build Log",
    "",
    `Build ID: ${manifest.buildId || buildId}`,
    `Status: ${manifest.status || "unknown"}`,
    `Started At: ${manifest.startedAt || "-"}`,
    `Completed At: ${manifest.completedAt || "-"}`,
    `Duration Ms: ${manifest.durationMs ?? "-"}`,
    `Exit Code: ${manifest.exitCode ?? "-"}`,
    `Signal: ${manifest.signal ?? "-"}`,
    `Command: ${manifest.command || "-"}`,
    `Allure Results: ${manifest.allureResultsDir || "-"}`,
    `Allure Report: ${manifest.allureReportDir || "-"}`,
    `Report URL: ${manifest.reportUrl || "-"}`,
    "",
    "## stdout",
    stdout || "(empty)\n",
    "## stderr",
    stderr || "(empty)\n",
    "## manifest",
    JSON.stringify(manifest, null, 2),
    "",
  ].join("\n");
}

function assertDirectoryHasEntries(directory, label) {
  if (!fs.existsSync(directory) || !fs.statSync(directory).isDirectory()) {
    throw new Error(`${label} does not exist: ${directory}`);
  }
  if (fs.readdirSync(directory).length === 0) {
    throw new Error(`${label} is empty: ${directory}`);
  }
}

function findGeneratedReportHtml(reportDir) {
  const preferred = path.join(reportDir, "index.html");
  if (fs.existsSync(preferred) && fs.statSync(preferred).isFile()) {
    return preferred;
  }
  const matches = [];
  const visit = (directory) => {
    fs.readdirSync(directory, { withFileTypes: true }).forEach((entry) => {
      const entryPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        visit(entryPath);
        return;
      }
      if (entry.isFile() && /\.html?$/i.test(entry.name)) {
        matches.push(entryPath);
      }
    });
  };
  visit(reportDir);
  if (matches.length === 0) {
    throw new Error(`Allure report export did not create an HTML file in ${reportDir}`);
  }
  return matches.sort((left, right) => left.localeCompare(right))[0];
}

function yamlArgs(yamlVars) {
  return yamlVars.flatMap((item) => ["--yaml-vars", item]);
}

function normalizeYamlVars(yamlVars) {
  return (Array.isArray(yamlVars) ? yamlVars : [])
    .map(normalizeRelative)
    .filter(Boolean);
}

function normalizeSelectedSuiteIds(selectedSuiteIds) {
  return (Array.isArray(selectedSuiteIds) ? selectedSuiteIds : [])
    .map((item) => String(item || "").trim())
    .filter(Boolean);
}

function normalizeRelative(relativePath) {
  const normalized = normalizePath(relativePath);
  if (!normalized || normalized.startsWith("/") || normalized.includes("../")) {
    throw new Error(`Invalid project-relative path: ${relativePath}`);
  }
  return normalized;
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

function executionEnv(extraEnv, platform = process.platform) {
  const packageRoot = path.resolve(__dirname, "..", "..", "..");
  const env = mergeEnvironment(process.env, extraEnv, platform);
  const bufferedEnv = mergeEnvironment(env, {
    PYTHONUNBUFFERED: "1",
  }, platform);
  if (!isDirectory(path.join(packageRoot, "pytest_dsl"))) {
    return bufferedEnv;
  }
  const existingPythonPath = bufferedEnv.PYTHONPATH || "";
  const delimiter = platform === "win32" ? ";" : path.delimiter;
  return mergeEnvironment(bufferedEnv, {
    PYTHONPATH: existingPythonPath
      ? `${packageRoot}${delimiter}${existingPythonPath}`
      : packageRoot,
  }, platform);
}

function isDirectory(directory) {
  try {
    return fs.statSync(directory).isDirectory();
  } catch {
    return false;
  }
}

function executableName(name) {
  return process.platform === "win32" ? `${name}.cmd` : name;
}

function sanitizeId(value) {
  const normalized = String(value || "").replace(/[^a-zA-Z0-9_.-]/g, "_");
  if (!normalized) {
    throw new Error("buildId is required");
  }
  return normalized;
}

function sanitizeExportFilePart(value) {
  return sanitizeId(value || "build").replace(/[.]+/g, "_");
}

function normalizePath(filePath) {
  return String(filePath || "").replace(/\\/g, "/");
}

function emit(callbacks, event) {
  if (callbacks && typeof callbacks.onEvent === "function") {
    callbacks.onEvent(event);
  }
}

module.exports = {
  createBuildPlan,
  defaultAllureReportExportName,
  defaultBuildLogExportName,
  exportAllureReportFile,
  exportBuildLogs,
  hasRunningBuild,
  startBuildTask,
  stopBuildTask,
};
