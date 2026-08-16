import { useEffect, useState } from 'react'
import { auditApi } from '../api/client'
import type { ApiResult } from '../api/client'

export default function Settings() {
  const [days, setDays] = useState(90)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    auditApi
      .get<ApiResult<{ retention_days: number }>>('/audit/settings')
      .then((res) => setDays(res.data.data?.retention_days || 90))
      .catch(() => setError('加载设置失败'))
  }, [])

  async function save() {
    try {
      const res = await auditApi.put<ApiResult<{ retention_days: number }>>(
        '/audit/settings/retention',
        { days },
      )
      setDays(res.data.data.retention_days)
      setMessage('保留策略已保存')
    } catch {
      setError('保存失败')
    }
  }

  async function restart() {
    try {
      const res = await auditApi.post<ApiResult<{ message: string }>>('/audit/settings/restart')
      setMessage(res.data.data?.message || '已记录重启请求')
    } catch {
      setError('重启请求失败')
    }
  }

  return (
    <div className="page wide">
      <h1>设置</h1>
      {error && <p className="error">{error}</p>}
      {message && <p className="muted">{message}</p>}
      <div className="card">
        <label>
          审计事件保留天数
          <input
            type="number"
            min={1}
            max={3650}
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          />
        </label>
        <button type="button" onClick={save}>
          保存保留策略
        </button>
        <button type="button" onClick={restart}>
          请求重启服务
        </button>
      </div>
    </div>
  )
}
