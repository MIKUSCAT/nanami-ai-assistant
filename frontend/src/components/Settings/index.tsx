import React, { useState, useEffect } from 'react'
import { X, Save, RefreshCw, Trash2, Eye, EyeOff, Search, ChevronDown, ChevronRight } from 'lucide-react'
import { config } from '../../config'

interface SettingsProps {
  onClose: () => void
}

interface EnvConfig {
  MAIN_PROVIDER: string
  MAIN_MODEL: string
  MAIN_API_KEY: string
  MAIN_BASE_URL: string
  MAIN_CONTEXT_LENGTH: string
  COMPACT_PROVIDER: string
  COMPACT_MODEL: string
  COMPACT_API_KEY: string
  COMPACT_BASE_URL: string
  COMPACT_CONTEXT_LENGTH: string
  QUICK_PROVIDER: string
  QUICK_MODEL: string
  QUICK_API_KEY: string
  QUICK_BASE_URL: string
  QUICK_CONTEXT_LENGTH: string
  SEARCH_AGENT_PROVIDER: string
  SEARCH_AGENT_MODEL: string
  SEARCH_AGENT_API_KEY: string
  SEARCH_AGENT_BASE_URL: string
  SEARCH_AGENT_CONTEXT_LENGTH: string
  BROWSER_AGENT_PROVIDER: string
  BROWSER_AGENT_MODEL: string
  BROWSER_AGENT_API_KEY: string
  BROWSER_AGENT_BASE_URL: string
  BROWSER_AGENT_CONTEXT_LENGTH: string
  WINDOWS_AGENT_PROVIDER: string
  WINDOWS_AGENT_MODEL: string
  WINDOWS_AGENT_API_KEY: string
  WINDOWS_AGENT_BASE_URL: string
  WINDOWS_AGENT_CONTEXT_LENGTH: string
  TAVILY_API_KEY: string
  WORKSPACE_ROOT: string
  PORT: string
  AUTO_COMPACT_RATIO: string
  LTM_MD_PATH: string
}

interface ModelDetectorProps {
  onModelSelect: (model: string) => void
  currentModel: string
}

const ModelDetector: React.FC<ModelDetectorProps> = ({ onModelSelect, currentModel }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [models, setModels] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchModels = async () => {
    setLoading(true)
    setError(null)

    try {
      const { fetchModels } = await import('../../services/api')
      const data = await fetchModels()
      const modelList = data?.map((m: any) => m.id || m).filter(Boolean) || []
      setModels(modelList)

      if (modelList.length > 0) {
        setIsOpen(true)
      } else {
        setError('未找到可用的模型')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取模型列表失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-2">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={fetchModels}
          disabled={loading}
          className="px-3 py-1.5 text-xs bg-primary-500 hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-1"
        >
          <Search size={14} />
          {loading ? '检测中...' : '检测模型'}
        </button>
        {currentModel && (
          <span className="px-3 py-1.5 text-xs bg-green-500/10 text-green-600 dark:text-green-400 rounded-lg">
            当前: {currentModel}
          </span>
        )}
      </div>

      {error && (
        <div className="mt-2 p-2 text-xs text-red-600 dark:text-red-400 bg-red-500/10 rounded">
          {error}
        </div>
      )}

      {isOpen && models.length > 0 && (
        <div className="mt-2 p-3 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 max-h-48 overflow-y-auto">
          <div className="text-xs font-medium mb-2 text-gray-600 dark:text-gray-400">可用模型 (点击选择):</div>
          <div className="space-y-1">
            {models.map((model) => (
              <button
                key={model}
                type="button"
                onClick={() => {
                  onModelSelect(model)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-2 py-1.5 text-sm rounded hover:bg-light-bg-soft dark:hover:bg-dark-bg-soft transition-colors ${
                  model === currentModel ? 'bg-primary-500/20 text-primary-600 dark:text-primary-400' : ''
                }`}
              >
                {model}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const PasswordInput: React.FC<{
  value: string
  onChange: (value: string) => void
  placeholder?: string
}> = ({ value, onChange, placeholder }) => {
  const [show, setShow] = useState(false)

  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2 pr-10 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
        placeholder={placeholder}
      />
      <button
        type="button"
        onClick={() => setShow(!show)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
      >
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  )
}

const ModelInput: React.FC<{
  label: string
  value: string
  onChange: (value: string) => void
}> = ({ label, value, onChange }) => {
  return (
    <div>
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium mb-2">{label}</label>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
        placeholder="例如: gpt-4, claude-3-sonnet"
      />
      <ModelDetector
        currentModel={value}
        onModelSelect={onChange}
      />
    </div>
  )
}

export const Settings: React.FC<SettingsProps> = ({ onClose }) => {
  const [settings, setSettings] = useState<EnvConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [clearSuccess, setClearSuccess] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`${config.apiBaseUrl}/api/settings`)
      if (!response.ok) {
        throw new Error('获取设置失败')
      }
      const data = await response.json()
      setSettings(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载设置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!settings) return

    try {
      setSaving(true)
      setError(null)
      const response = await fetch(`${config.apiBaseUrl}/api/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      })

      if (!response.ok) {
        throw new Error('保存设置失败')
      }

      setSuccess(true)
      setTimeout(() => setSuccess(false), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存设置失败')
    } finally {
      setSaving(false)
    }
  }

  const handleChange = (key: keyof EnvConfig, value: string) => {
    if (!settings) return
    setSettings({ ...settings, [key]: value })
  }

  const handleClearCache = async () => {
    if (!confirm('⚠️ 确定要清除所有缓存吗？\n\n这将删除：\n- 所有对话记录\n- TODO列表\n- 缓存的截图和文件\n\n此操作不可恢复！')) {
      return
    }

    try {
      setClearing(true)
      setError(null)
      const response = await fetch(`${config.apiBaseUrl}/api/clear_all_cache`, {
        method: 'POST',
      })

      const result = await response.json()

      if (result.success) {
        setClearSuccess(true)
        setTimeout(() => {
          setClearSuccess(false)
          window.location.reload()
        }, 2000)
      } else {
        setError(result.message || '清除缓存失败')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '清除缓存失败')
    } finally {
      setClearing(false)
    }
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-dark-bg-soft rounded-lg p-6">
          <div className="flex items-center gap-3">
            <RefreshCw className="animate-spin" size={20} />
            <span>加载设置中...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-bg-soft rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold">系统设置</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {success && (
            <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-600 dark:text-green-400">
              ✅ 设置保存成功！部分设置需要重启后端服务生效
            </div>
          )}

          {clearSuccess && (
            <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-600 dark:text-green-400">
              ✅ 缓存清除成功！页面即将刷新...
            </div>
          )}

          {settings && (
            <>
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-primary-600 dark:text-primary-400">
                  主模型配置（用于主要对话）
                </h3>
                <div>
                  <label className="block text-sm font-medium mb-2">提供商</label>
                  <input
                    type="text"
                    value={settings.MAIN_PROVIDER}
                    onChange={(e) => handleChange('MAIN_PROVIDER', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <ModelInput
                  label="模型"
                  value={settings.MAIN_MODEL}
                  onChange={(value) => handleChange('MAIN_MODEL', value)}
                />
                <div>
                  <label className="block text-sm font-medium mb-2">API Key</label>
                  <PasswordInput
                    value={settings.MAIN_API_KEY}
                    onChange={(value) => handleChange('MAIN_API_KEY', value)}
                    placeholder="留空则不使用认证"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Base URL</label>
                  <input
                    type="text"
                    value={settings.MAIN_BASE_URL}
                    onChange={(e) => handleChange('MAIN_BASE_URL', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                    placeholder="例如: https://api.openai.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">上下文长度</label>
                  <input
                    type="number"
                    value={settings.MAIN_CONTEXT_LENGTH}
                    onChange={(e) => handleChange('MAIN_CONTEXT_LENGTH', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-primary-600 dark:text-primary-400">
                  压缩模型配置（用于上下文压缩，节省成本）
                </h3>
                <div className="text-sm text-gray-600 dark:text-gray-400 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  💡 压缩模型用于对话历史摘要和上下文压缩，推荐使用成本较低的模型
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">提供商</label>
                  <input
                    type="text"
                    value={settings.COMPACT_PROVIDER}
                    onChange={(e) => handleChange('COMPACT_PROVIDER', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <ModelInput
                  label="模型"
                  value={settings.COMPACT_MODEL}
                  onChange={(value) => handleChange('COMPACT_MODEL', value)}
                />
                <div>
                  <label className="block text-sm font-medium mb-2">API Key</label>
                  <PasswordInput
                    value={settings.COMPACT_API_KEY}
                    onChange={(value) => handleChange('COMPACT_API_KEY', value)}
                    placeholder="留空则不使用认证"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Base URL</label>
                  <input
                    type="text"
                    value={settings.COMPACT_BASE_URL}
                    onChange={(e) => handleChange('COMPACT_BASE_URL', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">上下文长度</label>
                  <input
                    type="number"
                    value={settings.COMPACT_CONTEXT_LENGTH}
                    onChange={(e) => handleChange('COMPACT_CONTEXT_LENGTH', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-primary-600 dark:text-primary-400">
                  快速模型配置（用于简单任务）
                </h3>
                <div className="text-sm text-gray-600 dark:text-gray-400 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  💡 快速模型用于简单任务和快速响应，推荐使用成本较低的模型
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">提供商</label>
                  <input
                    type="text"
                    value={settings.QUICK_PROVIDER}
                    onChange={(e) => handleChange('QUICK_PROVIDER', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <ModelInput
                  label="模型"
                  value={settings.QUICK_MODEL}
                  onChange={(value) => handleChange('QUICK_MODEL', value)}
                />
                <div>
                  <label className="block text-sm font-medium mb-2">API Key</label>
                  <PasswordInput
                    value={settings.QUICK_API_KEY}
                    onChange={(value) => handleChange('QUICK_API_KEY', value)}
                    placeholder="留空则不使用认证"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Base URL</label>
                  <input
                    type="text"
                    value={settings.QUICK_BASE_URL}
                    onChange={(e) => handleChange('QUICK_BASE_URL', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">上下文长度</label>
                  <input
                    type="number"
                    value={settings.QUICK_CONTEXT_LENGTH}
                    onChange={(e) => handleChange('QUICK_CONTEXT_LENGTH', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-primary-600 dark:text-primary-400">
                  深度搜索SubAgent模型配置
                </h3>
                <div className="text-sm text-gray-600 dark:text-gray-400 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  💡 深度搜索SubAgent用于学术论文检索、技术文档收集等任务
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">提供商</label>
                  <input
                    type="text"
                    value={settings.SEARCH_AGENT_PROVIDER}
                    onChange={(e) => handleChange('SEARCH_AGENT_PROVIDER', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <ModelInput
                  label="模型"
                  value={settings.SEARCH_AGENT_MODEL}
                  onChange={(value) => handleChange('SEARCH_AGENT_MODEL', value)}
                />
                <div>
                  <label className="block text-sm font-medium mb-2">API Key</label>
                  <PasswordInput
                    value={settings.SEARCH_AGENT_API_KEY}
                    onChange={(value) => handleChange('SEARCH_AGENT_API_KEY', value)}
                    placeholder="留空则不使用认证"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Base URL</label>
                  <input
                    type="text"
                    value={settings.SEARCH_AGENT_BASE_URL}
                    onChange={(e) => handleChange('SEARCH_AGENT_BASE_URL', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">上下文长度</label>
                  <input
                    type="number"
                    value={settings.SEARCH_AGENT_CONTEXT_LENGTH}
                    onChange={(e) => handleChange('SEARCH_AGENT_CONTEXT_LENGTH', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-primary-600 dark:text-primary-400">
                  浏览器SubAgent模型配置
                </h3>
                <div className="text-sm text-gray-600 dark:text-gray-400 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  💡 浏览器SubAgent用于B站视频分析等需要网页交互的任务
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">提供商</label>
                  <input
                    type="text"
                    value={settings.BROWSER_AGENT_PROVIDER}
                    onChange={(e) => handleChange('BROWSER_AGENT_PROVIDER', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <ModelInput
                  label="模型"
                  value={settings.BROWSER_AGENT_MODEL}
                  onChange={(value) => handleChange('BROWSER_AGENT_MODEL', value)}
                />
                <div>
                  <label className="block text-sm font-medium mb-2">API Key</label>
                  <PasswordInput
                    value={settings.BROWSER_AGENT_API_KEY}
                    onChange={(value) => handleChange('BROWSER_AGENT_API_KEY', value)}
                    placeholder="留空则不使用认证"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Base URL</label>
                  <input
                    type="text"
                    value={settings.BROWSER_AGENT_BASE_URL}
                    onChange={(e) => handleChange('BROWSER_AGENT_BASE_URL', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">上下文长度</label>
                  <input
                    type="number"
                    value={settings.BROWSER_AGENT_CONTEXT_LENGTH}
                    onChange={(e) => handleChange('BROWSER_AGENT_CONTEXT_LENGTH', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-primary-600 dark:text-primary-400">
                  Windows SubAgent模型配置
                </h3>
                <div className="text-sm text-gray-600 dark:text-gray-400 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  💡 Windows SubAgent用于Windows应用自动化操作任务
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">提供商</label>
                  <input
                    type="text"
                    value={settings.WINDOWS_AGENT_PROVIDER}
                    onChange={(e) => handleChange('WINDOWS_AGENT_PROVIDER', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <ModelInput
                  label="模型"
                  value={settings.WINDOWS_AGENT_MODEL}
                  onChange={(value) => handleChange('WINDOWS_AGENT_MODEL', value)}
                />
                <div>
                  <label className="block text-sm font-medium mb-2">API Key</label>
                  <PasswordInput
                    value={settings.WINDOWS_AGENT_API_KEY}
                    onChange={(value) => handleChange('WINDOWS_AGENT_API_KEY', value)}
                    placeholder="留空则不使用认证"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Base URL</label>
                  <input
                    type="text"
                    value={settings.WINDOWS_AGENT_BASE_URL}
                    onChange={(e) => handleChange('WINDOWS_AGENT_BASE_URL', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">上下文长度</label>
                  <input
                    type="number"
                    value={settings.WINDOWS_AGENT_CONTEXT_LENGTH}
                    onChange={(e) => handleChange('WINDOWS_AGENT_CONTEXT_LENGTH', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-primary-600 dark:text-primary-400">
                  其他设置
                </h3>
                <div>
                  <label className="block text-sm font-medium mb-2">Tavily API Key（搜索功能）</label>
                  <PasswordInput
                    value={settings.TAVILY_API_KEY}
                    onChange={(value) => handleChange('TAVILY_API_KEY', value)}
                    placeholder="留空则禁用搜索功能"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">工作空间根目录</label>
                  <input
                    type="text"
                    value={settings.WORKSPACE_ROOT}
                    onChange={(e) => handleChange('WORKSPACE_ROOT', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">服务器端口</label>
                  <input
                    type="number"
                    value={settings.PORT}
                    onChange={(e) => handleChange('PORT', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">自动压缩比例（0.92 = 92%）</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.5"
                    max="0.99"
                    value={settings.AUTO_COMPACT_RATIO}
                    onChange={(e) => handleChange('AUTO_COMPACT_RATIO', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">长期记忆路径</label>
                  <input
                    type="text"
                    value={settings.LTM_MD_PATH}
                    onChange={(e) => handleChange('LTM_MD_PATH', e.target.value)}
                    className="w-full px-4 py-2 bg-light-bg-mute dark:bg-dark-bg-mute rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                </div>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex gap-3">
            <button
              onClick={loadSettings}
              disabled={loading}
              className="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              重新加载
            </button>
            <button
              onClick={handleClearCache}
              disabled={clearing}
              className="px-4 py-2 text-sm bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-400 border border-red-500/30 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
              title="清除所有对话记录、TODO和缓存文件"
            >
              <Trash2 size={16} className={clearing ? 'animate-spin' : ''} />
              {clearing ? '清除中...' : '清除所有缓存'}
            </button>
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 text-sm bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <Save size={16} />
              {saving ? '保存中...' : '保存设置'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
