import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

type Discussion = {
  id: string
  topic: string
  status: string
  created_at: string
}

export default function Discussions() {
  const [items, setItems] = useState<Discussion[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get<ApiResult<{ items: Discussion[] }>>('/discussions')
      .then((res) => setItems(res.data.data.items || []))
      .catch(() => setError('加载讨论失败'))
  }, [])

  return (
    <div className="page">
      <div className="row">
        <Link to="/characters">← 我的角色</Link>
        <Link to="/discussions/new">新建讨论</Link>
      </div>
      <h1>我的讨论</h1>
      {error && <p className="error">{error}</p>}
      {items.length === 0 && !error && <p>暂无讨论</p>}
      <ul className="checklist">
        {items.map((d) => (
          <li key={d.id}>
            <Link to={`/discussions/${d.id}`}>
              <strong>{d.topic}</strong>
            </Link>
            <span> · {d.status}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}