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
  createEntry: (projectRoot, options) => ipcRenderer.invoke("file:create", projectRoot, options),
  renameEntry: (projectRoot, options) => ipcRenderer.invoke("file:rename", projectRoot, options),
  moveEntry: (projectRoot, options) => ipcRenderer.invoke("file:move", projectRoot, options),
  deleteEntry: (projectRoot, options) => ipcRenderer.invoke("file:delete", projectRoot, options),
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
  },
  startBuild: (options) => ipcRenderer.invoke("build:start", options),
  stopBuild: (buildId) => ipcRenderer.invoke("build:stop", buildId),
  downloadBuildReport: (options) => ipcRenderer.invoke("build:download-report", options),
  downloadBuildLogs: (options) => ipcRenderer.invoke("build:download-logs", options),
  onBuildEvent: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("build:event", listener);
    return () => ipcRenderer.removeListener("build:event", listener);
  }
});
