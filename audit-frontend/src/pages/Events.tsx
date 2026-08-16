import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { auditApi, formatTs } from '../api/client'
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
  const [level, setLevel] = useState('')
  const list = useQuery({
    queryKey: ['audit', 'events', level],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '50', offset: '0' })
      if (level) params.set('level', level)
      const res = await auditApi.get<ApiResult<EventList>>(`/audit/events?${params}`)
      return res.data.data
    },
  })

  const items = list.data?.items || []
  const total = list.data?.total || 0

  return (
    <div className="page wide">
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
      {list.isError && <p className="error">加载审计事件失败（检查 ADMIN_JWT 与主后端）</p>}
      <ul className="checklist">
        {items.map((e) => (
          <li key={e.id}>
            <strong>{e.event_type}</strong>
            <span className={`status-pill ${e.level}`}>{e.level}</span>
            <span className="muted"> · {formatTs(e.created_at)}</span>
            {e.payload && Object.keys(e.payload).length > 0 && (
              <pre className="quote">{JSON.stringify(e.payload, null, 2)}</pre>
            )}
          </li>
        ))}
      </ul>
      {items.length === 0 && !list.isError && <p>暂无事件</p>}
    </div>
  )
}
