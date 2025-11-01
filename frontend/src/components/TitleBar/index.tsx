import React, { useEffect } from 'react'
import { Minus, Square, X } from 'lucide-react'

export const TitleBar: React.FC = () => {
  useEffect(() => {
    console.log('TitleBar mounted')
    console.log('window.electronAPI:', window.electronAPI)
  }, [])

  const handleMinimize = () => {
    console.log('Minimize button clicked')
    console.log('electronAPI available:', !!window.electronAPI)
    if (window.electronAPI?.windowMinimize) {
      window.electronAPI.windowMinimize()
      console.log('windowMinimize called')
    } else {
      console.error('electronAPI.windowMinimize not available')
    }
  }

  const handleMaximize = () => {
    console.log('Maximize button clicked')
    if (window.electronAPI?.windowMaximize) {
      window.electronAPI.windowMaximize()
      console.log('windowMaximize called')
    } else {
      console.error('electronAPI.windowMaximize not available')
    }
  }

  const handleClose = () => {
    console.log('Close button clicked')
    if (window.electronAPI?.windowClose) {
      window.electronAPI.windowClose()
      console.log('windowClose called')
    } else {
      console.error('electronAPI.windowClose not available')
    }
  }

  return (
    <div
      className="h-8 bg-light-navbar dark:bg-dark-navbar border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-3 select-none"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex items-center">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">七海 AI 助手</span>
      </div>

      <div
        className="flex items-center gap-1"
        style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
      >
        <button
          onClick={handleMinimize}
          className="w-8 h-6 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
          title="最小化"
        >
          <Minus size={14} />
        </button>
        <button
          onClick={handleMaximize}
          className="w-8 h-6 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
          title="最大化"
        >
          <Square size={12} />
        </button>
        <button
          onClick={handleClose}
          className="w-8 h-6 flex items-center justify-center hover:bg-red-500 hover:text-white rounded transition-colors"
          title="关闭"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  )
}
