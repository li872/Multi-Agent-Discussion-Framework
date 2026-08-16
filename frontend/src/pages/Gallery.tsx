import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
type Character = {
  id: string
  name: string
  description: string
  status: string
  quotes?: string[]
}

export default function Gallery() {
  const [characters, setCharacters] = useState<Character[]>([])
  const [error, setError] = useState('')
  const [copying, setCopying] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  async function refresh(q = '') {
    const params = q ? `?search=${encodeURIComponent(q)}` : ''
    const res = await api.get<ApiResult<{ items: Character[] }>>(
      `/characters/gallery${params}`,
    )
    setCharacters(res.data.data.items || [])
  }

  // 搜索防抖：300ms 防抖后请求 GET /characters/gallery?search=xxx
  useEffect(() => {
    const timer = setTimeout(() => {
      refresh(search).catch(() => setError('加载画廊失败'))
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  async function onCopy(id: string, name: string) {
    setCopying(id)
    setError('')
    try {
      await api.post(`/characters/${id}/copy`)
      alert(`已复制「${name}」到我的角色`)
    } catch {
      setError('复制失败（可能未登录或角色非公开）')
    } finally {
      setCopying(null)
    }
  }

  return (
    <div className="page">
      <h1>公开画廊</h1>
      <div className="row" style={{ marginTop: 16, marginBottom: 8 }}>
        <input
          placeholder="搜索公开角色名或描述"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, maxWidth: 400 }}
        />
      </div>
      {error && <p className="error">{error}</p>}
      {characters.length === 0 && !error && <p>暂无公开角色</p>}
      <ul className="checklist">
        {characters.map((c) => (
          <li key={c.id}>
            <strong>{c.name}</strong>
            <span> · {c.status}</span>
            {c.description ? (
              <p className="quote">{c.description}</p>
            ) : null}
            {c.quotes && c.quotes.length > 1 && (
              <p className="muted">另有 {c.quotes.length - 1} 条引用语</p>
            )}
            <button
              type="button"
              disabled={copying === c.id}
              onClick={() => onCopy(c.id, c.name)}
            >
              {copying === c.id ? '复制中…' : '复制到我的角色'}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
