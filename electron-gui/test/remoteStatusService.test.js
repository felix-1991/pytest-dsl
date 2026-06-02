const assert = require("node:assert/strict");
const http = require("node:http");
const test = require("node:test");

const {
  checkRemoteServers,
  normalizeServers,
  parseKeywordNames
} = require("../src/services/remoteStatusService");

test("normalizes remote server inputs", () => {
  assert.deepEqual(
    normalizeServers([
      { url: "http://127.0.0.1:8270", alias: "api" },
      { url: "http://127.0.0.1:8271", name: "ui" },
      null
    ]),
    [
      { url: "http://127.0.0.1:8270", alias: "api", timeout: undefined },
      { url: "http://127.0.0.1:8271", alias: "ui", timeout: undefined }
    ]
  );
});

test("parses XML-RPC keyword name arrays", () => {
  const xml = `<?xml version="1.0"?>
  <methodResponse><params><param><value><array><data>
    <value><string>HTTP请求</string></value>
    <value><string>打印</string></value>
  </data></array></value></param></params></methodResponse>`;

  assert.deepEqual(parseKeywordNames(xml), ["HTTP请求", "打印"]);
});

test("checks XML-RPC remote keyword server status", async (t) => {
  const server = http.createServer((request, response) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      body += chunk;
    });
    request.on("end", () => {
      assert.match(body, /get_keyword_names/);
      response.writeHead(200, { "Content-Type": "text/xml" });
      response.end(`<?xml version="1.0"?>
        <methodResponse><params><param><value><array><data>
          <value><string>HTTP请求</string></value>
          <value><string>断言</string></value>
          <value><string>打印</string></value>
        </data></array></value></param></params></methodResponse>`);
    });
  });

  try {
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });
  } catch (error) {
    if (error && error.code === "EPERM") {
      t.skip("sandbox does not allow opening a local test server");
      return;
    }
    throw error;
  }
  const address = server.address();

  try {
    const result = await checkRemoteServers([
      { alias: "api_server", url: `http://127.0.0.1:${address.port}/` },
      { alias: "missing_url" }
    ]);

    assert.equal(result.counts.online, 1);
    assert.equal(result.counts.unchecked, 1);
    assert.equal(result.servers[0].status, "online");
    assert.equal(result.servers[0].keywords, 3);
    assert.equal(result.servers[1].status, "unchecked");
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});
