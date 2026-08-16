import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { auditApi, formatTs } from '../api/client'
import type { ApiResult, PageData } from '../api/client'
import { auditApiBase } from '../api/base'

type DiscRow = {
  id: string
  owner_id: string
  topic: string
  status: string
  duration: number
  created_at: string | null
}

type DiscDetail = DiscRow & {
  messages: {
    id: string
    round_number: number
    agent_name: string | null
    message_type: string
    content: string
    created_at: string | null
  }[]
}

export default function Discussions() {
  const qc = useQueryClient()
  const [detail, setDetail] = useState<DiscDetail | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [live, setLive] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  const list = useQuery({
    queryKey: ['admin', 'discussions'],
    queryFn: async () => {
      const res = await auditApi.get<ApiResult<PageData<DiscRow>>>('/admin/discussions', {
        params: { page: 1, page_size: 50 },
      })
      return res.data.data
    },
  })

  const items = list.data?.items || []
  const total = list.data?.total || 0

  async function openDetail(id: string) {
    try {
      const res = await auditApi.get<ApiResult<DiscDetail>>(`/admin/discussions/${id}`)
      setDetail(res.data.data)
    } catch {
      setError('加载讨论详情失败')
    }
  }

  async function remove(id: string) {
    if (!window.confirm('确认删除该讨论？')) return
    setBusy(id)
    try {
      await auditApi.delete(`/admin/discussions/${id}`)
      if (detail?.id === id) setDetail(null)
      qc.invalidateQueries({ queryKey: ['admin', 'discussions'] })
    } catch {
      setError('删除失败')
    } finally {
      setBusy(null)
    }
  }

  function listen(id: string) {
    esRef.current?.close()
    const token = localStorage.getItem('audit_token') || ''
    const url = `${auditApiBase()}/audit/discussions/${id}/stream?access_token=${encodeURIComponent(token)}`
    const es = new EventSource(url)
    esRef.current = es
    setLive(true)
    es.onerror = () => {
      setLive(false)
      es.close()
    }
  }

  useEffect(() => {
    return () => esRef.current?.close()
  }, [])

  return (
    <div className="page wide">
      <h1>讨论</h1>
      <p className="muted">
        共 {total} 场{live ? ' · 正在旁听' : ''}
      </p>
      {(error || list.isError) && <p className="error">{error || '加载讨论失败'}</p>}
      <ul className="checklist">
        {items.map((d) => (
          <li key={d.id}>
            <strong>{d.topic}</strong>
            <span className={`status-pill ${d.status}`}>{d.status}</span>
            <span className="muted"> · {formatTs(d.created_at)}</span>
            <div className="row">
              <button type="button" onClick={() => openDetail(d.id)}>
                详情
              </button>
              <button type="button" onClick={() => listen(d.id)}>
                旁听
              </button>
              <button type="button" disabled={busy === d.id} onClick={() => remove(d.id)}>
                删除
              </button>
            </div>
          </li>
        ))}
      </ul>
      {items.length === 0 && !error && !list.isError && <p>暂无讨论</p>}
      {detail && (
        <div className="card">
          <h2>{detail.topic}</h2>
          <p className="muted">
            {detail.status} · {detail.messages.length} 条消息
          </p>
          <ul className="checklist">
            {detail.messages.slice(0, 40).map((m) => (
              <li key={m.id}>
                <span className="muted">
                  R{m.round_number} {m.agent_name || m.message_type} · {formatTs(m.created_at)}
                </span>
                <p>{m.content?.slice(0, 200)}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
