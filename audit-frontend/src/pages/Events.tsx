import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { auditApi } from '../api/client'
import type { ApiResult } from '../api/client'

type AuditEvent = {
  id: string
  user_id: string | null
  discussion_id: string | null
  event_type: string
  level: string
  payload: Record<string, unknown>
  created_at: string | null
}

type EventList = {
  items: AuditEvent[]
  total: number
}

export default function Events() {
  const navigate = useNavigate()
  const [items, setItems] = useState<AuditEvent[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')
  const [level, setLevel] = useState('')

  async function load() {
    const params = new URLSearchParams({ limit: '50', offset: '0' })
    if (level) params.set('level', level)
    const res = await auditApi.get<ApiResult<EventList>>(`/audit/events?${params}`)
    setItems(res.data.data?.items || [])
    setTotal(res.data.data?.total || 0)
  }

  useEffect(() => {
    load().catch(() => setError('加载审计事件失败（检查 ADMIN_TOKEN 与主后端）'))
  }, [level])

  function onLogout() {
    localStorage.removeItem('audit_token')
    localStorage.removeItem('audit_admin')
    navigate('/login')
  }

  return (
    <div className="page wide">
      <div className="row">
        <span>MADF 审计</span>
        <button type="button" onClick={onLogout}>
          退出
        </button>
      </div>
      <h1>审计事件</h1>
      <div className="row">
        <select value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">全部级别</option>
          <option value="P0">P0</option>
          <option value="P1">P1</option>
          <option value="P2">P2</option>
        </select>
        <span className="muted">共 {total} 条</span>
      </div>
      {error && <p className="error">{error}</p>}
      <ul className="checklist">
        {items.map((e) => (
          <li key={e.id}>
            <strong>{e.event_type}</strong>
            <span> · {e.level}</span>
            <span className="muted"> · {e.created_at || ''}</span>
            {e.payload && Object.keys(e.payload).length > 0 && (
              <pre className="quote">{JSON.stringify(e.payload, null, 2)}</pre>
            )}
          </li>
        ))}
      </ul>
      {items.length === 0 && !error && <p>暂无事件</p>}
    </div>
  )
}
