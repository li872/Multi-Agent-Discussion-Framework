import { useEffect, useState } from 'react'
import { auditApi } from '../api/client'
import type { ApiResult } from '../api/client'

type Stats = { users: number; characters: number; discussions: number }
type Health = {
  components: Record<string, { status: string; latency_ms?: number; error?: string }>
}
type TokenStats = { tokens: number }
type Trend = { items: { day: string | null; tokens: number }[] }

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [tokens, setTokens] = useState<TokenStats | null>(null)
  const [trend, setTrend] = useState<Trend['items']>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      auditApi.get<ApiResult<Stats>>('/admin/stats/overview'),
      auditApi.get<ApiResult<Health>>('/admin/health'),
      auditApi.get<ApiResult<TokenStats>>('/admin/stats/tokens'),
      auditApi.get<ApiResult<Trend>>('/admin/stats/token-trend'),
    ])
      .then(([s, h, t, tr]) => {
        setStats(s.data.data)
        setHealth(h.data.data)
        setTokens(t.data.data)
        setTrend(tr.data.data?.items || [])
      })
      .catch(() => setError('加载仪表盘失败'))
  }, [])

  const max = Math.max(1, ...trend.map((x) => x.tokens))

  return (
    <div className="page wide">
      <h1>仪表盘</h1>
      {error && <p className="error">{error}</p>}
      <div className="stat-grid">
        <div className="card">
          <span className="muted">用户</span>
          <strong>{stats ? stats.users : '…'}</strong>
        </div>
        <div className="card">
          <span className="muted">角色</span>
          <strong>{stats ? stats.characters : '…'}</strong>
        </div>
        <div className="card">
          <span className="muted">讨论</span>
          <strong>{stats ? stats.discussions : '…'}</strong>
        </div>
        <div className="card">
          <span className="muted">Token</span>
          <strong>{tokens ? tokens.tokens : '…'}</strong>
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
        {health &&
          Object.entries(health.components || {}).map(([name, c]) => (
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
