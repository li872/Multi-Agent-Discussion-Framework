import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

type Discussion = {
  id: string
  topic: string
  status: string
  created_at: string
}

export default function Discussions() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const list = useQuery({
    queryKey: ['discussions', debounced],
    queryFn: async () => {
      const params = debounced ? `?search=${encodeURIComponent(debounced)}` : ''
      const res = await api.get<ApiResult<{ items: Discussion[] }>>(`/discussions${params}`)
      return res.data.data.items || []
    },
  })

  async function onDelete(id: string, topic: string) {
    if (!window.confirm(`确定删除讨论「${topic}」？`)) return
    setError('')
    try {
      await api.delete(`/discussions/${id}`)
      qc.invalidateQueries({ queryKey: ['discussions'] })
    } catch {
      setError('删除失败')
    }
  }

  const items = list.data || []

  return (
    <div className="page">
      <h1>我的讨论</h1>
      <div className="row" style={{ marginTop: 16, marginBottom: 8 }}>
        <input
          placeholder="搜索讨论主题或状态"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, maxWidth: 400 }}
        />
        <Link to="/discussions/new">新建讨论</Link>
      </div>
      {(error || list.isError) && <p className="error">{error || '加载讨论失败'}</p>}
      {items.length === 0 && !error && !list.isError && <p>暂无讨论</p>}
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
