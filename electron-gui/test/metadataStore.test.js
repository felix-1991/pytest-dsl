const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  metadataPath,
  readMetadata,
  updateRuntimeMetadata,
  writeMetadata
} = require("../src/services/metadataStore");

function makeTempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "pytest-dsl-gui-metadata-"));
}

function writeRawMetadata(projectRoot, metadata) {
  const metadataDir = path.join(projectRoot, ".pytest-dsl-gui");
  fs.mkdirSync(metadataDir, { recursive: true });
  fs.writeFileSync(
    path.join(metadataDir, "metadata.json"),
    `${JSON.stringify(metadata, null, 2)}\n`,
    "utf8"
  );
}

test("legacy metadata gains null runtime defaults without losing existing values", (t) => {
  const root = makeTempProject();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  writeRawMetadata(root, {
    version: 1,
    lastOpenedFile: "tests/existing.dsl",
    recentFiles: ["tests/existing.dsl"],
    layout: {
      leftWidth: 420,
      rightWidth: 516
    },
    updatedAt: "2026-06-22T00:00:00.000Z"
  });

  const metadata = readMetadata(root);

  assert.deepEqual(metadata.runtime, {
    pythonExecutable: null,
    allureExecutable: null
  });
  assert.equal(metadata.lastOpenedFile, "tests/existing.dsl");
  assert.deepEqual(metadata.layout, {
    leftWidth: 420,
    rightWidth: 516
  });

  updateRuntimeMetadata(root, {
    pythonExecutable: "/opt/python/bin/python",
    unsupportedExecutable: "/opt/unsupported/bin/tool",
    lastOpenedFile: "tests/replacement.dsl",
    layout: {
      leftWidth: 1,
      rightWidth: 1
    }
  });
  const updated = readMetadata(root);
  const onDisk = JSON.parse(fs.readFileSync(metadataPath(root), "utf8"));

  assert.equal(updated.lastOpenedFile, "tests/existing.dsl");
  assert.deepEqual(updated.layout, {
    leftWidth: 420,
    rightWidth: 516
  });
  assert.deepEqual(updated.runtime, {
    pythonExecutable: "/opt/python/bin/python",
    allureExecutable: null
  });
  assert.deepEqual(onDisk.runtime, updated.runtime);
  assert.equal(
    Object.prototype.hasOwnProperty.call(onDisk.runtime, "unsupportedExecutable"),
    false
  );
});

test("Python and Allure runtime overrides save independently", (t) => {
  const root = makeTempProject();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));

  updateRuntimeMetadata(root, {
    pythonExecutable: "  /opt/python/bin/python  "
  });
  const withPython = readMetadata(root);

  assert.deepEqual(withPython.runtime, {
    pythonExecutable: "/opt/python/bin/python",
    allureExecutable: null
  });

  updateRuntimeMetadata(root, {
    allureExecutable: "  /opt/allure/bin/allure  "
  });
  const withAllure = readMetadata(root);

  assert.deepEqual(withAllure.runtime, {
    pythonExecutable: "/opt/python/bin/python",
    allureExecutable: "/opt/allure/bin/allure"
  });
});

test("resetting one runtime override preserves the other", (t) => {
  const root = makeTempProject();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  updateRuntimeMetadata(root, {
    pythonExecutable: "/opt/python/bin/python",
    allureExecutable: "/opt/allure/bin/allure"
  });
  const beforeReset = readMetadata(root);

  assert.deepEqual(beforeReset.runtime, {
    pythonExecutable: "/opt/python/bin/python",
    allureExecutable: "/opt/allure/bin/allure"
  });

  updateRuntimeMetadata(root, {
    pythonExecutable: null
  });
  const metadata = readMetadata(root);

  assert.deepEqual(metadata.runtime, {
    pythonExecutable: null,
    allureExecutable: "/opt/allure/bin/allure"
  });
});

test("runtime metadata converts blank and non-string overrides to null", (t) => {
  const root = makeTempProject();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));

  writeMetadata(root, {
    runtime: {
      pythonExecutable: "   ",
      allureExecutable: 42
    }
  });
  const metadata = readMetadata(root);

  assert.deepEqual(metadata.runtime, {
    pythonExecutable: null,
    allureExecutable: null
  });
});
