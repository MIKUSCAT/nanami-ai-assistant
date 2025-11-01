import React, { useState } from 'react'
import { Todo } from '../../types'
import { CheckCircle2, Circle, Loader2, ChevronDown, ChevronRight } from 'lucide-react'

interface TodoListProps {
  todos: Todo[]
  onToggle?: (todo: Todo) => void
}

export const TodoList: React.FC<TodoListProps> = ({ todos, onToggle }) => {
  const [collapsed, setCollapsed] = useState(false)

  if (todos.length === 0) return null

  const getStatusIcon = (status: Todo['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 size={16} className="text-green-500 animate-[checkmark_0.4s_ease-in-out]" />
      case 'in_progress':
        return <Loader2 size={16} className="text-blue-500 animate-spin" />
      default:
        return <Circle size={16} className="text-gray-400" />
    }
  }

  const getStatusText = (status: Todo['status']) => {
    switch (status) {
      case 'completed':
        return '已完成'
      case 'in_progress':
        return '进行中'
      default:
        return '待处理'
    }
  }

  const getStatusColor = (status: Todo['status']) => {
    switch (status) {
      case 'completed':
        return 'text-green-500'
      case 'in_progress':
        return 'text-blue-500'
      default:
        return 'text-gray-500'
    }
  }

  const completedCount = todos.filter((t) => t.status === 'completed').length
  const totalCount = todos.length
  const progress = (completedCount / totalCount) * 100

  return (
    <div className="mb-4 rounded-xl overflow-hidden bg-light-bg-soft dark:bg-dark-bg-soft border border-gray-200 dark:border-gray-700">
      {/* 头部 */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute transition-colors"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-3">
          <button className="p-1 hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute rounded transition-colors">
            {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
          </button>
          <div>
            <h3 className="text-sm font-semibold">任务列表</h3>
            <p className="text-xs opacity-60 mt-0.5">
              {completedCount} / {totalCount} 已完成
            </p>
          </div>
        </div>
        <div className="text-sm font-medium opacity-70">{Math.round(progress)}%</div>
      </div>

      {/* 进度条 */}
      <div className="h-1 bg-gray-200 dark:bg-gray-700">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* 任务列表 */}
      {!collapsed && (
        <div className="p-3 space-y-2 animate-[slideDown_0.3s_ease-out]">
          {todos
            .sort((a, b) => a.order - b.order)
            .map((todo, index) => (
              <div
                key={todo.id}
                className="flex items-start gap-3 p-3 rounded-lg hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute transition-all duration-200 group"
                style={{
                  animation: `todoFadeIn 0.4s ease-out ${index * 0.05}s both`,
                }}
              >
                <button
                  className="mt-0.5 cursor-pointer"
                  title={todo.status === 'completed' ? '标记为未完成' : '标记为完成'}
                  onClick={() => onToggle?.(todo)}
                >
                  {getStatusIcon(todo.status)}
                </button>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-sm transition-all duration-300 ${
                        todo.status === 'completed'
                          ? 'line-through opacity-60'
                          : 'opacity-100'
                      }`}
                    >
                      {todo.title}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(
                        todo.status
                      )} bg-current bg-opacity-10 transition-all duration-300`}
                    >
                      {getStatusText(todo.status)}
                    </span>
                  </div>
                  {todo.description && (
                    <p className="text-xs opacity-60 mt-1.5 leading-relaxed">
                      {todo.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}
