import {
  COMMAND_CONTEXT_LABELS,
  createCommandBar,
} from "./state.js";

export function createCommandController({
  state,
  el,
  consoleScopeForMode,
  currentCommand,
  normalizeConsoleScope,
}) {
  function normalizeCommandText(command) {
    return String(command || "pytest-dsl").replace(/\s+/g, " ").trim() || "pytest-dsl";
  }

  function previewCommand(command = currentCommand(), options = {}) {
    const scope = normalizeConsoleScope(options.scope || state.console.activeScope);
    const preview = commandPreviewForScope(scope);
    if (preview.taskId) {
      return preview.command;
    }
    if (preview.persistent && !options.force) {
      return preview.command;
    }
    return updateCommandPreview(command, {
      context: "preview",
      persistent: false,
      taskId: null,
      scope,
    });
  }

  function setExecutionCommand(command, options = {}) {
    const scope = normalizeConsoleScope(options.scope || consoleScopeForMode(options.mode));
    const updated = updateCommandPreview(command, {
      context: commandContextForMode(options.mode),
      persistent: true,
      taskId: options.taskId || null,
      scope,
    });
    if (scope === "debug") {
      lockGeneratedCommand(updated, {
        context: commandContextForMode(options.mode),
        taskId: options.taskId || null,
      });
    }
    return updated;
  }

  function releaseExecutionCommand(taskId) {
    const preview = commandPreviewForTask(taskId) || currentCommandPreview();
    if (
      taskId &&
      preview.taskId &&
      preview.taskId !== taskId
    ) {
      return preview.command;
    }
    preview.taskId = null;
    preview.persistent = false;
    preview.context = "preview";
    releaseCommandBarTask(taskId);
    updateCommandPreview(currentCommand(), {
      context: "preview",
      persistent: false,
      taskId: null,
      scope: consoleScopeForMode(state.currentTaskMode),
    });
    return preview.command;
  }

  function resetCommandPreview(command = "pytest-dsl") {
    const preview = currentCommandPreview();
    preview.command = command;
    preview.context = "preview";
    preview.persistent = false;
    preview.taskId = null;
    resetCommandBar(command);
    renderCommandPreview();
    return command;
  }

  function updateCommandPreview(command, options = {}) {
    const scope = normalizeConsoleScope(options.scope || consoleScopeForMode(options.context));
    const preview = state.commandPreviews[scope];
    const normalized = normalizeCommandText(command);
    preview.command = normalized;
    preview.context = options.context || preview.context || "preview";
    preview.persistent = Boolean(options.persistent);
    preview.taskId = options.taskId || null;

    if (scope === state.console.activeScope) {
      renderCommandPreview();
    }
    if (scope === "debug") {
      syncCommandBarPreview(normalized, { context: preview.context });
    }
    return normalized;
  }

  function syncCommandBarPreview(command, options = {}) {
    if (state.commandBar.locked) {
      return state.commandBar.command;
    }
    state.commandBar.command = normalizeCommandText(command);
    state.commandBar.context = options.context || "preview";
    state.commandBar.taskId = null;
    renderCommandBar();
    return state.commandBar.command;
  }

  function lockGeneratedCommand(command, options = {}) {
    state.commandBar.command = normalizeCommandText(command);
    state.commandBar.context = options.context || "preview";
    state.commandBar.locked = true;
    state.commandBar.taskId = options.taskId || null;
    renderCommandBar();
    return state.commandBar.command;
  }

  function releaseCommandBarTask(taskId) {
    if (taskId && state.commandBar.taskId === taskId) {
      state.commandBar.taskId = null;
      renderCommandBar();
    }
  }

  function resetCommandBar(command = "pytest-dsl") {
    state.commandBar = createCommandBar(normalizeCommandText(command));
    renderCommandBar();
    return state.commandBar.command;
  }

  function currentCommandPreview() {
    return commandPreviewForScope(state.console.activeScope);
  }

  function commandPreviewForScope(scope) {
    return state.commandPreviews[normalizeConsoleScope(scope)];
  }

  function commandPreviewForTask(taskId) {
    if (!taskId) {
      return null;
    }
    return Object.values(state.commandPreviews)
      .find((preview) => preview.taskId === taskId) || null;
  }

  function renderCommandPreview() {
    const preview = currentCommandPreview();
    const label = commandContextLabel(preview.context);
    el.commandContext.textContent = label;
    el.commandContext.title = label;
    el.commandPreview.textContent = preview.command;
    el.commandPreview.title = preview.command;
  }

  function renderCommandBar() {
    if (!el.commandBar) {
      return;
    }
    const title = state.commandBar.locked
      ? `保持到下次生成或执行 · ${commandContextLabel(state.commandBar.context)}`
      : "随当前文件、选择和配置实时更新";
    el.commandBar.classList.toggle("is-locked", state.commandBar.locked);
    el.commandBar.classList.toggle("is-live", !state.commandBar.locked);
    el.generatedCommandStatus.textContent = state.commandBar.locked ? "已锁定" : "实时预览";
    el.generatedCommandStatus.title = title;
    el.generatedCommandText.textContent = state.commandBar.command;
    el.generatedCommandText.title = state.commandBar.command;
    el.copyCommandBtn.disabled = !state.commandBar.command || el.commandBar.hidden;
    el.regenerateCommandBtn.textContent = state.commandBar.locked ? "重新生成" : "生成并锁定";
    el.regenerateCommandBtn.title = state.commandBar.locked
      ? "用当前选择重新生成并替换锁定命令"
      : "生成并锁定当前命令";
  }

  function commandContextForMode(mode) {
    return COMMAND_CONTEXT_LABELS[mode] ? mode : "preview";
  }

  function commandContextLabel(context) {
    return COMMAND_CONTEXT_LABELS[context] || COMMAND_CONTEXT_LABELS.preview;
  }

  return {
    commandContextForMode,
    commandContextLabel,
    lockGeneratedCommand,
    normalizeCommandText,
    previewCommand,
    releaseExecutionCommand,
    renderCommandBar,
    renderCommandPreview,
    resetCommandPreview,
    setExecutionCommand,
    updateCommandPreview,
  };
}
