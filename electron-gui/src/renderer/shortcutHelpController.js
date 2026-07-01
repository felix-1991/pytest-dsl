export function createShortcutHelpController({ el }) {
  let lastFocus = null;

  function openShortcutHelp() {
    if (!el.shortcutHelpDialog) {
      return;
    }
    lastFocus = document.activeElement;
    el.shortcutHelpDialog.hidden = false;
    if (el.shortcutHelpBtn) {
      el.shortcutHelpBtn.setAttribute("aria-expanded", "true");
    }
    const target = el.shortcutHelpCloseBtn || el.shortcutHelpDialog;
    if (target && typeof target.focus === "function") {
      target.focus();
    }
  }

  function closeShortcutHelp(options = {}) {
    if (!el.shortcutHelpDialog || el.shortcutHelpDialog.hidden) {
      return;
    }
    el.shortcutHelpDialog.hidden = true;
    if (el.shortcutHelpBtn) {
      el.shortcutHelpBtn.setAttribute("aria-expanded", "false");
    }
    if (
      options.restoreFocus !== false &&
      lastFocus &&
      typeof lastFocus.focus === "function"
    ) {
      lastFocus.focus();
    }
    lastFocus = null;
  }

  function handleShortcutHelpBackdropClick(event) {
    if (event.target === el.shortcutHelpDialog) {
      closeShortcutHelp();
    }
  }

  function handleShortcutHelpKeydown(event) {
    if (event.key !== "Escape") {
      return;
    }
    event.preventDefault();
    closeShortcutHelp();
  }

  return {
    closeShortcutHelp,
    handleShortcutHelpBackdropClick,
    handleShortcutHelpKeydown,
    openShortcutHelp,
  };
}
