import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

type Character = {
  id: string
  name: string
  description: string
  status: string
}

export default function Gallery() {
  const [characters, setCharacters] = useState<Character[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get<ApiResult<{ items: Character[] }>>('/characters/gallery')
      .then((res) => setCharacters(res.data.data.items || []))
      .catch(() => setError('加载画廊失败'))
  }, [])

  return (
    <div className="page">
      <div className="row">
        <Link to="/characters">← 我的角色</Link>
        <Link to="/discussions">我的讨论</Link>
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
          </li>
        ))}
      </ul>
    </div>
  )
}
