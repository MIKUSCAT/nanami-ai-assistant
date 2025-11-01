import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

process.env.DIST = path.join(__dirname, '../dist')
process.env.VITE_PUBLIC = app.isPackaged
  ? process.env.DIST
  : path.join(process.env.DIST, '../public')

let win: BrowserWindow | null = null
const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL']

function createWindow() {
  if (win !== null) {
    return
  }

  win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    backgroundColor: '#1F2428',
    titleBarStyle: 'hidden',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: true,
      devTools: !app.isPackaged,
      disableBlinkFeatures: 'Auxclick',
      enableWebSQL: false,
      v8CacheOptions: 'none'
    },
    icon: path.join(process.env.VITE_PUBLIC, 'icon.png')
  })

  // 禁用错误提示对话框
  win.webContents.on('did-fail-load', () => {
    console.error('Page failed to load')
  })

  win.webContents.on('crashed', () => {
    console.error('Renderer process crashed')
  })

  // 加载应用
  // 开发模式下 vite-plugin-electron 会设置 VITE_DEV_SERVER_URL
  if (VITE_DEV_SERVER_URL) {
    console.log('Loading dev server:', VITE_DEV_SERVER_URL)
    win.loadURL(VITE_DEV_SERVER_URL)
  } else {
    // 生产模式
    win.loadFile(path.join(process.env.DIST, 'index.html'))
  }

  // 键盘快捷键
  win.webContents.on('before-input-event', (event, input) => {
    // F12 或 Ctrl+Shift+I 打开DevTools
    if (input.key === 'F12' || (input.control && input.shift && input.key === 'I')) {
      win?.webContents.toggleDevTools()
      event.preventDefault()
    }
  })

  // 窗口关闭事件
  win.on('closed', () => {
    win = null
  })
}

const gotTheLock = app.requestSingleInstanceLock()

if (!gotTheLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (win) {
      if (win.isMinimized()) win.restore()
      win.focus()
    }
  })

  app.whenReady().then(() => {
    app.commandLine.appendSwitch('disable-gpu-shader-disk-cache')
    app.commandLine.appendSwitch('disable-gpu-sandbox')
    app.commandLine.appendSwitch('disable-software-rasterizer')
    createWindow()
  })
}

// 所有窗口关闭时退出(macOS除外)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// macOS重新激活时创建窗口
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

// IPC通信处理
ipcMain.handle('get-app-version', () => {
  console.log('IPC: get-app-version called')
  return app.getVersion()
})

// 窗口控制
ipcMain.handle('window-minimize', () => {
  console.log('IPC: window-minimize called')
  win?.minimize()
})

ipcMain.handle('window-maximize', () => {
  console.log('IPC: window-maximize called')
  if (win?.isMaximized()) {
    win.unmaximize()
  } else {
    win?.maximize()
  }
})

ipcMain.handle('window-close', () => {
  console.log('IPC: window-close called')
  win?.close()
})

// 禁用所有错误对话框
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error)
  // 不显示对话框,只记录日志
})

app.on('render-process-gone', (event, webContents, details) => {
  console.error('Render process gone:', details)
  // 静默处理,不显示错误
})
