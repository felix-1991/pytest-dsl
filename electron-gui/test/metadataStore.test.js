const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
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

test("legacy metadata gains null runtime defaults without losing existing values", () => {
  const root = makeTempProject();
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

  const updated = updateRuntimeMetadata(root, {
    pythonExecutable: "/opt/python/bin/python",
    lastOpenedFile: "tests/replacement.dsl",
    layout: {
      leftWidth: 1,
      rightWidth: 1
    }
  });

  assert.equal(updated.lastOpenedFile, "tests/existing.dsl");
  assert.deepEqual(updated.layout, {
    leftWidth: 420,
    rightWidth: 516
  });
});

test("Python and Allure runtime overrides save independently", () => {
  const root = makeTempProject();

  const withPython = updateRuntimeMetadata(root, {
    pythonExecutable: "  /opt/python/bin/python  "
  });
  const withAllure = updateRuntimeMetadata(root, {
    allureExecutable: "  /opt/allure/bin/allure  "
  });

  assert.deepEqual(withPython.runtime, {
    pythonExecutable: "/opt/python/bin/python",
    allureExecutable: null
  });
  assert.deepEqual(withAllure.runtime, {
    pythonExecutable: "/opt/python/bin/python",
    allureExecutable: "/opt/allure/bin/allure"
  });
  assert.deepEqual(readMetadata(root).runtime, withAllure.runtime);
});

test("resetting one runtime override preserves the other", () => {
  const root = makeTempProject();
  updateRuntimeMetadata(root, {
    pythonExecutable: "/opt/python/bin/python",
    allureExecutable: "/opt/allure/bin/allure"
  });

  const metadata = updateRuntimeMetadata(root, {
    pythonExecutable: null
  });

  assert.deepEqual(metadata.runtime, {
    pythonExecutable: null,
    allureExecutable: "/opt/allure/bin/allure"
  });
});

test("runtime metadata converts blank and non-string overrides to null", () => {
  const root = makeTempProject();

  const metadata = writeMetadata(root, {
    runtime: {
      pythonExecutable: "   ",
      allureExecutable: 42
    }
  });

  assert.deepEqual(metadata.runtime, {
    pythonExecutable: null,
    allureExecutable: null
  });
});
