const fs = require("node:fs");
const path = require("node:path");

function resolvePythonCommand(projectRoot, env = process.env, options = {}) {
  const commands = resolvePythonCommands(projectRoot, env);
  return options.all ? commands : commands[0];
}

function resolvePythonCommands(projectRoot, env = process.env) {
  if (env.PYTEST_DSL_PYTHON) {
    return [env.PYTEST_DSL_PYTHON];
  }
  if (env.PYTHON) {
    return [env.PYTHON];
  }

  const venvPython = findProjectVenvPython(projectRoot);
  if (venvPython) {
    return [venvPython, "python", "python3"];
  }
  return ["python", "python3"];
}

function findProjectVenvPython(projectRoot) {
  if (!projectRoot) {
    return null;
  }
  const root = path.resolve(projectRoot);
  const candidates = process.platform === "win32"
    ? [
        path.join(root, ".venv", "Scripts", "python.exe"),
        path.join(root, "venv", "Scripts", "python.exe"),
      ]
    : [
        path.join(root, ".venv", "bin", "python"),
        path.join(root, "venv", "bin", "python"),
      ];

  return candidates.find((candidate) => {
    try {
      return fs.existsSync(candidate) && fs.statSync(candidate).isFile();
    } catch {
      return false;
    }
  }) || null;
}

module.exports = {
  resolvePythonCommand,
  resolvePythonCommands,
};
