import { useEffect, useState } from 'react'
import { auditApi } from '../api/client'
import type { ApiResult } from '../api/client'

type Component = {
  status: string
  latency_ms?: number
  http_status?: number
  error?: string
}

type Health = {
  app?: string
  components: Record<string, Component>
}

export default function Health() {
  const [data, setData] = useState<Health | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const [orphans, setOrphans] = useState<{ id: string; topic: string; status: string }[]>([])
  const [loadInfo, setLoadInfo] = useState<{ pid?: number; cpu_count?: number } | null>(null)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [h, o, l] = await Promise.all([
        auditApi.get<ApiResult<Health>>('/admin/health'),
        auditApi.get<ApiResult<{ items: { id: string; topic: string; status: string }[] }>>(
          '/admin/health/orphans',
        ),
        auditApi.get<ApiResult<{ pid: number; cpu_count: number }>>('/admin/health/load'),
      ])
      setData(h.data.data)
      setOrphans(o.data.data?.items || [])
      setLoadInfo(l.data.data)
    } catch {
      setError('健康检查失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="page wide">
      <div className="row">
        <h1>系统健康</h1>
        <button type="button" disabled={loading} onClick={load}>
          {loading ? '检查中…' : '刷新'}
        </button>
      </div>
      {data?.app && <p className="muted">{data.app}</p>}
      {error && <p className="error">{error}</p>}
      <ul className="checklist">
        {data &&
          Object.entries(data.components || {}).map(([name, c]) => (
            <li key={name} className="card">
              <div className="row">
                <strong>{name}</strong>
                <span className={`status-pill ${c.status}`}>{c.status}</span>
              </div>
              {c.latency_ms != null && <p className="muted">延迟 {c.latency_ms} ms</p>}
              {c.http_status != null && <p className="muted">HTTP {c.http_status}</p>}
              {c.error && <p className="error">{c.error}</p>}
            </li>
          ))}
      </ul>
      {loadInfo && (
        <p className="muted">
          负载 pid={loadInfo.pid} cpu={loadInfo.cpu_count}
        </p>
      )}
      <h2>孤儿讨论</h2>
      <ul className="checklist">
        {orphans.map((d) => (
          <li key={d.id}>
            <strong>{d.topic}</strong>
            <span className={`status-pill ${d.status}`}>{d.status}</span>
          </li>
        ))}
      </ul>
      {orphans.length === 0 && <p className="muted">没有超时未结束的讨论</p>}
    </div>
  )
}
