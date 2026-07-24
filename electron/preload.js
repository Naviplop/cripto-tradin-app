const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  selectLicenseFile: () => ipcRenderer.invoke('select-license-file'),
});
