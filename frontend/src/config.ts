// 前端配置文件
export const config = {
  // 后端API地址
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:7878',

  // 长期记忆设置
  ltm: {
    enabled: true,
    autoSave: false, // 是否自动保存偏好
    minMessages: 4, // 最少消息数才能保存偏好
  },

  // 主题设置
  theme: {
    default: 'light' as 'light' | 'dark',
  },

  // 消息设置
  message: {
    maxLength: 10000, // 最大消息长度
    streamChunkSize: 1000, // 流式响应块大小
  },

  // 文件上传设置
  upload: {
    maxFileSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: [
      'text/plain',
      'text/markdown',
      'application/pdf',
      'image/png',
      'image/jpeg',
      'image/gif',
      'application/json',
    ],
  },

  // TODO设置
  todo: {
    showAnimations: true, // 显示动画
    autoCollapse: false, // 自动折叠已完成
  },
}

// 开发环境配置
if (import.meta.env.DEV) {
  console.log('✨ 七海配置已加载', config)
}
