(function () {
  "use strict";

  const api = window.pytestDslDefinition;

  let _readonlyEditorKey = null;

  async function loadDefinition(data) {
    const { projectRoot, path, line, name } = data || {};
    if (!projectRoot || !path) {
      document.getElementById("defMeta").textContent = "无效的定义数据";
      return;
    }

    try {
      const result = await api.readSourceFile({ projectRoot, path });
      document.getElementById("defPath").textContent = result.path;
      document.getElementById("defMeta").textContent =
        `${name || "未知"} : 第 ${line || 1} 行 · ${result.language || "python"}`;

      const container = document.getElementById("defEditor");
      if (!container) return;

      const key = "def-main";
      CM6.create(key, container, {});
      _readonlyEditorKey = key;
      CM6.show(key);
      CM6.setContent(result.content);
      CM6.setLanguage(result.language || "python");
      CM6.setEnabled(false);

      if (line && line > 0) {
        // Wait a tick for layout, then scroll
        setTimeout(() => {
          try { CM6.scrollToLine(line); } catch (_) { /* ignore */ }
        }, 80);
      }
    } catch (error) {
      document.getElementById("defMeta").textContent = `Error: ${error.message}`;
    }
  }

  function init() {
    document.getElementById("defCloseBtn").addEventListener("click", () => {
      api.close();
    });

    // Keep listening so a reused definition window can jump to another symbol
    // in the same source file.
    api.onData(loadDefinition);

    // Fallback: if data was sent before we were ready, check after a short delay
    setTimeout(() => {
      if (!_readonlyEditorKey) {
        document.getElementById("defMeta").textContent = "等待定义数据...";
      }
    }, 1500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
