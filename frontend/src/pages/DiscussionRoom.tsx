import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import { displayName } from '../lib/displayName'
import { RichText } from '../lib/RichText'

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
  created_at: string
}

/** 把入库的 think 原文尽量收成可读短句（学习版存的是 decision=... 字符串） */
function formatThinkText(content: string): string {
  const decision = content.match(/decision=([^,\s]+)/)?.[1]
  const reasoning = content.match(/reasoning=(.*)$/)?.[1]?.trim()
  if (reasoning) {
    return decision ? `【${decision}】${reasoning}` : reasoning
  }
  return content
}

function bubbleClassName(messageType: string): string {
  if (messageType === 'user_intervene') return 'bubble user'
  if (messageType === 'agent_think') return 'bubble thought'
  if (messageType === 'host_intro' || messageType === 'host_summary') {
    return 'bubble host'
  }
  return 'bubble'
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
  const lastTsRef = useRef<string>('')
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

  // 已加载/收到的最新消息时间戳，作为 SSE 重连时的 after 断点
  useEffect(() => {
    if (messages.length > 0) {
      lastTsRef.current = messages[messages.length - 1].created_at
    }
  }, [messages])

  useEffect(() => {
    if (!id) return
    let es: EventSource | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    const connect = () => {
      // 重连时带上 lastTsRef.current，后端从 PostgreSQL 补发断点之后消息
      const after = lastTsRef.current
      const url = `/api/v1/discussions/${id}/stream${
        after ? `?after=${encodeURIComponent(after)}` : ''
      }`
      es = new EventSource(url)
      setLive(true)

      // 正式消息（已写入 PostgreSQL）：思考/介入/完整发言/总结等
      es.addEventListener('message', (ev) => {
        try {
          const msg = JSON.parse(ev.data) as Message
          // 更新最后收到的时间戳，作为重连断点
          if (msg.created_at && msg.created_at > (lastTsRef.current || '')) {
            lastTsRef.current = msg.created_at
          }
          setMessages((prev) => {
            if (prev.some((m) => m.id === msg.id)) return prev
            // 流式结束后：用正式 message 替换 temp_id=stream-... 的临时气泡，避免两条发言
            // 按 message_type + round_number 匹配，适用于 agent_speak 和 host_summary
            const idx = prev.findIndex(
              (m) =>
                m.id.startsWith('stream-') &&
                m.message_type === msg.message_type &&
                m.round_number === msg.round_number,
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
                created_at: '',
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

      // 主持人开场开始：先插一个空气泡（React 状态），后续 chunk 往里追加
      es.addEventListener('host_intro_start', (ev) => {
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
                message_type: 'host_intro',
                content: '',
                confidence: null,
                created_at: '',
              },
            ]
          })
        } catch {
          // ignore
        }
      })

      // 主持人开场增量：每个 chunk 拼到对应 temp_id 气泡（打字机效果）
      es.addEventListener('host_intro_chunk', (ev) => {
        try {
          const data = JSON.parse(ev.data) as { temp_id: string; content: string }
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

      // 主持人总结开始：先插一个空气泡（React 状态），后续 chunk 往里追加
      es.addEventListener('host_summary_start', (ev) => {
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
                message_type: 'host_summary',
                content: '',
                confidence: null,
                created_at: '',
              },
            ]
          })
        } catch {
          // ignore
        }
      })

      // 主持人总结增量：每个 chunk 拼到对应 temp_id 气泡（打字机效果）
      es.addEventListener('host_summary_chunk', (ev) => {
        try {
          const data = JSON.parse(ev.data) as { temp_id: string; content: string }
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

      // 重连追赶摘要：消息过多时后端只发最近 20 条 + 提示
      es.addEventListener('catchup_summary', (ev) => {
        try {
          const data = JSON.parse(ev.data) as {
            message: string
            total: number
            skipped: number
          }
          setMessages((prev) => [
            ...prev,
            {
              id: `catchup-summary-${Date.now()}`,
              round_number: 0,
              agent_name: '系统',
              message_type: 'catchup_summary',
              content: `${data.message}（共 ${data.total} 条，已省略 ${data.skipped} 条）`,
              confidence: null,
              created_at: new Date().toISOString(),
            },
          ])
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

      es.onerror = () => {
        setLive(false)
        es?.close()
        // 3 秒后重连，携带 lastTsRef.current 作为 after
        reconnectTimer = setTimeout(connect, 3000)
      }

      es.onopen = () => setLive(true)
    }

    connect()

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      es?.close()
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

  async function onResume() {
    // 续聊：对 completed / error 的讨论重新启动编排，保留已有历史
    if (!id) return
    setStarting(true)
    setError('')
    try {
      await api.post(`/discussions/${id}/resume`)
      setDiscussion((d) => (d ? { ...d, status: 'running' } : d))
    } catch {
      setError('续聊失败（可能状态已改变，或后端报错）')
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
      </div>
      <h1>{discussion?.topic || '讨论室'}</h1>
      {discussion?.status === 'pending' && (
        <button onClick={onStart} disabled={starting}>
          {starting ? '启动中…' : '开始讨论'}
        </button>
      )}
      {(discussion?.status === 'completed' || discussion?.status === 'error') && (
        <button onClick={onResume} disabled={starting}>
          {starting ? '续聊中…' : '继续讨论'}
        </button>
      )}
      {error && <p className="error">{error}</p>}
      <div className="messages">
        {messages.length === 0 && <p className="muted">还没有消息</p>}
        {messages.map((m) => (
          <article key={m.id} className={bubbleClassName(m.message_type)}>
            <header>
              <strong>
                {m.message_type === 'user_intervene'
                  ? `观众（${displayName(m.agent_name) || '我'}）`
                  : displayName(m.agent_name) || m.message_type}
              </strong>
              <span className="bubble-meta">
                {/* 视觉区分：思考 vs 发言（对齐参考项目的「内部思考」标签思路） */}
                {m.message_type === 'agent_think' && (
                  <span className="badge thought-badge">内部思考</span>
                )}
                {m.message_type === 'agent_speak' && (
                  <span className="badge speak-badge">发言</span>
                )}
                #{m.round_number}
                {m.confidence != null ? ` · 置信度 ${m.confidence}` : ''}
              </span>
            </header>
            {m.message_type === 'agent_think' ? (
              <p>{formatThinkText(m.content)}</p>
            ) : (
              <RichText text={m.content} />
            )}
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
