const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("pytestDslDefinition", {
  readSourceFile: (options) => ipcRenderer.invoke("source:read", options),
  close: () => ipcRenderer.invoke("definition:close"),
  onData: (callback) => {
    const listener = (_event, data) => callback(data);
    ipcRenderer.on("definition:data", listener);
    return () => ipcRenderer.removeListener("definition:data", listener);
  },
});
