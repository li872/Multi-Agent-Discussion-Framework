import axios from 'axios'

// 审计前端只用 audit_token，绝不用主系统 localStorage.token
export const auditApi = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

auditApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('audit_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

auditApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('audit_token')
      localStorage.removeItem('audit_admin')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

export type ApiResult<T> = {
  code: number
  message: string
  data: T
}
