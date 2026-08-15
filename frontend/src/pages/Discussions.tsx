import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import LogoutButton from '../components/LogoutButton'

type Discussion = {
  id: string
  topic: string
  status: string
  created_at: string
}

export default function Discussions() {
  const [items, setItems] = useState<Discussion[]>([])
  const [error, setError] = useState('')

  async function refresh() {
    const res = await api.get<ApiResult<{ items: Discussion[] }>>('/discussions')
    setItems(res.data.data.items || [])
  }

  useEffect(() => {
    refresh().catch(() => setError('加载讨论失败'))
  }, [])

  async function onDelete(id: string, topic: string) {
    if (!window.confirm(`确定删除讨论「${topic}」？`)) return
    setError('')
    try {
      // 软删除：后端写 deleted_at，列表不再返回
      await api.delete(`/discussions/${id}`)
      setItems((prev) => prev.filter((d) => d.id !== id))
    } catch {
      setError('删除失败')
    }
  }

  return (
    <div className="page">
      <div className="row">
        <Link to="/characters">← 我的角色</Link>
        <Link to="/discussions/new">新建讨论</Link>
        <LogoutButton />
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
            <button type="button" onClick={() => onDelete(d.id, d.topic)}>
              删除
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
