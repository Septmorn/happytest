import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // AI 调用可能较慢，设 2 分钟超时
})

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

/**
 * 启动闭环管道
 */
export function runPipeline(params) {
  return api.post('/pipeline/run', params)
}

/**
 * 查询管道状态
 */
export function getPipelineStatus(taskId) {
  return api.get(`/pipeline/status/${taskId}`)
}

/**
 * 健康检查
 */
export function healthCheck() {
  return api.get('/health')
}

export default api