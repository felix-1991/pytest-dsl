const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("pytestDslGui", {
  openProject: () => ipcRenderer.invoke("project:open"),
  getDefaultProject: () => ipcRenderer.invoke("project:default"),
  scanProject: (projectRoot) => ipcRenderer.invoke("project:scan", projectRoot),
  scanProjectConfig: (projectRoot) => ipcRenderer.invoke("project:config", projectRoot),
  readFile: (projectRoot, relativePath) => ipcRenderer.invoke("file:read", projectRoot, relativePath),
  saveFile: (projectRoot, relativePath, content) => (
    ipcRenderer.invoke("file:save", projectRoot, relativePath, content)
  ),
  checkRemoteServers: (servers) => ipcRenderer.invoke("remote:check", servers),
  listKeywords: (options) => ipcRenderer.invoke("keyword:list", options),
  findKeywordDefinitions: (options) => ipcRenderer.invoke("keyword:definition", options),
  readSourceFile: (options) => ipcRenderer.invoke("source:read", options),
  copyText: (text) => ipcRenderer.invoke("clipboard:write", text),
  startExecution: (options) => ipcRenderer.invoke("execution:start", options),
  sendExecutionCommand: (taskId, command) => (
    ipcRenderer.invoke("execution:command", taskId, command)
  ),
  stopExecution: (taskId) => ipcRenderer.invoke("execution:stop", taskId),
  onExecutionEvent: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("execution:event", listener);
    return () => ipcRenderer.removeListener("execution:event", listener);
  }
});
