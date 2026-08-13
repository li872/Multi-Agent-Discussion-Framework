import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

type Character = { id: string; name: string }

export default function NewDiscussion() {
  const navigate = useNavigate()
  const [characters, setCharacters] = useState<Character[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [topic, setTopic] = useState('创新与执行哪个更重要')
  const [duration, setDuration] = useState(60)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api
      .get<ApiResult<{ items: Character[] }>>('/characters')
      .then((res) => setCharacters(res.data.data.items || []))
      .catch(() => setError('加载角色失败'))
  }, [])

  function toggle(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!topic.trim() || selected.length === 0) {
      setError('请填写主题并至少选择一个角色')
      return
    }
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post<ApiResult<{ id: string }>>('/discussions', {
        topic,
        character_ids: selected,
        duration,
      })
      if (data.code !== 200) {
        setError(data.message || '创建失败')
        return
      }
      navigate(`/discussions/${data.data.id}`)
    } catch {
      setError('创建讨论失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <h1>新建讨论</h1>
      <form onSubmit={onSubmit} className="card">
        <label>
          主题
          <input value={topic} onChange={(e) => setTopic(e.target.value)} />
        </label>
        <label>
          时长（秒）
          <input
            type="number"
            min={60}
            max={3600}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
          />
        </label>
        <div>
          <p>选择角色（可多选）</p>
          {characters.length === 0 && <p>暂无角色，请先在后端创建</p>}
          <ul className="checklist">
            {characters.map((c) => (
              <li key={c.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={selected.includes(c.id)}
                    onChange={() => toggle(c.id)}
                  />
                  {c.name.replace('-perspective', '')}
                </label>
              </li>
            ))}
          </ul>
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? '创建中…' : '创建并进入讨论室'}
        </button>
      </form>
    </div>
  )
}