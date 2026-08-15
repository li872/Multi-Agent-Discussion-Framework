import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import LogoutButton from '../components/LogoutButton'

type Character = {
  id: string
  name: string
  description: string
  status: string
}

export default function Gallery() {
  const [characters, setCharacters] = useState<Character[]>([])
  const [error, setError] = useState('')
  const [copying, setCopying] = useState<string | null>(null)

  async function refresh() {
    const res = await api.get<ApiResult<{ items: Character[] }>>('/characters/gallery')
    setCharacters(res.data.data.items || [])
  }

  useEffect(() => {
    refresh().catch(() => setError('加载画廊失败'))
  }, [])

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
      <div className="row">
        <Link to="/characters">← 我的角色</Link>
        <Link to="/discussions">我的讨论</Link>
        <LogoutButton />
      </div>
      <h1>公开画廊</h1>
      {error && <p className="error">{error}</p>}
      {characters.length === 0 && !error && <p>暂无公开角色</p>}
      <ul className="checklist">
        {characters.map((c) => (
          <li key={c.id}>
            <strong>{c.name}</strong>
            <span> · {c.status}</span>
            {c.description ? <p>{c.description}</p> : null}
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
