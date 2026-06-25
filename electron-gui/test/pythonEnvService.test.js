const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { updateRuntimeMetadata } = require("../src/services/metadataStore");
const {
  isExecutableAvailable,
  mergeEnvironment,
  resolvePythonCommand,
  resolvePythonCommands,
  resolvePythonRuntimeTarget,
  resolvePythonTarget,
  resolvePythonTargets,
} = require("../src/services/pythonEnvService");

function makeTempProject(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-python-env-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}

function writeExecutable(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, "test executable fixture\n", "utf8");
  fs.chmodSync(filePath, 0o755);
  return filePath;
}

function writeScript(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
  fs.chmodSync(filePath, 0o755);
  return filePath;
}

function writeNodeCommand(root, name, source) {
  const scriptPath = path.join(root, `${name}.js`);
  fs.writeFileSync(scriptPath, source, "utf8");
  if (process.platform === "win32") {
    const commandPath = path.join(root, `${name}.cmd`);
    fs.writeFileSync(commandPath, `@echo off\r\n"${process.execPath}" "${scriptPath}" %*\r\n`, "utf8");
    return commandPath;
  }
  const commandPath = path.join(root, name);
  fs.writeFileSync(commandPath, `#!/bin/sh\nexec "${process.execPath}" "${scriptPath}" "$@"\n`, "utf8");
  fs.chmodSync(commandPath, 0o755);
  return commandPath;
}

function projectPython(root, environment = ".venv", platform = "linux") {
  return platform === "win32"
    ? path.join(root, environment, "Scripts", "python.exe")
    : path.join(root, environment, "bin", "python");
}

test("mergeEnvironment canonicalizes Windows path-like keys without duplicates", () => {
  const merged = mergeEnvironment({
    Path: "base-path",
    PATH: "stale-base-path",
    PathExt: ".CMD",
    PythonPath: "base-pythonpath",
    Feature: "base-feature",
    FEATURE: "stale-feature",
  }, {
    path: "override-path",
    PATHEXT: ".EXE;.CMD",
    pythonpath: "override-pythonpath",
    feature: "override-feature",
  }, "win32");

  assert.equal(merged.PATH, "override-path");
  assert.equal(merged.PATHEXT, ".EXE;.CMD");
  assert.equal(merged.PYTHONPATH, "override-pythonpath");
  assert.equal(merged.feature, "override-feature");
  assert.deepEqual(
    Object.keys(merged).filter((key) => (
      ["path", "pathext", "pythonpath", "feature"].includes(key.toLowerCase())
    )),
    ["PATH", "PATHEXT", "PYTHONPATH", "feature"],
  );
});

test("mergeEnvironment keeps POSIX environment key casing distinct", () => {
  assert.deepEqual(mergeEnvironment({ Path: "base" }, { PATH: "override" }, "linux"), {
    Path: "base",
    PATH: "override",
  });
});

test("saved project Python is an exclusive configured target", (t) => {
  const root = makeTempProject(t);
  const configured = writeExecutable(path.join(root, "runtime", "python"));
  writeExecutable(projectPython(root));
  updateRuntimeMetadata(root, { pythonExecutable: `  ${configured}  ` });

  assert.deepEqual(resolvePythonTargets(root, {
    PYTEST_DSL_PYTHON: "/env/pytest-dsl-python",
    PYTHON: "/env/python",
    PATH: "/bin",
  }, { platform: "linux", skipCommonPaths: true }), [{
    command: configured,
    args: [],
    source: "project-config",
    configured: true,
  }]);
});

test("options.pythonExecutable is an exclusive configured override", (t) => {
  const root = makeTempProject(t);
  const saved = writeExecutable(path.join(root, "saved", "python"));
  const explicit = writeExecutable(path.join(root, "explicit", "python"));
  updateRuntimeMetadata(root, { pythonExecutable: saved });

  assert.deepEqual(resolvePythonTargets(root, {
    PYTEST_DSL_PYTHON: "/env/python",
    PATH: "/bin",
  }, {
    platform: "linux",
    pythonExecutable: ` ${explicit} `,
  }), [{
    command: explicit,
    args: [],
    source: "project-config",
    configured: true,
  }]);
});

test("invalid saved Python fails without falling back", (t) => {
  const root = makeTempProject(t);
  const missing = path.join(root, "missing", "python");
  const environmentPython = writeExecutable(path.join(root, "env", "python"));
  updateRuntimeMetadata(root, { pythonExecutable: missing });

  assert.throws(
    () => resolvePythonTarget(root, {
      PYTEST_DSL_PYTHON: environmentPython,
      PATH: path.dirname(environmentPython),
    }, { platform: "linux", skipCommonPaths: true }),
    (error) => {
      assert.match(
        error.message,
        /Configured Python executable does not exist or is not executable/,
      );
      assert.match(error.message, /Configuration > Runtime/);
      assert.match(error.message, new RegExp(missing.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
      return true;
    },
  );
});

test("invalid options.pythonExecutable fails without falling back", (t) => {
  const root = makeTempProject(t);
  const missing = path.join(root, "missing-explicit", "python");
  const environmentPython = writeExecutable(path.join(root, "env", "python"));

  assert.throws(
    () => resolvePythonTargets(root, {
      PYTEST_DSL_PYTHON: environmentPython,
      PATH: path.dirname(environmentPython),
    }, {
      platform: "linux",
      pythonExecutable: missing,
    }),
    /Configured Python executable does not exist or is not executable/,
  );
});

test("Windows configured Python rejects extensions outside PATHEXT", (t) => {
  const root = makeTempProject(t);
  const configured = path.join(root, "runtime", "python.txt");
  fs.mkdirSync(path.dirname(configured), { recursive: true });
  fs.writeFileSync(configured, "not a Windows executable", "utf8");

  assert.throws(
    () => resolvePythonTargets(root, {
      PATH: "",
      PATHEXT: ".EXE",
    }, {
      platform: "win32",
      pythonExecutable: configured,
    }),
    /Configured Python executable does not exist or is not executable/,
  );
});

test("project virtualenv precedes environment candidates during auto detection", (t) => {
  const root = makeTempProject(t);
  const pytestDslPython = writeExecutable(path.join(root, "env", "pytest-dsl-python"));
  const python = writeExecutable(path.join(root, "env", "python"));
  const venvPython = writeExecutable(projectPython(root));

  assert.deepEqual(
    resolvePythonTargets(root, {
      PYTEST_DSL_PYTHON: ` ${pytestDslPython} `,
      PYTHON: python,
      PATH: "",
    }, { platform: "linux", skipCommonPaths: true }).slice(0, 3),
    [
      { command: venvPython, args: [], source: "project-venv", configured: false },
      { command: pytestDslPython, args: [], source: "environment", configured: false },
      { command: python, args: [], source: "environment", configured: false },
    ],
  );
});

test("project .venv precedes venv and resolves with an empty PATH", (t) => {
  const root = makeTempProject(t);
  const dotVenvPython = writeExecutable(projectPython(root, ".venv"));
  writeExecutable(projectPython(root, "venv"));

  assert.deepEqual(resolvePythonTarget(root, { PATH: "" }, { platform: "linux", skipCommonPaths: true }), {
    command: dotVenvPython,
    args: [],
    source: "project-venv",
    configured: false,
  });
});

test("project .venv and venv are both discovered before environment candidates", (t) => {
  const root = makeTempProject(t);
  const dotVenvPython = writeExecutable(projectPython(root, ".venv"));
  const venvPython = writeExecutable(projectPython(root, "venv"));
  const envPython = writeExecutable(path.join(root, "env", "python"));

  assert.deepEqual(
    resolvePythonTargets(root, {
      PYTEST_DSL_PYTHON: envPython,
      PATH: "",
    }, { platform: "linux", skipCommonPaths: true }).slice(0, 3),
    [
      { command: dotVenvPython, args: [], source: "project-venv", configured: false },
      { command: venvPython, args: [], source: "project-venv", configured: false },
      { command: envPython, args: [], source: "environment", configured: false },
    ],
  );
});

test("project venv is discovered when .venv is absent and PATH is empty", (t) => {
  const root = makeTempProject(t);
  const venvPython = writeExecutable(projectPython(root, "venv"));

  assert.equal(
    resolvePythonTarget(root, { PATH: "" }, { platform: "linux", skipCommonPaths: true }).command,
    venvPython,
  );
});

test("runtime preflight requires Python 3.9 or newer", (t) => {
  const root = makeTempProject(t);
  writeScript(projectPython(root), [
    "#!/bin/sh",
    "echo 'Python 3.9 or newer is required; current Python is 3.8.18' >&2",
    "exit 1",
    "",
  ].join("\n"));

  assert.throws(
    () => resolvePythonRuntimeTarget(root, { PATH: "" }, { platform: "linux", skipCommonPaths: true }),
    /Python 3\.9.*pip install pytest-dsl/,
  );
});

test("runtime preflight retries a later candidate when the first lacks pytest-dsl", (t) => {
  const root = makeTempProject(t);
  const badPython = writeScript(path.join(root, "bin-one", "python3"), [
    "#!/bin/sh",
    "echo \"ModuleNotFoundError: No module named 'pytest_dsl'\" >&2",
    "exit 1",
    "",
  ].join("\n"));
  const goodPython = writeScript(path.join(root, "bin-two", "python"), [
    "#!/bin/sh",
    "echo '/ok/python'",
    "",
  ].join("\n"));

  const target = resolvePythonRuntimeTarget(root, {
    PATH: `${path.dirname(badPython)}${path.delimiter}${path.dirname(goodPython)}`,
  }, { platform: "linux", skipCommonPaths: true, skipShellPathDiscovery: true });

  assert.equal(target.command, goodPython);
});

test("runtime preflight allows slow Python dependency probes", (t) => {
  const root = makeTempProject(t);
  const slowPython = writeNodeCommand(root, "slow-python", [
    "setTimeout(() => {",
    "  console.log(process.argv[1]);",
    "}, 6000);",
    "",
  ].join("\n"));
  updateRuntimeMetadata(root, { pythonExecutable: slowPython });

  const target = resolvePythonRuntimeTarget(root, { PATH: "" });

  assert.equal(target.command, slowPython);
});

test("POSIX runtime detection can use login shell PATH without fixed install paths", (t) => {
  const root = makeTempProject(t);
  const shellBin = path.join(root, "shell-bin");
  const shellPython = writeExecutable(path.join(shellBin, "python3"));

  assert.deepEqual(resolvePythonTarget(root, { PATH: "" }, {
    platform: "linux",
    skipCommonPaths: true,
    shellPathProvider: () => shellBin,
  }), {
    command: shellPython,
    args: [],
    source: "path",
    configured: false,
  });
});

test("POSIX fallback order is python3 then python", (t) => {
  const root = makeTempProject(t);

  assert.deepEqual(resolvePythonTargets(root, { PATH: "" }, { platform: "linux", skipCommonPaths: true }), [
    { command: "python3", args: [], source: "path", configured: false },
    { command: "python", args: [], source: "path", configured: false },
  ]);
});

test("Windows targets include python and py -3", (t) => {
  const root = makeTempProject(t);

  assert.deepEqual(resolvePythonTargets(root, { PATH: "" }, { platform: "win32", skipCommonPaths: true }), [
    { command: "python", args: [], source: "path", configured: false },
    { command: "py", args: ["-3"], source: "path", configured: false },
  ]);
});

test("Windows resolution selects py with -3 through mixed-case Path and PathExt", (t) => {
  const root = makeTempProject(t);
  const bin = path.join(root, "bin");
  fs.mkdirSync(bin, { recursive: true });
  fs.writeFileSync(path.join(bin, "py.CUSTOM"), "windows launcher", "utf8");

  const target = resolvePythonTarget(root, {
    Path: bin,
    PathExt: ".CuStOm",
  }, { platform: "win32", skipCommonPaths: true });

  assert.equal(target.command.toLowerCase(), path.join(bin, "py.custom").toLowerCase());
  assert.deepEqual(target.args, ["-3"]);
  assert.equal(target.source, "path");
  assert.equal(target.configured, false);
});

test("duplicate normalized candidates are removed without changing order", (t) => {
  const root = makeTempProject(t);

  assert.deepEqual(resolvePythonTargets(root, {
    PYTEST_DSL_PYTHON: " python3 ",
    PYTHON: "python3",
    PATH: "",
  }, { platform: "linux", skipCommonPaths: true }), [
    { command: "python3", args: [], source: "environment", configured: false },
    { command: "python", args: [], source: "path", configured: false },
  ]);
});

test("Windows duplicate candidates normalize separators and case", (t) => {
  const root = makeTempProject(t);

  assert.deepEqual(resolvePythonTargets(root, {
    PYTEST_DSL_PYTHON: "C:\\Tools\\Python.EXE",
    PYTHON: "c:/tools/python.exe",
    PATH: "",
  }, { platform: "win32", skipCommonPaths: true }), [
    {
      command: "C:\\Tools\\Python.EXE",
      args: [],
      source: "environment",
      configured: false,
    },
    { command: "python", args: [], source: "path", configured: false },
    { command: "py", args: ["-3"], source: "path", configured: false },
  ]);
});

test("legacy command resolvers prefer project virtualenv before env and keep python-first fallback", (t) => {
  const root = makeTempProject(t);
  const venvPython = writeExecutable(projectPython(root));
  const env = { PYTEST_DSL_PYTHON: "/opt/custom/python", PATH: "" };
  const options = { platform: "linux", skipCommonPaths: true };

  assert.equal(resolvePythonCommand(root, env, options), venvPython);
  assert.deepEqual(resolvePythonCommands(root, env, options), [venvPython, "/opt/custom/python"]);
  assert.deepEqual(
    resolvePythonCommand(root, env, { ...options, all: true }),
    [venvPython, "/opt/custom/python"],
  );

  const noVenvRoot = makeTempProject(t);
  assert.deepEqual(resolvePythonCommands(noVenvRoot, env, options), ["/opt/custom/python"]);
  assert.deepEqual(resolvePythonCommands(noVenvRoot, { PATH: "" }, options), [
    "python",
    "python3",
  ]);
  assert.deepEqual(resolvePythonCommands(noVenvRoot, { PATH: "" }, { platform: "win32", skipCommonPaths: true }), [
    "python",
    "python3",
  ]);
});

test("isExecutableAvailable checks absolute paths and POSIX execute permission", (t) => {
  const root = makeTempProject(t);
  const executable = writeExecutable(path.join(root, "bin", "python3"));
  const nonExecutable = path.join(root, "bin", "plain-file.EXE");
  const textFile = path.join(root, "bin", "plain-file.txt");
  fs.writeFileSync(nonExecutable, "not executable", "utf8");
  fs.writeFileSync(textFile, "not a Windows executable", "utf8");

  assert.equal(isExecutableAvailable(executable, { PATH: "" }, "linux"), true);
  assert.equal(isExecutableAvailable(nonExecutable, { PATH: "" }, "linux"), false);
  assert.equal(
    isExecutableAvailable(nonExecutable, { PATH: "", pathext: ".exe" }, "win32"),
    true,
  );
  assert.equal(
    isExecutableAvailable(textFile, { PATH: "", PATHEXT: ".EXE" }, "win32"),
    false,
  );
  assert.equal(isExecutableAvailable(path.join(root, "missing"), { PATH: "" }, "linux"), false);
});

test("isExecutableAvailable searches PATH and Windows PATHEXT", (t) => {
  const root = makeTempProject(t);
  const bin = path.join(root, "bin");
  writeExecutable(path.join(bin, "python3"));
  fs.writeFileSync(path.join(bin, "python.CMD"), "windows shim", "utf8");
  fs.writeFileSync(path.join(bin, "python.txt"), "not executable", "utf8");

  assert.equal(isExecutableAvailable("python3", { PATH: bin }, "linux"), true);
  assert.equal(isExecutableAvailable("python", {
    PATH: bin,
    PATHEXT: ".CMD;.EXE",
  }, "win32"), true);
  assert.equal(isExecutableAvailable("python", {
    path: bin,
    pathext: ".cmd",
  }, "win32"), true);
  assert.equal(isExecutableAvailable("python.txt", {
    Path: bin,
    PathExt: ".EXE",
  }, "win32"), false);
  assert.equal(isExecutableAvailable("python", { PATH: "" }, "linux"), false);
});

test("resolvePythonTarget reports every checked command when none is usable", (t) => {
  const root = makeTempProject(t);

  assert.throws(
    () => resolvePythonTarget(root, { PATH: "" }, { platform: "linux", skipCommonPaths: true }),
    (error) => {
      assert.match(error.message, /Checked: python3, python/);
      assert.match(error.message, /Configuration > Runtime/);
      return true;
    },
  );
});
