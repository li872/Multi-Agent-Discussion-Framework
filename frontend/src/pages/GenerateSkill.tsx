// 完整 Nuwa Skill 生成页面
// 流程：
// 1. 选推荐人物 / 手动输入人名 + 补充说明
// 2. POST /characters 创建占位角色
// 3. POST /characters/{id}/generate 触发完整 Nuwa 管线
// 4. EventSource 连接 /characters/{id}/generation-progress 接收 main/sub/tool/done/error 事件
//
// 技术：React + SSE + axios

import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import LogoutButton from '../components/LogoutButton'

type ProgressEvent = {
  level: 'main' | 'sub' | 'tool' | 'done' | 'error'
  message: string
  agent?: string
  tool?: string
  query?: string
  file_count?: number
  source_count?: number
}

type Character = {
  id: string
  name: string
  status: string
}

export default function GenerateSkill() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [recommendations, setRecommendations] = useState<string[]>([])
  const [recSource, setRecSource] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState<'idle' | 'generating' | 'done' | 'error'>('idle')
  const [mainLogs, setMainLogs] = useState<string[]>([])
  const [subAgents, setSubAgents] = useState<Set<string>>(new Set())
  const [toolLogs, setToolLogs] = useState<string[]>([])
  const [doneInfo, setDoneInfo] = useState<ProgressEvent | null>(null)

  useEffect(() => {
    api
      .get<ApiResult<{ items: string[]; source: string }>>('/characters/recommendations')
      .then((res) => {
        const data = res.data.data
        setRecommendations(data.items || [])
        setRecSource(data.source || 'fallback')
      })
      .catch(() => {
        // 推荐接口失败时静默，不影响主功能
      })
  }, [])

  function onPickRecommendation(person: string) {
    setName(person)
    setDescription(`蒸馏 ${person} 的视角与思维框架`)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('请填写人物名')
      return
    }
    setError('')
    setLoading(true)
    setStatus('generating')
    setMainLogs([])
    setSubAgents(new Set())
    setToolLogs([])
    setDoneInfo(null)

    try {
      // 1. 创建占位角色（状态 ready，后续会被生成任务覆盖）
      const createRes = await api.post<ApiResult<Character>>('/characters', {
        name: name.trim(),
        description: description.trim(),
        tags: [],
        is_public: false,
      })
      const character = createRes.data.data

      // 2. 触发完整 Nuwa 管线
      await api.post<ApiResult<Character>>(`/characters/${character.id}/generate`)

      // 3. 连接 SSE 进度流
      connectProgress(character.id)
    } catch {
      setError('创建或触发生成失败')
      setStatus('error')
      setLoading(false)
    }
  }

  function connectProgress(skillId: string) {
    const es = new EventSource(`/api/v1/characters/${skillId}/generation-progress`)
    let heartbeatTimer: number | null = null

    const resetHeartbeat = () => {
      if (heartbeatTimer) window.clearTimeout(heartbeatTimer)
      heartbeatTimer = window.setTimeout(() => {
        es.close()
        setStatus('error')
        setError('生成进度连接超时，请刷新页面或查看角色列表')
        setLoading(false)
      }, 60000)
    }
    resetHeartbeat()

    es.addEventListener('generation_progress', (ev) => {
      resetHeartbeat()
      try {
        const data = JSON.parse(ev.data) as ProgressEvent
        handleProgress(data)
      } catch {
        // ignore
      }
    })

    es.addEventListener('error', () => {
      // SSE 连接错误：如果是生成结束后端关闭 channel，会触发这里，但不一定是失败
    })

    es.onerror = () => {
      es.close()
      if (heartbeatTimer) window.clearTimeout(heartbeatTimer)
      setLoading(false)
    }
  }

  function handleProgress(data: ProgressEvent) {
    if (data.level === 'main') {
      setMainLogs((prev) => [...prev, data.message])
    } else if (data.level === 'sub') {
      setSubAgents((prev) => new Set([...prev, data.agent || data.message]))
    } else if (data.level === 'tool') {
      const log = data.query ? `搜索：${data.query}` : data.message
      setToolLogs((prev) => [...prev, log])
    } else if (data.level === 'done') {
      setDoneInfo(data)
      setStatus('done')
      setLoading(false)
    } else if (data.level === 'error') {
      setError(data.message)
      setStatus('error')
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="row">
        <Link to="/">← 首页</Link>
        <Link to="/characters">我的角色</Link>
        <LogoutButton />
      </div>
      <h1>AI 生成角色 Skill（完整 Nuwa 管线）</h1>

      {recommendations.length > 0 && (
        <div className="card">
          <p className="muted">推荐人物（来源：{recSource === 'llm' ? 'LLM' : '静态池'}，点击填入）</p>
          <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
            {recommendations.map((person) => (
              <button
                key={person}
                type="button"
                className="tag"
                onClick={() => onPickRecommendation(person)}
              >
                {person}
              </button>
            ))}
          </div>
        </div>
      )}

      <form className="card" onSubmit={onSubmit}>
        <label>
          人物名
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：Steve Jobs"
          />
        </label>
        <label>
          补充说明（可选）
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="希望重点提炼的方向、领域或问题"
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? '生成中…' : '开始完整生成'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {status !== 'idle' && (
        <div className="card">
          <h3>生成状态：{status === 'generating' ? '进行中…' : status === 'done' ? '完成' : '失败'}</h3>

          {subAgents.size > 0 && (
            <div style={{ marginTop: 12 }}>
              <p className="muted">子 Agent</p>
              <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
                {Array.from(subAgents).map((agent) => (
                  <span key={agent} className="badge">
                    {agent}
                  </span>
                ))}
              </div>
            </div>
          )}

          {toolLogs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <p className="muted">工具调用</p>
              <ul className="tool-log">
                {toolLogs.slice(-20).map((log, idx) => (
                  <li key={idx}>{log}</li>
                ))}
              </ul>
            </div>
          )}

          {mainLogs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <p className="muted">主阶段</p>
              <div className="progress-log">
                {mainLogs.slice(-10).map((log, idx) => (
                  <p key={idx}>{log}</p>
                ))}
              </div>
            </div>
          )}

          {doneInfo && (
            <div style={{ marginTop: 12 }}>
              <p className="success">
                {doneInfo.message}（文件数：{doneInfo.file_count}，来源数：{doneInfo.source_count}）
              </p>
              <button
                type="button"
                onClick={() => navigate('/characters')}
                style={{ marginTop: 8 }}
              >
                去角色列表查看
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
