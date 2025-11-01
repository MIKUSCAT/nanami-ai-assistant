// 注意: 预加载脚本在 Electron 中以 CommonJS 方式执行
// 使用 require 避免 ESModule 导致的 "Cannot use import statement outside a module" 问题
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { contextBridge, ipcRenderer } = require('electron')

// 暴露受保护的方法到渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  windowMinimize: () => ipcRenderer.invoke('window-minimize'),
  windowMaximize: () => ipcRenderer.invoke('window-maximize'),
  windowClose: () => ipcRenderer.invoke('window-close'),
})

console.log('Preload script loaded successfully')
console.log('electronAPI exposed to window')
