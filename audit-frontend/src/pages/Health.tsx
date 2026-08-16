import { useQuery } from '@tanstack/react-query'
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
  const health = useQuery({
    queryKey: ['admin', 'health-page'],
    queryFn: async () => {
      const [h, o, l] = await Promise.all([
        auditApi.get<ApiResult<Health>>('/admin/health'),
        auditApi.get<ApiResult<{ items: { id: string; topic: string; status: string }[] }>>(
          '/admin/health/orphans',
        ),
        auditApi.get<ApiResult<{ pid: number; cpu_count: number }>>('/admin/health/load'),
      ])
      return {
        data: h.data.data,
        orphans: o.data.data?.items || [],
        loadInfo: l.data.data,
      }
    },
  })

  const data = health.data?.data
  const orphans = health.data?.orphans || []
  const loadInfo = health.data?.loadInfo

  return (
    <div className="page wide">
      <div className="row">
        <h1>系统健康</h1>
        <button type="button" disabled={health.isFetching} onClick={() => health.refetch()}>
          {health.isFetching ? '检查中…' : '刷新'}
        </button>
      </div>
      {data?.app && <p className="muted">{data.app}</p>}
      {health.isError && <p className="error">健康检查失败</p>}
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
