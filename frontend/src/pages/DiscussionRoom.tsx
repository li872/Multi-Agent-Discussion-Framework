import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import LogoutButton from '../components/LogoutButton'

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
  const [live, setLive] = useState(false)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)

  async function loadOnce() {
    if (!id) return
    const [dRes, mRes] = await Promise.all([
      api.get<ApiResult<Discussion>>(`/discussions/${id}`),
      api.get<ApiResult<Message[]>>(`/discussions/${id}/messages`),
    ])
    setDiscussion(dRes.data.data)
    setMessages(mRes.data.data || [])
  }

  useEffect(() => {
    loadOnce().catch(() => setError('加载讨论失败'))
  }, [id])

  useEffect(() => {
    if (!id) return
    // SSE：浏览器 EventSource 长连接；后端把 Redis 频道转成 event/data 推过来
    const es = new EventSource(`/api/v1/discussions/${id}/stream`)
    setLive(true)

    // 正式消息（已写入 PostgreSQL）：思考/介入/完整发言等
    es.addEventListener('message', (ev) => {
      try {
        const msg = JSON.parse(ev.data) as Message
        setMessages((prev) => {
          if (prev.some((m) => m.id === msg.id)) return prev
          // 流式结束后：用正式 message 替换 temp_id=stream-... 的临时气泡，避免两条发言
          const idx = prev.findIndex(
            (m) =>
              m.id.startsWith('stream-') &&
              m.message_type === 'agent_speak' &&
              m.agent_name === msg.agent_name &&
              msg.message_type === 'agent_speak',
          )
          if (idx >= 0) {
            const next = [...prev]
            next[idx] = msg
            return next
          }
          return [...prev, msg]
        })
      } catch {
        // ignore bad payload
      }
    })

    // 发言开始：先插一个空气泡（React 状态），后续 chunk 往里追加
    es.addEventListener('agent_speak_start', (ev) => {
      try {
        const data = JSON.parse(ev.data) as {
          temp_id: string
          agent_name: string
          round: number
        }
        setMessages((prev) => {
          if (prev.some((m) => m.id === data.temp_id)) return prev
          return [
            ...prev,
            {
              id: data.temp_id,
              round_number: data.round,
              agent_name: data.agent_name,
              message_type: 'agent_speak',
              content: '',
              confidence: null,
            },
          ]
        })
      } catch {
        // ignore
      }
    })

    // 发言增量：每个 chunk 拼到对应 temp_id 气泡（打字机效果）
    es.addEventListener('agent_speak_chunk', (ev) => {
      try {
        const data = JSON.parse(ev.data) as {
          temp_id: string
          content: string
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === data.temp_id
              ? { ...m, content: m.content + data.content }
              : m,
          ),
        )
      } catch {
        // ignore
      }
    })

    es.addEventListener('status', (ev) => {
      try {
        const data = JSON.parse(ev.data) as { status: string }
        setDiscussion((d) => (d ? { ...d, status: data.status } : d))
      } catch {
        // ignore
      }
    })

    es.onerror = () => setLive(false)
    es.onopen = () => setLive(true)

    return () => {
      es.close()
      setLive(false)
    }
  }, [id])

  async function onStart() {
    if (!id) return
    setStarting(true)
    setError('')
    try {
      await api.post(`/discussions/${id}/start`)
      setDiscussion((d) => (d ? { ...d, status: 'running' } : d))
    } catch {
      setError('启动失败（可能已启动过，或后端报错）')
    } finally {
      setStarting(false)
    }
  }

  async function onIntervene(e: FormEvent) {
    e.preventDefault()
    if (!id || !draft.trim() || sending) return
    setSending(true)
    setError('')
    try {
      await api.post(`/discussions/${id}/intervene`, { content: draft.trim() })
      setDraft('')
    } catch {
      setError('发送失败（讨论未进行中，或后端报错）')
    } finally {
      setSending(false)
    }
  }

  const canIntervene =
    discussion?.status === 'running' || discussion?.status === 'starting'

  return (
    <div className="page wide">
      <div className="row">
        <Link to="/discussions">← 我的讨论</Link>
        <span className="status">
          状态：{discussion?.status || '…'}
          {live ? ' · 实时' : ' · 未连接'}
        </span>
        <LogoutButton />
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
          <article
            key={m.id}
            className={
              m.message_type === 'user_intervene' ? 'bubble user' : 'bubble'
            }
          >
            <header>
              <strong>
                {m.message_type === 'user_intervene'
                  ? `观众（${m.agent_name || '我'}）`
                  : m.agent_name || m.message_type}
              </strong>
              <span>
                #{m.round_number} · {m.message_type}
                {m.confidence != null ? ` · ${m.confidence}` : ''}
              </span>
            </header>
            <p>{m.content}</p>
          </article>
        ))}
      </div>
      {canIntervene && (
        <form className="composer" onSubmit={onIntervene}>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="输入你的观点，Enter 发送"
            disabled={sending}
            maxLength={2000}
          />
          <button type="submit" disabled={sending || !draft.trim()}>
            {sending ? '发送中…' : '发送'}
          </button>
        </form>
      )}
    </div>
  )
}
