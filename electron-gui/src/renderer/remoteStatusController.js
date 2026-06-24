import {
  REMOTE_MONITOR_INTERVAL_MS,
  REMOTE_STATUS_LABELS,
  emptyRemoteStatus,
} from "./state.js";
import {
  escapeAttr,
  escapeHtml,
  escapeRegExp,
  errorMessage,
  isPlainObject,
} from "./utils.js";

export function createRemoteStatusController({
  state,
  el,
  api,
  appendLog,
  currentCommand,
  previewCommand,
  selectedMergedConfig,
  initializeConfigSelection,
  renderConfig,
  renderActiveFile,
  renderProject,
  renderDeductions,
}) {
  function startDynamicRemoteMonitoring() {
    stopDynamicRemoteMonitoring();
    if (!state.snapshot) {
      return;
    }
    state.remoteMonitorTimer = setInterval(
      runDynamicRemoteMonitorTick,
      REMOTE_MONITOR_INTERVAL_MS
    );
  }

  function stopDynamicRemoteMonitoring() {
    if (state.remoteMonitorTimer) {
      clearInterval(state.remoteMonitorTimer);
      state.remoteMonitorTimer = null;
    }
    state.remoteMonitorRunning = false;
  }

  async function runDynamicRemoteMonitorTick() {
    if (!state.snapshot || state.remoteMonitorRunning || state.remoteStatus.loading) {
      return;
    }

    state.remoteMonitorRunning = true;
    try {
      await refreshProjectConfigIfChanged();
      if (state.snapshot) {
        await refreshRemoteStatuses();
      }
    } catch (error) {
      appendLog("error", `Dynamic remote monitor failed: ${errorMessage(error)}`);
    } finally {
      state.remoteMonitorRunning = false;
    }
  }

  async function refreshProjectConfigIfChanged() {
    if (!state.snapshot || typeof api.scanProjectConfig !== "function") {
      return false;
    }

    const result = await api.scanProjectConfig(state.snapshot.project.rootPath);
    const config = result && result.config ? result.config : null;
    if (!config || config.signature === state.configSignature) {
      return false;
    }

    const previousSelected = new Set(state.selectedConfigPaths);
    state.snapshot.config = config;
    state.configSignature = config.signature || null;
    initializeConfigSelection(state.snapshot, previousSelected);
    renderConfig();
    renderProject();
    renderDeductions();
    if (state.currentFile) {
      renderActiveFile();
    } else {
      previewCommand(currentCommand());
    }
    appendLog("info", "Config files changed; remote status will refresh");
    return true;
  }

  async function refreshRemoteStatuses() {
    if (!state.snapshot) {
      state.remoteStatus = emptyRemoteStatus();
      renderRemoteStatus();
      return;
    }

    const servers = extractRemoteServers(selectedMergedConfig());
    const probeSeq = state.remoteProbeSeq + 1;
    state.remoteProbeSeq = probeSeq;
    state.remoteStatus = {
      servers: servers.map((server) => ({
        ...server,
        status: "unchecked",
        keywords: 0,
        latencyMs: null,
        error: null,
      })),
      counts: countRemoteStatuses(servers),
      checkedAt: null,
      loading: servers.length > 0,
    };
    renderRemoteStatus();

    if (servers.length === 0) {
      return;
    }

    try {
      const result = await api.checkRemoteServers(servers);
      if (probeSeq !== state.remoteProbeSeq) {
        return;
      }
      state.remoteStatus = { ...result, loading: false };
      renderRemoteStatus();
    } catch (error) {
      if (probeSeq !== state.remoteProbeSeq) {
        return;
      }
      state.remoteStatus = {
        servers: servers.map((server) => ({
          ...server,
          status: "offline",
          keywords: 0,
          latencyMs: null,
          error: errorMessage(error),
        })),
        counts: { online: 0, offline: servers.length, unchecked: 0 },
        checkedAt: new Date().toISOString(),
        loading: false,
      };
      renderRemoteStatus();
      appendLog("error", `Remote status check failed: ${errorMessage(error)}`);
    }
  }

  function renderRemoteStatus() {
    if (!el.remoteStatusSummary || !el.remoteServiceRows || !el.remoteStatusBar) {
      return;
    }

    const remote = state.remoteStatus || emptyRemoteStatus();
    const servers = (remote.servers || []).map((server) => ({
      ...server,
      current: isRemoteServerCurrent(server),
    }));
    const counts = remote.counts || countRemoteStatuses(servers);
    const total = servers.length;
    const dot = remoteDotClass(counts, total, remote.loading);
    const className = `remote-summary ${remoteSummaryClass(counts, total, remote.loading)}`;
    const unchecked = counts.unchecked || 0;

    el.remoteStatusSummary.className = className;
    if (total === 0) {
      el.remoteStatusSummary.innerHTML =
        `<span class="status-dot unchecked"></span><span>无远程服务</span>`;
      el.remoteStatusBar.innerHTML =
        `<span class="status-dot unchecked"></span>远程: 无远程服务`;
    } else {
      const checkingText = remote.loading ? " · 探测中" : "";
      el.remoteStatusSummary.innerHTML =
        `<span class="status-dot ${dot}"></span><span>远程 ${counts.online}/${total} · ${counts.offline} 离线 · ${unchecked} 未探测${checkingText}</span>`;
      el.remoteStatusBar.innerHTML =
        `<span class="status-dot ${dot}"></span>远程: ${counts.online} 在线 · ${counts.offline} 离线 · ${unchecked} 未探测${formatCheckedAt(remote.checkedAt)}`;
    }

    if (total === 0) {
      el.remoteServiceRows.innerHTML = `<p class="empty">选中的配置中没有 remote_servers</p>`;
      return;
    }

    const sorted = [...servers].sort((left, right) => {
      const rank = { offline: 0, unchecked: 1, online: 2 };
      if (left.current !== right.current) return left.current ? -1 : 1;
      return rank[left.status] - rank[right.status];
    });

    el.remoteServiceRows.innerHTML = sorted
      .map((server) => `
      <div class="remote-service-row${server.current ? " is-current" : ""}">
        <span class="status-dot ${escapeAttr(server.status)}"></span>
        <span class="remote-service-name">
          <strong title="${escapeAttr(server.alias)}">${escapeHtml(server.alias)}</strong>
          <span title="${escapeAttr(server.url || "未配置 URL")}">${escapeHtml(server.url || "未配置 URL")}</span>
        </span>
        <span class="remote-service-meta">${escapeHtml(REMOTE_STATUS_LABELS[server.status] || "未知")} · ${escapeHtml(formatRemoteMeta(server, remote.loading))}</span>
      </div>
    `)
      .join("");
  }

  function extractRemoteServers(configData) {
    const remoteServers = configData && configData.remote_servers;
    if (!remoteServers) {
      return [];
    }

    const servers = [];
    if (Array.isArray(remoteServers)) {
      remoteServers.forEach((server, index) => {
        if (isPlainObject(server)) {
          servers.push(normalizeRemoteServer(server, `remote_${index + 1}`));
        }
      });
    } else if (isPlainObject(remoteServers)) {
      Object.entries(remoteServers).forEach(([name, server]) => {
        if (typeof server === "string") {
          servers.push(normalizeRemoteServer({ alias: name, url: server }, name));
          return;
        }
        if (isPlainObject(server)) {
          servers.push(normalizeRemoteServer({ alias: name, ...server }, name));
        }
      });
    }

    const seen = new Set();
    return servers.filter((server) => {
      const key = server.alias || server.url;
      if (!key || seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  function normalizeRemoteServer(server, fallbackAlias) {
    return {
      alias: String(server.alias || server.name || fallbackAlias),
      url: server.url ? String(server.url) : "",
      timeout: server.timeout,
    };
  }

  function countRemoteStatuses(servers) {
    return (servers || []).reduce(
      (counts, server) => {
        const status = server.status || "unchecked";
        counts[status] = (counts[status] || 0) + 1;
        return counts;
      },
      { online: 0, offline: 0, unchecked: 0 },
    );
  }

  function remoteSummaryClass(counts, total, loading) {
    if (total === 0) return "is-empty";
    if (loading) return "is-unchecked";
    if (counts.offline > 0 && counts.online === 0) return "is-offline";
    if (counts.offline > 0) return "is-warning";
    if (counts.unchecked > 0) return "is-unchecked";
    return "is-online";
  }

  function remoteDotClass(counts, total, loading) {
    if (total === 0 || loading) return "unchecked";
    if (counts.offline > 0) return "warning";
    if (counts.unchecked > 0) return "unchecked";
    return "online";
  }

  function formatRemoteMeta(server, loading) {
    if (loading && server.status === "unchecked") {
      return "探测中";
    }
    if (server.status === "online") {
      return `${server.keywords || 0} 关键字 · ${server.latencyMs || 0}ms`;
    }
    if (server.status === "offline") {
      return server.error || "连接失败";
    }
    return server.error || "未探测";
  }

  function formatCheckedAt(checkedAt) {
    if (!checkedAt) {
      return "";
    }
    const date = new Date(checkedAt);
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    return ` · 已检查 ${date.toTimeString().slice(0, 5)}`;
  }

  function isRemoteServerCurrent(server) {
    if (!server || !server.alias || !state.currentFile) {
      return false;
    }
    const content = CM6.getContent();
    const alias = escapeRegExp(server.alias);
    return new RegExp(`(^|\\s)${alias}\\|`).test(content) ||
      new RegExp(`\\bas\\s+${alias}\\b`).test(content);
  }

  return {
    startDynamicRemoteMonitoring,
    stopDynamicRemoteMonitoring,
    runDynamicRemoteMonitorTick,
    refreshProjectConfigIfChanged,
    refreshRemoteStatuses,
    renderRemoteStatus,
    extractRemoteServers,
    normalizeRemoteServer,
    countRemoteStatuses,
    remoteSummaryClass,
    remoteDotClass,
    formatRemoteMeta,
    formatCheckedAt,
    isRemoteServerCurrent,
  };
}
