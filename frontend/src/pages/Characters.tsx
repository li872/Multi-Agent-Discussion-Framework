import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import { displayName } from '../lib/displayName'

type Character = {
  id: string
  name: string
  description: string
  status: string
  is_public: boolean
  quotes?: string[]
}

export default function Characters() {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const list = useQuery({
    queryKey: ['characters', debounced],
    queryFn: async () => {
      const params = debounced ? `?search=${encodeURIComponent(debounced)}` : ''
      const res = await api.get<ApiResult<{ items: Character[] }>>(`/characters${params}`)
      return res.data.data.items || []
    },
    refetchInterval: (q) =>
      (q.state.data || []).some((c) => c.status === 'generating') ? 3000 : false,
  })

  const createMut = useMutation({
    mutationFn: () =>
      api.post('/characters', {
        name: name.trim(),
        description: description.trim(),
        tags: [],
        is_public: false,
      }),
    onSuccess: () => {
      setName('')
      setDescription('')
      qc.invalidateQueries({ queryKey: ['characters'] })
    },
    onError: () => setError('创建失败（名字可能重复，或后端报错）'),
  })

  const genMut = useMutation({
    mutationFn: () =>
      api.post('/characters/generate', {
        name: name.trim(),
        description: description.trim(),
      }),
    onSuccess: () => {
      setName('')
      setDescription('')
      qc.invalidateQueries({ queryKey: ['characters'] })
    },
    onError: () => setError('生成失败（名字可能重复，或 LLM/后端报错）'),
  })

  const characters = list.data || []

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('请填写角色名')
      return
    }
    setError('')
    createMut.mutate()
  }

  async function onGenerate() {
    if (!name.trim()) {
      setError('请填写要生成的人物名')
      return
    }
    setError('')
    genMut.mutate()
  }

  async function onDelete(id: string, charName: string) {
    if (!window.confirm(`确定删除角色「${charName}」？`)) return
    setError('')
    try {
      await api.delete(`/characters/${id}`)
      qc.invalidateQueries({ queryKey: ['characters'] })
    } catch {
      setError('删除失败')
    }
  }

  async function onTogglePublic(id: string, current: boolean) {
    setError('')
    try {
      await api.put(`/characters/${id}`, { is_public: !current })
      qc.invalidateQueries({ queryKey: ['characters'] })
    } catch {
      setError('修改可见性失败')
    }
  }

  return (
    <div className="page">
      <h1>我的角色</h1>
      <form className="card" onSubmit={onCreate}>
        <label>
          角色名
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          描述 / 生成补充说明
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <div className="row">
          <button type="submit" disabled={createMut.isPending || genMut.isPending}>
            {createMut.isPending ? '创建中…' : '手动创建'}
          </button>
          <button
            type="button"
            disabled={createMut.isPending || genMut.isPending}
            onClick={() => onGenerate()}
          >
            {genMut.isPending ? '提交生成…' : 'AI 生成 Skill'}
          </button>
        </div>
      </form>
      <div className="row" style={{ marginTop: 16, marginBottom: 8 }}>
        <input
          placeholder="搜索角色名或描述"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, maxWidth: 400 }}
        />
      </div>
      {(error || list.isError) && <p className="error">{error || '加载角色失败'}</p>}
      {characters.length === 0 && !error && !list.isError && <p>暂无角色</p>}
      <ul className="checklist">
        {characters.map((c) => (
          <li key={c.id}>
            <strong>{displayName(c.name)}</strong>
            <span> · {c.status}</span>
            {c.status === 'generating' && (
              <span className="muted">（后台生成中，约数十秒）</span>
            )}
            {c.description ? <p className="quote">{c.description}</p> : null}
            {c.quotes && c.quotes.length > 1 && (
              <p className="muted">另有 {c.quotes.length - 1} 条引用语</p>
            )}
            <div className="row">
              <Link to={`/characters/${c.id}/skill`}>查看 / 编辑 Skill</Link>
              <button type="button" onClick={() => onTogglePublic(c.id, c.is_public)}>
                {c.is_public ? '设为私有' : '公开到画廊'}
              </button>
              <button type="button" onClick={() => onDelete(c.id, displayName(c.name))}>
                删除
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
