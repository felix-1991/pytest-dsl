const http = require("node:http");
const https = require("node:https");

const DEFAULT_TIMEOUT_MS = 2000;
const MAX_TIMEOUT_MS = 3000;
const XMLRPC_GET_KEYWORDS = `<?xml version="1.0"?>
<methodCall>
  <methodName>get_keyword_names</methodName>
  <params></params>
</methodCall>`;

async function checkRemoteServers(servers, options = {}) {
  const normalized = normalizeServers(servers);
  const checkedAt = new Date().toISOString();
  const results = await Promise.all(
    normalized.map((server) => probeRemoteServer(server, options))
  );
  const counts = countStatuses(results);

  return {
    checkedAt,
    counts,
    servers: results
  };
}

async function probeRemoteServer(server, options = {}) {
  const timeoutMs = resolveTimeoutMs(server.timeout, options.timeoutMs);
  const base = {
    alias: server.alias,
    url: server.url,
    timeoutMs,
    status: "unchecked",
    keywords: 0,
    latencyMs: null,
    error: null
  };

  if (!server.url) {
    return { ...base, error: "missing url" };
  }

  const startedAt = Date.now();
  try {
    const response = await postXmlRpc(server.url, XMLRPC_GET_KEYWORDS, timeoutMs);
    const latencyMs = Date.now() - startedAt;
    const keywordNames = parseKeywordNames(response.body);

    return {
      ...base,
      status: "online",
      keywords: keywordNames.length,
      latencyMs
    };
  } catch (error) {
    return {
      ...base,
      status: "offline",
      latencyMs: Date.now() - startedAt,
      error: error && error.message ? error.message : String(error)
    };
  }
}

function normalizeServers(servers) {
  if (!Array.isArray(servers)) {
    return [];
  }

  return servers
    .filter((server) => server && typeof server === "object")
    .map((server, index) => ({
      alias: String(server.alias || server.name || `remote_${index + 1}`),
      url: server.url ? String(server.url) : "",
      timeout: server.timeout
    }));
}

function resolveTimeoutMs(serverTimeout, requestedTimeout) {
  const requested = Number(requestedTimeout);
  if (Number.isFinite(requested) && requested > 0) {
    return Math.min(requested, MAX_TIMEOUT_MS);
  }

  const configured = Number(serverTimeout);
  if (Number.isFinite(configured) && configured > 0) {
    return Math.min(configured * 1000, MAX_TIMEOUT_MS);
  }

  return DEFAULT_TIMEOUT_MS;
}

function postXmlRpc(urlValue, body, timeoutMs) {
  return new Promise((resolve, reject) => {
    let url;
    try {
      url = new URL(urlValue);
    } catch {
      reject(new Error("invalid url"));
      return;
    }

    const client = url.protocol === "https:" ? https : http;
    const request = client.request(
      {
        method: "POST",
        protocol: url.protocol,
        hostname: url.hostname,
        port: url.port,
        path: `${url.pathname || "/"}${url.search || ""}`,
        headers: {
          "Content-Type": "text/xml",
          "Content-Length": Buffer.byteLength(body)
        },
        timeout: timeoutMs
      },
      (response) => {
        let responseBody = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          responseBody += chunk;
        });
        response.on("end", () => {
          if (response.statusCode < 200 || response.statusCode >= 300) {
            reject(new Error(`http ${response.statusCode}`));
            return;
          }
          resolve({ statusCode: response.statusCode, body: responseBody });
        });
      }
    );

    request.on("timeout", () => {
      request.destroy(new Error("timeout"));
    });
    request.on("error", reject);
    request.write(body);
    request.end();
  });
}

function parseKeywordNames(xml) {
  const fault = xml.match(/<fault>[\s\S]*?<string>([\s\S]*?)<\/string>[\s\S]*?<\/fault>/i);
  if (fault) {
    throw new Error(unescapeXml(fault[1]));
  }

  const array = xml.match(/<array>\s*<data>([\s\S]*?)<\/data>\s*<\/array>/i);
  if (!array) {
    return [];
  }

  const names = [];
  const valuePattern = /<value>\s*(?:<string>)?([\s\S]*?)(?:<\/string>)?\s*<\/value>/gi;
  let match = valuePattern.exec(array[1]);
  while (match) {
    const value = unescapeXml(match[1].replace(/<[^>]+>/g, "").trim());
    if (value) {
      names.push(value);
    }
    match = valuePattern.exec(array[1]);
  }

  return names;
}

function unescapeXml(value) {
  return String(value)
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, "\"")
    .replace(/&apos;/g, "'")
    .replace(/&#039;/g, "'")
    .replace(/&amp;/g, "&");
}

function countStatuses(servers) {
  return servers.reduce(
    (counts, server) => {
      counts[server.status] = (counts[server.status] || 0) + 1;
      return counts;
    },
    { online: 0, offline: 0, unchecked: 0 }
  );
}

module.exports = {
  checkRemoteServers,
  countStatuses,
  normalizeServers,
  parseKeywordNames,
  probeRemoteServer
};
