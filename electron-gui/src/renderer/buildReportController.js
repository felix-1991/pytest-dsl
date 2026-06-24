import {
  BUILD_STATUS_LABELS,
  allureRuntimeUnavailableMessage,
  isAllureRuntimeAvailable,
  isPythonRuntimeAvailable,
  pythonRuntimeUnavailableMessage,
} from "./state.js";
import { escapeAttr, escapeHtml, errorMessage } from "./utils.js";

export function createBuildReportController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  currentSelectedSuiteIds,
  suiteBuildScopeLabel,
  buildCommandLabel,
  buildResultsDirForBuild,
  buildPytestArgsLabel,
  activeBuildCommandId,
  selectedConfigSources,
}) {
  function updateBuildActionState() {
    const hasProject = Boolean(state.snapshot);
    const hasSuites = currentSelectedSuiteIds("build").length > 0;
    const isBuildRunning = state.currentTaskId && state.currentTaskMode === "build";
    const isAnyTaskRunning = Boolean(state.currentTaskId);
    const hasCompletedBuild = Boolean(state.snapshot && state.currentBuildId && state.currentBuildStatus && state.currentBuildStatus !== "running");
    const pythonReady = isPythonRuntimeAvailable(state);
    el.buildRunBtn.disabled = !hasProject || !hasSuites || isAnyTaskRunning || !pythonReady;
    el.buildRunBtn.title = !pythonReady && hasProject
      ? pythonRuntimeUnavailableMessage(state)
      : "运行 pytest 构建";
    el.buildStopBtn.hidden = !isBuildRunning;
    el.buildStopBtn.disabled = !isBuildRunning;
    el.buildOpenReportBtn.disabled = !hasCompletedBuild && !state.currentBuildReportUrl;
    el.buildDownloadReportBtn.disabled = !hasCompletedBuild || isAnyTaskRunning || !state.currentBuildResultsDir;
    el.buildDownloadLogsBtn.disabled = !hasCompletedBuild || isAnyTaskRunning;
  }

  function updateBuildSummary(options = {}) {
    if (!el.buildScope) {
      return;
    }
    const selectedSuiteIds = currentSelectedSuiteIds("build");
    const yamlVars = selectedConfigSources().map((source) => source.relativePath);
    const scopeLabel = state.snapshot
      ? selectedSuiteIds.length > 0
        ? suiteBuildScopeLabel(selectedSuiteIds)
        : "未选择构建案例"
      : "未打开项目";
    const command = options.command || buildCommandLabel(activeBuildCommandId());
    const resultsDir = options.resultsDir || state.currentBuildResultsDir || (
      state.currentBuildId
        ? buildResultsDirForBuild(state.currentBuildId)
        : "运行后生成"
    );
    const reportText = options.reportText ||
      state.currentBuildReportUrl ||
      state.currentBuildReportText ||
      defaultBuildReportText();
    const pytestArgs = buildPytestArgsLabel(yamlVars, activeBuildCommandId());
    const configText = yamlVars.length > 0 ? yamlVars.join(", ") : "未选择 YAML 配置";

    el.buildScope.textContent = yamlVars.length > 0
      ? `${scopeLabel} · ${yamlVars.length} config`
      : scopeLabel;
    el.buildScope.title = el.buildScope.textContent;
    el.buildConfigSummary.textContent = configText;
    el.buildConfigSummary.title = configText;
    el.buildPytestArgs.textContent = pytestArgs;
    el.buildPytestArgs.title = pytestArgs;
    el.buildAllureStatus.textContent = reportText;
    el.buildAllureStatus.title = reportText;
    el.buildCommand.textContent = command;
    el.buildCommand.title = command;
    el.buildResultsDir.textContent = resultsDir;
    el.buildResultsDir.title = resultsDir;
    el.buildReportUrl.textContent = reportText;
    el.buildReportUrl.title = reportText;
    if (options.status) {
      el.buildStatus.textContent = options.status;
    } else if (!state.snapshot) {
      el.buildStatus.textContent = "打开项目后选择构建案例";
    } else if (selectedSuiteIds.length === 0) {
      el.buildStatus.textContent = "请在左侧选择要构建的案例";
    } else if (!isPythonRuntimeAvailable(state)) {
      el.buildStatus.textContent = "Python 运行环境不可用，无法调试或构建";
    } else if (state.currentTaskMode === "build") {
      el.buildStatus.textContent = "构建运行中";
    } else if (!isAllureRuntimeAvailable(state)) {
      el.buildStatus.textContent = "可运行 pytest；未检测到 Allure 3，报告不可用";
    } else {
      el.buildStatus.textContent = "准备运行 pytest 并生成 Allure 报告";
    }
    updateBuildActionState();
  }

  function resetBuildReport() {
    clearBuildReportReloadTimer();
    cancelBuildReportFrameReveal();
    state.currentBuildReportUrl = "";
    state.currentBuildReportText = "";
    state.buildReportReloadSeq = 0;
    el.buildReportFrame.src = "about:blank";
    el.buildReportFrame.hidden = true;
    el.buildReportEmpty.hidden = false;
    el.buildReportEmpty.textContent = defaultBuildReportText();
    el.buildReportUrl.textContent = defaultBuildReportText();
    el.buildAllureStatus.textContent = defaultBuildReportText();
    el.buildOpenReportBtn.disabled = true;
  }

  function setBuildReportUrl(url) {
    state.currentBuildReportUrl = normalizeAllureReportUrl(url);
    if (!state.currentBuildReportUrl) {
      resetBuildReport();
      return;
    }
    state.currentBuildReportText = "";
    el.buildReportFrame.src = buildReportFrameUrl(state.currentBuildReportUrl);
    syncBuildReportFrameVisibility({ defer: state.activeView === "build" });
    el.buildReportUrl.textContent = state.currentBuildReportUrl;
    el.buildReportUrl.title = state.currentBuildReportUrl;
    el.buildOpenReportBtn.disabled = false;
    scheduleBuildReportFrameReload();
  }

  function syncBuildReportFrameVisibility(options = {}) {
    cancelBuildReportFrameReveal();
    if (!state.currentBuildReportUrl) {
      el.buildReportFrame.hidden = true;
      el.buildReportEmpty.hidden = false;
      el.buildReportEmpty.textContent = defaultBuildReportText();
      return;
    }

    if (state.activeView !== "build") {
      el.buildReportFrame.hidden = true;
      el.buildReportEmpty.hidden = false;
      el.buildReportEmpty.textContent = "Allure 报告已生成，切到构建页后显示";
      return;
    }

    if (options.defer) {
      el.buildReportFrame.hidden = true;
      el.buildReportEmpty.hidden = false;
      el.buildReportEmpty.textContent = "Allure 报告准备就绪，正在加载视图";
      deferBuildReportFrameReveal();
      return;
    }

    revealBuildReportFrame();
  }

  function deferBuildReportFrameReveal() {
    const reveal = () => {
      state.buildReportRevealRaf = null;
      state.buildReportRevealTimer = window.setTimeout(() => {
        state.buildReportRevealTimer = null;
        revealBuildReportFrame();
      }, 0);
    };

    if (typeof window.requestAnimationFrame === "function") {
      state.buildReportRevealRaf = window.requestAnimationFrame(reveal);
    } else {
      state.buildReportRevealTimer = window.setTimeout(revealBuildReportFrame, 0);
    }
  }

  function revealBuildReportFrame() {
    if (!state.currentBuildReportUrl || state.activeView !== "build") {
      return;
    }
    el.buildReportFrame.hidden = false;
    el.buildReportEmpty.hidden = true;
  }

  function cancelBuildReportFrameReveal() {
    if (state.buildReportRevealRaf !== null && typeof window.cancelAnimationFrame === "function") {
      window.cancelAnimationFrame(state.buildReportRevealRaf);
    }
    state.buildReportRevealRaf = null;
    if (state.buildReportRevealTimer) {
      window.clearTimeout(state.buildReportRevealTimer);
      state.buildReportRevealTimer = null;
    }
  }

  function buildReportFrameUrl(url) {
    const value = String(url || "").trim();
    if (!value) {
      return "";
    }
    const reloadSeq = Number(arguments[1] || 0);
    const token = encodeURIComponent(state.currentBuildId || String(Date.now()));
    const hashIndex = value.indexOf("#");
    const base = hashIndex >= 0 ? value.slice(0, hashIndex) : value;
    const hash = hashIndex >= 0 ? value.slice(hashIndex) : "";
    const separator = base.includes("?") ? "&" : "?";
    const reloadToken = reloadSeq > 0 ? `-${encodeURIComponent(String(reloadSeq))}` : "";
    return `${base}${separator}pytestDslBuild=${token}${reloadToken}${hash}`;
  }

  function scheduleBuildReportFrameReload() {
    clearBuildReportReloadTimer();
    scheduleBuildReportReloadAttempt(1);
  }

  function scheduleBuildReportReloadAttempt(attempt) {
    if (!state.currentBuildReportUrl || attempt > 2) {
      return;
    }
    const buildId = state.currentBuildId;
    const reportUrl = state.currentBuildReportUrl;
    const delayMs = attempt === 1 ? 500 : 1500;
    state.buildReportReloadTimer = window.setTimeout(() => {
      if (state.currentBuildId !== buildId || state.currentBuildReportUrl !== reportUrl) {
        return;
      }
      state.buildReportReloadSeq += 1;
      el.buildReportFrame.src = buildReportFrameUrl(state.currentBuildReportUrl, state.buildReportReloadSeq);
      scheduleBuildReportReloadAttempt(attempt + 1);
    }, delayMs);
  }

  function clearBuildReportReloadTimer() {
    if (state.buildReportReloadTimer) {
      window.clearTimeout(state.buildReportReloadTimer);
      state.buildReportReloadTimer = null;
    }
  }

  function normalizeAllureReportUrl(url) {
    const value = String(url || "").trim();
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
      return parsed.toString();
    } catch (_error) {
      return value;
    }
  }

  function openCurrentBuildReport() {
    if (!state.currentBuildReportUrl) {
      const message = isAllureRuntimeAvailable(state)
        ? "未生成 Allure 报告，请先完成一次带报告的构建"
        : "未生成 Allure 报告：未检测到 Allure 3，请安装后重新构建";
      appendLog("warn", message, { scope: "build" });
      showActionFeedback(message, "warn");
      return;
    }
    window.open(state.currentBuildReportUrl, "_blank", "noopener");
  }

  function currentBuildDownloadOptions() {
    if (!state.snapshot || !state.currentBuildId) {
      return null;
    }
    return {
      projectRoot: state.snapshot.project.rootPath,
      buildId: state.currentBuildId,
    };
  }

  async function downloadCurrentBuildReport() {
    const options = currentBuildDownloadOptions();
    if (!options || !state.currentBuildStatus || state.currentBuildStatus === "running") {
      appendLog("warn", "当前没有已完成的构建报告可下载", { scope: "build" });
      return;
    }
    if (!state.currentBuildResultsDir) {
      appendLog("warn", "当前构建没有 Allure results 目录", { scope: "build" });
      return;
    }
    if (!isAllureRuntimeAvailable(state)) {
      const message = "未检测到 Allure 3，请安装 Allure 3 后再下载报告";
      appendLog("warn", message, { scope: "build" });
      showActionFeedback("安装 Allure 3 后再下载报告", "warn");
      return;
    }
    if (typeof api.downloadBuildReport !== "function") {
      appendLog("warn", "当前环境不支持保存 Allure 报告", { scope: "build" });
      return;
    }

    el.buildDownloadReportBtn.disabled = true;
    appendLog("info", "正在生成并保存 Allure 报告", { scope: "build" });
    try {
      const result = await api.downloadBuildReport(options);
      if (result && result.canceled) {
        appendLog("info", "已取消保存 Allure 报告", { scope: "build" });
        return;
      }
      appendLog("pass", `Allure 报告已保存: ${result.path}`, { scope: "build" });
      showActionFeedback("Allure 报告已保存", "pass");
    } catch (error) {
      appendLog("error", `保存 Allure 报告失败: ${errorMessage(error)}`, { scope: "build" });
      showActionFeedback("保存 Allure 报告失败", "error");
    } finally {
      updateBuildActionState();
    }
  }

  async function downloadCurrentBuildLogs() {
    const options = currentBuildDownloadOptions();
    if (!options || !state.currentBuildStatus || state.currentBuildStatus === "running") {
      appendLog("warn", "当前没有已完成的构建日志可下载", { scope: "build" });
      return;
    }
    if (typeof api.downloadBuildLogs !== "function") {
      appendLog("warn", "当前环境不支持保存构建日志", { scope: "build" });
      return;
    }

    el.buildDownloadLogsBtn.disabled = true;
    appendLog("info", "正在保存构建日志", { scope: "build" });
    try {
      const result = await api.downloadBuildLogs(options);
      if (result && result.canceled) {
        appendLog("info", "已取消保存构建日志", { scope: "build" });
        return;
      }
      appendLog("pass", `构建日志已保存: ${result.path}`, { scope: "build" });
      showActionFeedback("构建日志已保存", "pass");
    } catch (error) {
      appendLog("error", `保存构建日志失败: ${errorMessage(error)}`, { scope: "build" });
      showActionFeedback("保存构建日志失败", "error");
    } finally {
      updateBuildActionState();
    }
  }

  function buildStatusLabel(status) {
    return BUILD_STATUS_LABELS[status] || `构建 ${status || "完成"}`;
  }

  function defaultBuildReportText() {
    if (state.snapshot && !isAllureRuntimeAvailable(state)) {
      return allureRuntimeUnavailableMessage(state);
    }
    return "等待 Allure 报告";
  }

  function recordBuildHistory(event) {
    const entry = {
      buildId: event.buildId,
      status: event.status,
      durationMs: event.durationMs,
      exitCode: event.exitCode,
      resultsDir: event.allureResultsDir || "",
      reportUrl: event.reportUrl || state.currentBuildReportUrl || "",
      command: buildCommandLabel(event.buildId),
      completedAt: new Date().toLocaleTimeString(),
    };
    state.buildHistory = [entry, ...state.buildHistory]
      .filter((item, index, list) =>
        index === list.findIndex((candidate) => candidate.buildId === item.buildId),
      )
      .slice(0, 8);
    renderBuildHistory();
  }

  function renderBuildHistory() {
    if (!el.buildHistoryList) {
      return;
    }
    if (!state.buildHistory.length) {
      el.buildHistoryList.innerHTML = `<p class="empty">还没有构建记录</p>`;
      return;
    }
    el.buildHistoryList.innerHTML = state.buildHistory
      .map((entry) => `
      <article class="build-history-item">
        <div class="build-history-line">
          <strong>${escapeHtml(buildStatusLabel(entry.status))}</strong>
          <span>${escapeHtml(entry.completedAt)}</span>
        </div>
        <code title="${escapeAttr(entry.command)}">${escapeHtml(entry.command)}</code>
        <dl>
          <div>
            <dt>耗时</dt>
            <dd>${Number(entry.durationMs || 0)}ms</dd>
          </div>
          <div>
            <dt>退出码</dt>
            <dd>${entry.exitCode === null || entry.exitCode === undefined ? "-" : escapeHtml(String(entry.exitCode))}</dd>
          </div>
        </dl>
        <p title="${escapeAttr(entry.resultsDir)}">${escapeHtml(entry.resultsDir || "无结果目录")}</p>
        ${entry.reportUrl ? `<a href="${escapeAttr(entry.reportUrl)}" target="_blank" rel="noreferrer">打开报告</a>` : ""}
      </article>
    `)
      .join("");
  }

  return {
    updateBuildActionState,
    updateBuildSummary,
    resetBuildReport,
    setBuildReportUrl,
    syncBuildReportFrameVisibility,
    deferBuildReportFrameReveal,
    revealBuildReportFrame,
    cancelBuildReportFrameReveal,
    buildReportFrameUrl,
    scheduleBuildReportFrameReload,
    scheduleBuildReportReloadAttempt,
    clearBuildReportReloadTimer,
    normalizeAllureReportUrl,
    openCurrentBuildReport,
    currentBuildDownloadOptions,
    downloadCurrentBuildReport,
    downloadCurrentBuildLogs,
    buildStatusLabel,
    recordBuildHistory,
    renderBuildHistory,
  };
}
