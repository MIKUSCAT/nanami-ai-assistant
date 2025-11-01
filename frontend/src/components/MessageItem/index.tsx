import React, { useEffect, useRef, useState } from 'react'
import { Message } from '../../types'
import { useChatStore } from '../../store/chat'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import { Copy, Edit2, RotateCcw, Trash2, Check } from 'lucide-react'

interface MessageItemProps {
  message: Message
  onRegenerate?: (message: Message) => void
}

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch {}
    }
    return ''
  },
})

export const MessageItem: React.FC<MessageItemProps> = ({ message, onRegenerate }) => {
  const isUser = message.role === 'user'
  const contentRef = useRef<HTMLDivElement>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState(message.content)
  const [copied, setCopied] = useState(false)
  const { updateMessage, deleteMessage } = useChatStore()

  let renderedContent = md.render(message.content)

  renderedContent = renderedContent.replace(
    /\$\$(.*?)\$\$/gs,
    '<span class="latex-block">$$$$1$$</span>'
  )
  renderedContent = renderedContent.replace(
    /\$(.*?)\$/g,
    '<span class="latex-inline">$$$1$</span>'
  )

  useEffect(() => {
    if (contentRef.current && typeof window !== 'undefined' && (window as any).renderMathInElement) {
      try {
        (window as any).renderMathInElement(contentRef.current, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false },
          ],
          throwOnError: false,
        })
      } catch (err) {
        console.error('KaTeX rendering error:', err)
      }
    }
  }, [message.content])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('复制失败:', err)
    }
  }

  const handleEdit = () => {
    setIsEditing(true)
    setEditContent(message.content)
  }

  const handleSaveEdit = () => {
    if (editContent.trim()) {
      updateMessage(message.id, editContent.trim())
      setIsEditing(false)
    }
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
    setEditContent(message.content)
  }

  const handleDelete = () => {
    if (confirm('确定删除这条消息吗？')) {
      deleteMessage(message.id)
    }
  }

  const handleRegenerate = () => {
    if (onRegenerate) {
      onRegenerate(message)
    }
  }

  return (
    <div
      className={`message-item mb-4 flex group ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-primary-50 dark:bg-dark-chat-user shadow-sm'
            : 'bg-light-chat-assistant dark:bg-dark-chat-assistant'
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium opacity-70">
            {isUser ? '你' : '七海'}
          </span>
          <span className="text-xs opacity-50">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>

        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full px-3 py-2 bg-white dark:bg-dark-bg-mute rounded-lg border border-primary-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400 text-sm"
              rows={4}
            />
            <div className="flex gap-2">
              <button
                onClick={handleSaveEdit}
                className="px-3 py-1 text-xs bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
              >
                保存
              </button>
              <button
                onClick={handleCancelEdit}
                className="px-3 py-1 text-xs bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-white rounded-lg transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        ) : (
          <>
            <div
              ref={contentRef}
              className={`markdown-content text-sm prose prose-sm max-w-none ${
                isUser
                  ? 'text-gray-800 dark:text-dark-text-user prose-invert'
                  : 'text-gray-800 dark:text-gray-200 prose-invert'
              }`}
              dangerouslySetInnerHTML={{ __html: renderedContent }}
            />
            {message.isStreaming && (
              <span className="inline-block w-1 h-4 ml-1 bg-current animate-pulse" />
            )}
          </>
        )}

        {!isEditing && !message.isStreaming && (
          <div className="mt-2 pt-2 border-t border-gray-200/50 dark:border-gray-600/30 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded hover:bg-primary-100 dark:hover:bg-gray-700 transition-colors"
              title="复制"
            >
              {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
            </button>

            <button
              onClick={handleEdit}
              className="p-1.5 rounded hover:bg-primary-100 dark:hover:bg-gray-700 transition-colors"
              title="编辑"
            >
              <Edit2 size={14} />
            </button>

            {isUser && (
              <button
                onClick={handleRegenerate}
                className="p-1.5 rounded hover:bg-primary-100 dark:hover:bg-gray-700 transition-colors"
                title="重新生成回复"
              >
                <RotateCcw size={14} />
              </button>
            )}

            <button
              onClick={handleDelete}
              className="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition-colors"
              title="删除"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
