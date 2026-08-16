import { useQuery } from '@tanstack/react-query'
import { auditApi } from '../api/client'
import type { ApiResult } from '../api/client'

type Stats = { users: number; characters: number; discussions: number }
type Health = {
  components: Record<string, { status: string; latency_ms?: number; error?: string }>
}
type TokenStats = { tokens: number }
type Trend = { items: { day: string | null; tokens: number }[] }

export default function Dashboard() {
  const stats = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: async () =>
      (await auditApi.get<ApiResult<Stats>>('/admin/stats/overview')).data.data,
  })
  const health = useQuery({
    queryKey: ['admin', 'health'],
    queryFn: async () =>
      (await auditApi.get<ApiResult<Health>>('/admin/health')).data.data,
  })
  const tokens = useQuery({
    queryKey: ['admin', 'tokens'],
    queryFn: async () =>
      (await auditApi.get<ApiResult<TokenStats>>('/admin/stats/tokens')).data.data,
  })
  const trendQ = useQuery({
    queryKey: ['admin', 'token-trend'],
    queryFn: async () =>
      (await auditApi.get<ApiResult<Trend>>('/admin/stats/token-trend')).data.data?.items || [],
  })

  const trend = trendQ.data || []
  const max = Math.max(1, ...trend.map((x) => x.tokens))
  const error =
    stats.isError || health.isError || tokens.isError || trendQ.isError
      ? '加载仪表盘失败'
      : ''

  return (
    <div className="page wide">
      <h1>仪表盘</h1>
      {error && <p className="error">{error}</p>}
      <div className="stat-grid">
        <div className="card">
          <span className="muted">用户</span>
          <strong>{stats.data ? stats.data.users : '…'}</strong>
        </div>
        <div className="card">
          <span className="muted">角色</span>
          <strong>{stats.data ? stats.data.characters : '…'}</strong>
        </div>
        <div className="card">
          <span className="muted">讨论</span>
          <strong>{stats.data ? stats.data.discussions : '…'}</strong>
        </div>
        <div className="card">
          <span className="muted">Token</span>
          <strong>{tokens.data ? tokens.data.tokens : '…'}</strong>
        </div>
      </div>
      <h2>Token 趋势（7 日）</h2>
      {trend.length === 0 && <p className="muted">暂无用量（LLM 记账接入后显示）</p>}
      <ul className="checklist">
        {trend.map((row) => (
          <li key={row.day || 'x'}>
            <span className="muted">{row.day || '—'}</span>
            <span> {row.tokens}</span>
            <div
              className="trend-bar"
              style={{
                height: 8,
                marginTop: 4,
                width: `${Math.round((row.tokens / max) * 100)}%`,
                background: 'var(--accent)',
                borderRadius: 4,
              }}
            />
          </li>
        ))}
      </ul>
      <h2>组件状态</h2>
      <ul className="checklist">
        {health.data &&
          Object.entries(health.data.components || {}).map(([name, c]) => (
            <li key={name}>
              <span className={`status-pill ${c.status}`}>{c.status}</span>
              <strong> {name}</strong>
              {c.latency_ms != null && <span className="muted"> · {c.latency_ms}ms</span>}
              {c.error && <span className="error"> · {c.error}</span>}
            </li>
          ))}
      </ul>
    </div>
  )
}
