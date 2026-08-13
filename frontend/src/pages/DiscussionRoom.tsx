import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

type Discussion = {
  id: string
  topic: string
  status: string
}

type Message = {
  id: string
  round_number: number
  agent_name: string | null
  message_type: string
  content: string
  confidence: number | null
}

export default function DiscussionRoom() {
  const { id } = useParams<{ id: string }>()
  const [discussion, setDiscussion] = useState<Discussion | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)

  async function refresh() {
    if (!id) return
    const [dRes, mRes] = await Promise.all([
      api.get<ApiResult<Discussion>>(`/discussions/${id}`),
      api.get<ApiResult<Message[]>>(`/discussions/${id}/messages`),
    ])
    setDiscussion(dRes.data.data)
    setMessages(mRes.data.data || [])
  }

  useEffect(() => {
    refresh().catch(() => setError('加载讨论失败'))
    const timer = setInterval(() => {
      refresh().catch(() => {})
    }, 3000)
    return () => clearInterval(timer)
  }, [id])

  async function onStart() {
    if (!id) return
    setStarting(true)
    setError('')
    try {
      await api.post(`/discussions/${id}/start`)
      await refresh()
    } catch {
      setError('启动失败（可能已启动过，或后端报错）')
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="page wide">
      <div className="row">
        <Link to="/discussions/new">← 新建讨论</Link>
        <span className="status">状态：{discussion?.status || '…'}</span>
      </div>
      <h1>{discussion?.topic || '讨论室'}</h1>
      {discussion?.status === 'pending' && (
        <button onClick={onStart} disabled={starting}>
          {starting ? '启动中…' : '开始讨论'}
        </button>
      )}
      {error && <p className="error">{error}</p>}
      <div className="messages">
        {messages.length === 0 && <p className="muted">还没有消息</p>}
        {messages.map((m) => (
          <article key={m.id} className="bubble">
            <header>
              <strong>{m.agent_name || m.message_type}</strong>
              <span>
                #{m.round_number} · {m.message_type}
                {m.confidence != null ? ` · ${m.confidence}` : ''}
              </span>
            </header>
            <p>{m.content}</p>
          </article>
        ))}
      </div>
    </div>
  )
}