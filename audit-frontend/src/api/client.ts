import axios from 'axios'
import { auditApiBase, auditLoginPath } from './base'

export const auditApi = axios.create({
  baseURL: auditApiBase(),
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
        window.location.href = auditLoginPath()
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

export type PageData<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export function formatTs(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString()
}
