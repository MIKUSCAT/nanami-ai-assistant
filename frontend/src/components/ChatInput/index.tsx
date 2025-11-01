import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, X, StopCircle } from 'lucide-react'

interface ChatInputProps {
  onSend: (text: string, files?: File[]) => void
  onAbort?: () => void
  disabled?: boolean
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, onAbort, disabled }) => {
  const [input, setInput] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (input.trim() || files.length > 0) {
      onSend(input.trim(), files)
      setInput('')
      setFiles([])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    setFiles((prev) => [...prev, ...selectedFiles])
  }

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  // 处理粘贴事件
  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return

    const pastedFiles: File[] = []

    // 遍历剪贴板项目
    for (let i = 0; i < items.length; i++) {
      const item = items[i]

      // 处理文件类型（图片等）
      if (item.kind === 'file') {
        const file = item.getAsFile()
        if (file) {
          pastedFiles.push(file)
        }
      }
    }

    // 如果有粘贴的文件，添加到文件列表
    if (pastedFiles.length > 0) {
      e.preventDefault() // 阻止默认粘贴行为
      setFiles((prev) => [...prev, ...pastedFiles])
    }
  }

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-light-bg-soft dark:bg-dark-bg-soft p-4">
      {/* 已选择的文件 */}
      {files.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {files.map((file, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-3 py-1.5 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg text-sm"
            >
              <Paperclip size={14} />
              <span>{file.name}</span>
              <button
                onClick={() => removeFile(index)}
                className="hover:text-red-500"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 输入框 */}
      <div className="flex items-end gap-2">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          multiple
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="p-2.5 rounded-lg hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute transition-colors disabled:opacity-50"
          title="上传文件"
        >
          <Paperclip size={20} />
        </button>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder="输入消息... (Shift+Enter换行, Ctrl+V粘贴图片)"
          disabled={disabled}
          rows={1}
          className="flex-1 px-4 py-2.5 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-400 dark:text-white disabled:opacity-50"
          style={{ maxHeight: '120px' }}
        />
        {disabled ? (
          <button
            onClick={onAbort}
            className="p-2.5 rounded-lg bg-red-500 hover:bg-red-600 text-white transition-colors"
            title="中断"
          >
            <StopCircle size={20} />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim() && files.length === 0}
            className="p-2.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="发送"
          >
            <Send size={20} />
          </button>
        )}
      </div>
    </div>
  )
}
