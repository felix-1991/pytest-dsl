const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const yaml = require("js-yaml");

const root = path.resolve(__dirname, "..");
const repoRoot = path.resolve(root, "..");
const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
const workflowPath = path.join(repoRoot, ".github", "workflows", "electron-gui-package.yml");
const buildResourceDir = path.join(root, "build");

function targetNames(config) {
  return (config.target || []).map((target) => (typeof target === "string" ? target : target.target));
}

function targetArchs(config, targetName) {
  const target = (config.target || []).find((item) => {
    return typeof item === "string" ? item === targetName : item.target === targetName;
  });
  return target && Array.isArray(target.arch) ? target.arch : [];
}

test("electron gui package metadata exposes local packaging commands and builder targets", () => {
  assert.equal(packageJson.private, true);
  assert.equal(packageJson.main, "main.js");
  assert.equal(packageJson.scripts.test, "node --test --test-concurrency=1");
  assert.equal(packageJson.scripts.package, "npm run build:editor && rimraf dist && electron-builder --publish never");
  assert.equal(
    packageJson.scripts["package:mac"],
    "npm run build:editor && rimraf dist && electron-builder --mac dmg zip --x64 --arm64 --publish never",
  );
  assert.equal(
    packageJson.scripts["package:win:x64"],
    "npm run build:editor && rimraf dist && electron-builder --win nsis zip --x64 --publish never",
  );
  assert.equal(
    packageJson.scripts["package:win:arm64"],
    "npm run build:editor && rimraf dist && electron-builder --win nsis zip --arm64 --publish never",
  );
  assert.equal(
    packageJson.scripts["package:linux"],
    "npm run build:editor && rimraf dist && electron-builder --linux AppImage deb --x64 --publish never",
  );

  assert.ok(packageJson.devDependencies["electron-builder"]);
  assert.ok(packageJson.devDependencies.electron);
  assert.ok(packageJson.devDependencies.rimraf);
  assert.equal(packageJson.dependencies.electron, undefined);

  const build = packageJson.build;
  assert.equal(build.appId, "io.pytestdsl.electronGui");
  assert.equal(build.productName, "Pytest DSL Studio");
  assert.equal(build.executableName, "pytest-dsl-studio");
  assert.equal(build.directories.output, "dist");
  assert.equal(build.directories.buildResources, "build");
  assert.equal(build.asar, true);
  assert.equal(build.publish, null);
  assert.deepEqual(build.electronDownload, {
    mirrorOptions: {
      mirror: "https://npmmirror.com/mirrors/electron/",
    },
  });
  assert.ok(build.files.includes("main.js"));
  assert.ok(build.files.includes("preload.js"));
  assert.ok(build.files.includes("src/**/*"));
  assert.ok(build.files.includes("package.json"));
  assert.ok(build.files.includes("!test{,/**}"));
  assert.ok(build.files.includes("!scripts{,/**}"));
  assert.ok(build.files.includes("!dist{,/**}"));
  assert.ok(build.files.includes("!.pytest-dsl-gui{,/**}"));

  assert.equal(build.mac.icon, "icon.icns");
  assert.deepEqual(targetNames(build.mac).sort(), ["dmg", "zip"]);
  assert.deepEqual(targetArchs(build.mac, "dmg").sort(), ["arm64", "x64"]);
  assert.deepEqual(targetArchs(build.mac, "zip").sort(), ["arm64", "x64"]);
  assert.equal(build.win.icon, "icon.ico");
  assert.equal(build.win.artifactName, "pytest-dsl-studio-${version}-win-${arch}.${ext}");
  assert.deepEqual(targetNames(build.win).sort(), ["nsis", "zip"]);
  assert.deepEqual(targetArchs(build.win, "nsis").sort(), ["arm64", "x64"]);
  assert.deepEqual(targetArchs(build.win, "zip").sort(), ["arm64", "x64"]);
  assert.equal(build.linux.icon, "icons");
  assert.deepEqual(targetNames(build.linux).sort(), ["AppImage", "deb"]);
  assert.deepEqual(targetArchs(build.linux, "AppImage"), ["x64"]);
  assert.deepEqual(targetArchs(build.linux, "deb"), ["x64"]);
  assert.equal(build.nsis.artifactName, "pytest-dsl-studio-${version}-win-${arch}-setup.${ext}");
  assert.equal(build.nsis.shortcutName, "Pytest DSL Studio");
  assert.equal(build.nsis.createDesktopShortcut, "always");
  assert.equal(build.nsis.createStartMenuShortcut, true);
  assert.equal(build.nsis.include, "installer.nsh");
  assert.equal(build.nsis.installerIcon, "installerIcon.ico");
  assert.equal(build.nsis.uninstallerIcon, "uninstallerIcon.ico");
});

test("electron gui packaging ships branded icon resources for all desktop targets", () => {
  for (const fileName of [
    "icon.svg",
    "icon.ico",
    "icon.icns",
    "installerIcon.ico",
    "uninstallerIcon.ico",
    "icons/32x32.png",
    "icons/128x128.png",
    "icons/256x256.png",
    "icons/512x512.png",
  ]) {
    assert.ok(fs.existsSync(path.join(buildResourceDir, fileName)), `${fileName} should exist`);
  }
});

test("nsis install repair avoids stale start menu shortcuts during finish launch", () => {
  const include = fs.readFileSync(path.join(buildResourceDir, "installer.nsh"), "utf8");

  assert.match(include, /!macro customInstall/);
  assert.match(include, /CRCCheck off/);
  assert.match(include, /Delete "\$newStartMenuLink"/);
  assert.match(include, /CreateShortCut "\$newStartMenuLink" "\$appExe"/);
  assert.match(include, /WinShell::SetLnkAUMI "\$newStartMenuLink" "\$\{APP_ID\}"/);
  assert.match(include, /StrCpy \$launchLink "\$appExe"/);
});

test("github workflow packages electron gui for macos windows x64 windows arm64 and linux", () => {
  const workflow = yaml.load(fs.readFileSync(workflowPath, "utf8"));
  const packageJob = workflow.jobs.package;
  const matrix = packageJob.strategy.matrix.include;
  const entries = Object.fromEntries(matrix.map((entry) => [entry.name, entry]));

  assert.equal(workflow.name, "Electron GUI Package");
  assert.ok(Object.hasOwn(workflow.on, "workflow_dispatch"));
  assert.ok(workflow.on.push.paths.includes("electron-gui/**"));
  assert.ok(workflow.on.pull_request.paths.includes(".github/workflows/electron-gui-package.yml"));
  assert.equal(workflow.permissions.contents, "read");
  assert.equal(packageJob.strategy["fail-fast"], false);

  assert.deepEqual(Object.keys(entries).sort(), ["linux", "macos", "windows-arm64", "windows-x64"]);
  assert.deepEqual(entries.macos, {
    name: "macos",
    os: "macos-latest",
    script: "package:mac",
    artifact: "electron-gui-macos",
  });
  assert.deepEqual(entries["windows-x64"], {
    name: "windows-x64",
    os: "windows-latest",
    script: "package:win:x64",
    artifact: "electron-gui-windows-x64",
  });
  assert.deepEqual(entries["windows-arm64"], {
    name: "windows-arm64",
    os: "windows-latest",
    script: "package:win:arm64",
    artifact: "electron-gui-windows-arm64",
  });
  assert.deepEqual(entries.linux, {
    name: "linux",
    os: "ubuntu-latest",
    script: "package:linux",
    artifact: "electron-gui-linux",
  });

  const steps = packageJob.steps;
  assert.ok(steps.some((step) => step.uses === "actions/checkout@v6"));
  assert.ok(
    steps.some(
      (step) =>
        step.uses === "actions/setup-node@v6" &&
        step.with["node-version"] === 20 &&
        step.with.cache === "npm" &&
        step.with["cache-dependency-path"] === "electron-gui/package-lock.json",
    ),
  );
  assert.ok(steps.some((step) => step.run === "npm ci --prefix electron-gui"));
  assert.ok(steps.some((step) => step.run === "npm run check --prefix electron-gui"));
  assert.ok(
    steps.some(
      (step) =>
        step.name === "Package Electron GUI" &&
        step.run === "npm run ${{ matrix.script }} --prefix electron-gui" &&
        step.env.CSC_IDENTITY_AUTO_DISCOVERY === "false",
    ),
  );
  assert.ok(
    steps.some(
      (step) =>
        step.uses === "actions/upload-artifact@v7" &&
        step.with.name === "${{ matrix.artifact }}" &&
        step.with.path.includes("electron-gui/dist/*") &&
        step.with.path.includes("!electron-gui/dist/*-unpacked/**") &&
        step.with["if-no-files-found"] === "error",
    ),
  );
});

test("packaged app documents that runtime prerequisites are external", () => {
  const readme = fs.readFileSync(path.join(repoRoot, "README.md"), "utf8");
  const exampleReadme = fs.readFileSync(
    path.join(repoRoot, "examples", "gui_validation", "README.md"),
    "utf8",
  );

  assert.match(readme, /项目.*\.venv/);
  assert.match(readme, /运行环境.*Python/);
  assert.match(readme, /Allure 3.*外部/);

  assert.match(exampleReadme, /配置.*运行环境/);
  assert.match(exampleReadme, /不会内置 Python 或 Allure/);
});
