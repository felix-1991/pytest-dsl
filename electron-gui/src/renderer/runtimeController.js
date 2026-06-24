export function createRuntimeController({
  state,
  el,
  api,
  appendLog,
  errorMessage,
  renderMetadata,
  showActionFeedback,
  onRuntimeStatusChange = () => {},
}) {
  function renderRuntimeStatus(status) {
    if (!status) return;
    state.runtimeStatus = {
      projectRoot: status.projectRoot || null,
      config: status.config || { pythonExecutable: null, allureExecutable: null },
      python: status.python || null,
      allure: status.allure || null,
    };
    renderRuntimeRow(
      "python",
      status.python,
      "Python 未配置",
    );
    renderRuntimeRow(
      "allure",
      status.allure,
      "Allure 未配置",
    );
    if (state.snapshot) {
      state.snapshot.metadata = {
        ...state.snapshot.metadata,
        runtime: status.config,
      };
    }
    onRuntimeStatusChange(state.runtimeStatus);
  }

  function renderRuntimeRow(kind, info, fallbackLabel) {
    const statusEl = kind === "python" ? el.runtimePythonStatus : el.runtimeAllureStatus;
    const pathEl = kind === "python" ? el.runtimePythonPath : el.runtimeAllurePath;
    if (!statusEl || !pathEl) return;
    statusEl.classList.remove("online", "warning", "offline", "unchecked");
    if (!info) {
      statusEl.classList.add("unchecked");
      pathEl.textContent = fallbackLabel;
      pathEl.title = fallbackLabel;
      return;
    }
    if (info.available) {
      statusEl.classList.add("online");
      const display = runtimeAvailableText(info);
      pathEl.textContent = display;
      pathEl.title = runtimeFullText(info, display);
      return;
    }
    const isConfigured = info.source === "project-config";
    const isAllure = kind === "allure";
    if (isAllure && !isConfigured && info.reason === "allure-not-found") {
      statusEl.classList.add("warning");
      const display = runtimeUnavailableText(kind, info, "Allure 未找到 (可选)");
      pathEl.textContent = display;
      pathEl.title = runtimeFullText(info, display);
      return;
    }
    statusEl.classList.add("offline");
    const display = runtimeUnavailableText(kind, info, `${kind} 不可用`);
    pathEl.textContent = display;
    pathEl.title = runtimeFullText(info, display);
  }

  function runtimeAvailableText(info) {
    const command = runtimeCommandText(info);
    const version = info.version ? ` (v${info.version})` : "";
    if (info.source === "project-config") {
      return `${command}${version}`;
    }
    return [
      `${command}${version}`,
      `来源: ${runtimeSourceLabel(info.source)}`,
    ].filter(Boolean).join("\n");
  }

  function runtimeUnavailableText(kind, info, fallback) {
    const lines = [info.message || fallback];
    if (info.command) {
      lines.push(`命令: ${runtimeCommandText(info)}`);
    }
    if (info.source) {
      lines.push(`来源: ${runtimeSourceLabel(info.source)}`);
    }
    if (info.action) {
      lines.push(`处理: ${info.action}`);
    }
    if (lines.length === 1 && kind === "allure" && info.reason === "allure-not-found") {
      lines.push("处理: 执行 npm install -g allure 安装 Allure 3，或点击“选择”指定 allure 可执行文件。");
    }
    return lines.filter(Boolean).join("\n");
  }

  function runtimeFullText(info, display) {
    const lines = [display];
    if (info.detail && !display.includes(info.detail)) {
      lines.push(info.detail);
    }
    if (Array.isArray(info.checked) && info.checked.length > 0) {
      lines.push("Checked candidates:");
      info.checked.forEach((candidate) => {
        lines.push(`- ${runtimeCommandText(candidate)} [${runtimeSourceLabel(candidate.source)}]: ${runtimeCandidateStatusText(candidate)}`);
      });
    }
    return lines.filter(Boolean).join("\n");
  }

  function runtimeCandidateStatusText(candidate) {
    if (!candidate.available) {
      return "不可执行";
    }
    if (candidate.probeStatus === "ok") {
      return "探针通过";
    }
    if (candidate.probeStatus === "missing") {
      return ["缺少依赖", compactRuntimeText(candidate.probeDetail)].filter(Boolean).join(": ");
    }
    if (candidate.probeStatus === "version-unsupported") {
      return ["版本不支持", compactRuntimeText(candidate.probeDetail)].filter(Boolean).join(": ");
    }
    if (candidate.probeStatus === "error") {
      return [
        "探针失败",
        candidate.probeSignal ? `信号 ${candidate.probeSignal}` : "",
        candidate.probeCode !== null && candidate.probeCode !== undefined ? `退出码 ${candidate.probeCode}` : "",
        compactRuntimeText(candidate.probeDetail),
      ].filter(Boolean).join(", ");
    }
    return "已发现";
  }

  function runtimeCommandText(info) {
    return [info.command, ...(info.args || [])].filter(Boolean).join(" ");
  }

  function compactRuntimeText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function runtimeSourceLabel(source) {
    const labels = {
      "project-config": "项目配置",
      "project-venv": "项目虚拟环境",
      "project-node-modules": "项目 node_modules",
      "studio-node-modules": "Studio 内置 node_modules",
      environment: "环境变量",
      path: "PATH",
    };
    return labels[source] || source || "未知";
  }

  async function changeRuntime(kind, reset = false, selectionMode = null) {
    if (!state.snapshot) return;
    const projectRoot = state.snapshot.project.rootPath;
    const method = reset ? api.resetRuntimeExecutable : api.selectRuntimeExecutable;
    if (typeof method !== "function") return;
    try {
      const result = await method({ projectRoot, kind, selectionMode });
      if (!result || result.canceled) return;
      renderRuntimeStatus(result);
      showActionFeedback(
        runtimeChangeFeedback(kind, reset, result),
        runtimeChangeFeedbackLevel(kind, reset, result),
      );
      if (state.snapshot) {
        state.snapshot.metadata = {
          ...state.snapshot.metadata,
          runtime: result.config,
        };
        renderMetadata(state.snapshot.metadata);
      }
    } catch (error) {
      appendLog("error", `Failed to update runtime: ${error.message}`);
      showActionFeedback(`运行环境更新失败: ${error.message}`, "error");
      showRuntimeRequirementDialog(error);
    }
  }

  function runtimeChangeFeedback(kind, reset, result) {
    const label = kind === "python" ? "Python" : "Allure";
    if (reset) {
      return `${label} 已恢复自动选择`;
    }
    const info = result && result[kind];
    if (!info) {
      return `${label} 已更新`;
    }
    if (info.available) {
      return `${label} 已选择: ${runtimeCommandText(info)}`;
    }
    return `${label} 已选择但不可用: ${info.message || runtimeCommandText(info) || "请查看详情"}`;
  }

  function runtimeChangeFeedbackLevel(kind, reset, result) {
    if (reset) {
      return "info";
    }
    const info = result && result[kind];
    return info && info.available ? "pass" : "warn";
  }

  function showRuntimeRequirementDialog(error) {
    const message = errorMessage(error);
    const body = runtimeRequirementDialogText(message);
    if (!body) {
      return false;
    }
    if (typeof window !== "undefined" && typeof window.alert === "function") {
      window.alert(body);
    }
    return true;
  }

  function runtimeRequirementDialogText(message) {
    if (isPythonRuntimeRequirementMessage(message)) {
      return [
        "Python 运行环境不可用",
        "",
        "需要 Python 3.9 及以上，并在当前解释器中安装 pytest-dsl。",
        "",
        "安装命令:",
        "pip install pytest-dsl",
        "",
        "也可以在运行环境里选择项目目录、.venv/venv 目录，或虚拟环境中的 Python 解释器路径。",
        "",
        "当前错误:",
        message,
      ].join("\n");
    }
    if (isAllureRuntimeRequirementMessage(message)) {
      return [
        "Allure 3 运行环境不可用",
        "",
        "构建报告需要 Allure 3。",
        "",
        "安装命令:",
        "npm install -g allure",
        "",
        "当前错误:",
        message,
      ].join("\n");
    }
    return "";
  }

  function isPythonRuntimeRequirementMessage(message) {
    return /PYTHON_RUNTIME_UNAVAILABLE|Python 运行环境不可用|Python 3\.9|pytest-dsl|pytest_dsl|Selected Python directory/i.test(message);
  }

  function isAllureRuntimeRequirementMessage(message) {
    return /ALLURE_RUNTIME_UNAVAILABLE|Allure 3 运行环境不可用|requires Allure 3|Allure 3 was not found|构建报告需要 Allure 3/i.test(message);
  }

  return {
    changeRuntime,
    renderRuntimeStatus,
    showRuntimeRequirementDialog,
  };
}
