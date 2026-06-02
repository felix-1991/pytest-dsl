const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { randomUUID } = require("node:crypto");

const STRUCTURED_EVENT_PREFIX = "__PYTEST_DSL_GUI_EVENT__";
const runningTasks = new Map();

function createExecutionPlan(options) {
  const projectRoot = assertProjectRoot(options.projectRoot);
  const taskId = sanitizeTaskId(options.taskId || randomUUID());
  const mode = normalizeMode(options.mode);
  const relativePath = normalizeRelative(options.relativePath);
  const yamlVars = normalizeYamlVars(options.yamlVars);
  const source = describeSource(mode, relativePath, options.selection, options.debugScope);
  const target = materializeTaskFile(projectRoot, taskId, relativePath, {
    ...options,
    selection: source.kind === "selection" ? options.selection : null,
  });
  const command = commandForMode(mode, options);

  const args = commandArgs(mode, target.relativePath, yamlVars, source);

  return {
    taskId,
    mode,
    cwd: projectRoot,
    command,
    args,
    displayCommand: displayCommand(mode, source, yamlVars),
    targetPath: target.absolutePath,
    targetRelativePath: target.relativePath,
    source,
    cleanupDir: target.cleanupDir,
  };
}

function startExecutionTask(options, callbacks = {}) {
  const plan = createExecutionPlan(options);
  const env = executionEnv(options.env);
  const spawnTarget = options.commandOverride
    ? options.commandOverride
    : resolveSpawnTarget(plan, options, env);
  const command = spawnTarget.command;
  const args = spawnTarget.args;
  const startedAt = Date.now();

  if (runningTasks.has(plan.taskId)) {
    throw new Error(`Execution task is already running: ${plan.taskId}`);
  }

  emit(callbacks, {
    type: "started",
    taskId: plan.taskId,
    mode: plan.mode,
    command: plan.displayCommand,
    source: plan.source,
  });

  const child = spawn(command, args, {
    cwd: plan.cwd,
    env,
    windowsHide: true,
  });

  const task = {
    child,
    plan,
    stopped: false,
    killTimer: null,
    stdoutBuffer: "",
  };
  runningTasks.set(plan.taskId, task);

  child.stdout.on("data", (chunk) => {
    handleStdoutChunk(task, chunk.toString(), callbacks);
  });

  child.stderr.on("data", (chunk) => {
    emit(callbacks, {
      type: "stderr",
      taskId: plan.taskId,
      text: chunk.toString(),
    });
  });

  child.on("error", (error) => {
    emit(callbacks, {
      type: "stderr",
      taskId: plan.taskId,
      text: `${error.message}\n`,
    });
  });

  return new Promise((resolve) => {
    child.on("close", (exitCode, signal) => {
      const running = runningTasks.get(plan.taskId);
      const stopped = Boolean(running && running.stopped);
      if (running && running.killTimer) {
        clearTimeout(running.killTimer);
      }
      runningTasks.delete(plan.taskId);
      cleanupTaskDir(plan.cleanupDir);

      const result = {
        taskId: plan.taskId,
        mode: plan.mode,
        status: stopped ? "stopped" : exitCode === 0 ? "passed" : "failed",
        exitCode,
        signal,
        durationMs: Date.now() - startedAt,
      };
      emit(callbacks, {
        type: "completed",
        ...result,
      });
      resolve(result);
    });
  });
}

function sendExecutionCommand(taskId, command) {
  const normalized = sanitizeTaskId(taskId);
  const task = runningTasks.get(normalized);
  if (!task) {
    return { sent: false, reason: "not-running" };
  }
  if (!task.child.stdin || task.child.stdin.destroyed || !task.child.stdin.writable) {
    return { sent: false, reason: "stdin-unavailable" };
  }

  task.child.stdin.write(`${command}\n`);
  return { sent: true, taskId: normalized, command };
}

function stopExecutionTask(taskId) {
  const normalized = sanitizeTaskId(taskId);
  const task = runningTasks.get(normalized);
  if (!task) {
    return { stopped: false, reason: "not-running" };
  }

  task.stopped = true;
  task.child.kill("SIGTERM");
  task.killTimer = setTimeout(() => {
    if (runningTasks.has(normalized)) {
      task.child.kill("SIGKILL");
    }
  }, 1500);
  if (typeof task.killTimer.unref === "function") {
    task.killTimer.unref();
  }

  return { stopped: true, taskId: normalized };
}

function hasRunningTask(taskId) {
  return runningTasks.has(sanitizeTaskId(taskId));
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

function normalizeMode(mode) {
  if (["syntax", "run", "debug"].includes(mode)) {
    return mode;
  }
  throw new Error(`Unsupported execution mode: ${mode}`);
}

function normalizeRelative(relativePath) {
  const normalized = String(relativePath || "").replace(/\\/g, "/");
  if (!normalized || normalized.startsWith("/") || normalized.includes("../")) {
    throw new Error(`Invalid project-relative path: ${relativePath}`);
  }
  return normalized;
}

function normalizeYamlVars(yamlVars) {
  return (Array.isArray(yamlVars) ? yamlVars : [])
    .map(normalizeRelative)
    .filter(Boolean);
}

function materializeTaskFile(projectRoot, taskId, relativePath, options) {
  const sourceContent = selectedContent(options.selection) || options.content;
  if (typeof sourceContent !== "string") {
    throw new Error("content is required");
  }

  const runDir = path.join(projectRoot, ".pytest-dsl-gui", "runs", taskId);
  const targetPath = path.join(runDir, relativePath);
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, ensureTrailingNewline(sourceContent), "utf8");

  return {
    absolutePath: targetPath,
    relativePath: path.relative(projectRoot, targetPath).replace(/\\/g, "/"),
    cleanupDir: runDir,
  };
}

function selectedContent(selection) {
  if (!selection || typeof selection.content !== "string") {
    return null;
  }
  const content = selection.content.trimEnd();
  return content ? content : null;
}

function ensureTrailingNewline(content) {
  return content.endsWith("\n") ? content : `${content}\n`;
}

function describeSource(mode, relativePath, selection, debugScope) {
  const fromLineScope = mode === "debug" ? normalizeFromLineScope(debugScope) : null;
  if (fromLineScope) {
    return {
      kind: "fromLine",
      relativePath,
      startLine: fromLineScope.startLine,
      endLine: null,
      label: `${relativePath}:${fromLineScope.startLine}-end`,
    };
  }

  if (selection && selectedContent(selection)) {
    const startLine = Number(selection.startLine) || 1;
    const endLine = Number(selection.endLine) || startLine;
    return {
      kind: "selection",
      relativePath,
      startLine,
      endLine,
      label: `${relativePath}:${startLine}-${endLine}`,
    };
  }
  return {
    kind: "file",
    relativePath,
    startLine: null,
    endLine: null,
    label: relativePath,
  };
}

function normalizeFromLineScope(debugScope) {
  if (!debugScope || debugScope.kind !== "fromLine") {
    return null;
  }
  const startLine = Math.trunc(Number(debugScope.startLine));
  if (!Number.isFinite(startLine) || startLine < 1) {
    return null;
  }
  return { startLine };
}

function yamlArgs(yamlVars) {
  return yamlVars.flatMap((item) => ["--yaml-vars", item]);
}

function commandArgs(mode, relativePath, yamlVars, source) {
  if (mode === "syntax") {
    return ["syntax", relativePath];
  }
  if (mode === "debug") {
    const pauseArgs = source && source.kind === "fromLine"
      ? ["--pause-from-line", String(source.startLine)]
      : [];
    return [
      "debug",
      relativePath,
      ...pauseArgs,
      ...yamlArgs(yamlVars),
    ];
  }
  return [relativePath, ...yamlArgs(yamlVars)];
}

function commandForMode(mode, options = {}) {
  if (mode === "syntax" || mode === "debug") {
    return options.workbenchExecutable ||
      process.env.PYTEST_DSL_WORKBENCH ||
      "pytest-dsl-workbench";
  }
  return options.pytestExecutable ||
    process.env.PYTEST_DSL_CLI ||
    "pytest-dsl";
}

function displayCommand(mode, source, yamlVars) {
  if (mode === "syntax") {
    return `syntax ${source.label}`;
  }
  const args = yamlVars.length > 0
    ? ` ${yamlArgs(yamlVars).join(" ")}`
    : "";
  const prefix = mode === "debug" ? "debug" : "pytest-dsl";
  return `${prefix} ${source.label}${args}`;
}

function handleStdoutChunk(task, text, callbacks) {
  task.stdoutBuffer += text;
  const lines = task.stdoutBuffer.split(/\r?\n/);
  task.stdoutBuffer = lines.pop() || "";

  lines.forEach((line) => handleStdoutLine(task, line, callbacks));
}

function handleStdoutLine(task, line, callbacks) {
  if (line.startsWith(STRUCTURED_EVENT_PREFIX)) {
    const event = parseStructuredEvent(task, line.slice(STRUCTURED_EVENT_PREFIX.length));
    if (event) {
      emit(callbacks, event);
    }
    return;
  }

  emit(callbacks, {
    type: "stdout",
    taskId: task.plan.taskId,
    text: `${line}\n`,
  });
}

function parseStructuredEvent(task, rawPayload) {
  let payload;
  try {
    payload = JSON.parse(rawPayload);
  } catch {
    return {
      type: "stdout",
      taskId: task.plan.taskId,
      text: `${STRUCTURED_EVENT_PREFIX}${rawPayload}\n`,
    };
  }

  if (payload.type === "debug_step") {
    const originalLine = Number(payload.line) || null;
    return {
      type: "debug-step",
      taskId: task.plan.taskId,
      phase: payload.phase || "start",
      line: mapSourceLine(task.plan.source, originalLine),
      originalLine,
      nodeType: payload.nodeType || null,
      description: payload.description || "",
      status: payload.status || null,
      error: payload.error || null,
      duration: payload.duration || null,
    };
  }

  return {
    type: payload.type || "event",
    taskId: task.plan.taskId,
    payload,
  };
}

function mapSourceLine(source, line) {
  if (!line) {
    return null;
  }
  if (source && source.kind === "selection" && source.startLine) {
    return source.startLine + line - 1;
  }
  return line;
}

function resolveSpawnTarget(plan, options = {}, env = process.env) {
  if (isExecutableAvailable(plan.command, env)) {
    return {
      command: plan.command,
      args: plan.args,
    };
  }

  if (plan.mode === "syntax" || plan.mode === "debug") {
    return {
      command: fallbackPythonExecutable(options),
      args: ["-m", "pytest_dsl.workbench.runner", ...plan.args],
    };
  }

  return {
    command: fallbackPythonExecutable(options),
    args: ["-m", "pytest_dsl.cli", ...plan.args],
  };
}

function isExecutableAvailable(command, env = process.env) {
  if (!command || command.includes("/") || command.includes("\\")) {
    return Boolean(command && fs.existsSync(command));
  }

  const pathValue = env.PATH || env.Path || env.path || "";
  const pathExts = process.platform === "win32"
    ? (env.PATHEXT || ".EXE;.CMD;.BAT;.COM").split(";")
    : [""];
  return pathValue.split(path.delimiter).some((directory) =>
    pathExts.some((extension) =>
      fs.existsSync(path.join(directory, `${command}${extension}`)),
    ),
  );
}

function fallbackPythonExecutable(options = {}) {
  return options.pythonExecutable ||
    process.env.PYTEST_DSL_PYTHON ||
    process.env.PYTHON ||
    "python";
}

function executionEnv(extraEnv) {
  const packageRoot = path.resolve(__dirname, "..", "..", "..");
  const existingPythonPath = process.env.PYTHONPATH || "";
  return {
    ...process.env,
    ...extraEnv,
    PYTHONUNBUFFERED: "1",
    PYTHONPATH: existingPythonPath
      ? `${packageRoot}${path.delimiter}${existingPythonPath}`
      : packageRoot,
  };
}

function sanitizeTaskId(taskId) {
  const value = String(taskId || "").replace(/[^a-zA-Z0-9_.-]/g, "_");
  if (!value) {
    throw new Error("taskId is required");
  }
  return value;
}

function cleanupTaskDir(directory) {
  if (!directory) {
    return;
  }
  fs.rmSync(directory, { recursive: true, force: true });
}

function emit(callbacks, event) {
  if (callbacks && typeof callbacks.onEvent === "function") {
    callbacks.onEvent(event);
  }
}

module.exports = {
  createExecutionPlan,
  hasRunningTask,
  sendExecutionCommand,
  startExecutionTask,
  stopExecutionTask,
};
