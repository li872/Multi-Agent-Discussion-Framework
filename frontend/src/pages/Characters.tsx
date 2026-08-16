// 角色列表 + 手动创建 + AI 生成（学习版）
// 原理：
// - 手动创建：POST /characters → 立刻 ready
// - AI 生成：POST /characters/generate → 先 generating，后台 LLM 写 SKILL.md
// - 列表里若有 generating，定时 GET /characters 刷新，直到变成 ready/error
// - 搜索：前端输入框 → 300ms 防抖 → 请求 GET /characters?search=xxx

import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
type Character = {
  id: string
  name: string
  description: string
  status: string
  is_public: boolean
  quotes?: string[]
}

export default function Characters() {
  const [characters, setCharacters] = useState<Character[]>([])
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [search, setSearch] = useState('')

  async function refreshList(q = '') {
    const params = q ? `?search=${encodeURIComponent(q)}` : ''
    const res = await api.get<ApiResult<{ items: Character[] }>>(
      `/characters${params}`,
    )
    setCharacters(res.data.data.items || [])
  }

  // 搜索防抖：300ms 内不再输入才发请求，避免连续按键时频繁请求后端
  useEffect(() => {
    const timer = setTimeout(() => {
      refreshList(search).catch(() => setError('加载角色失败'))
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  useEffect(() => {
    const hasGenerating = characters.some((c) => c.status === 'generating')
    if (!hasGenerating) return
    const timer = setInterval(() => {
      refreshList(search).catch(() => {})
    }, 3000)
    return () => clearInterval(timer)
  }, [characters, search])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('请填写角色名')
      return
    }
    setError('')
    setSaving(true)
    try {
      await api.post('/characters', {
        name: name.trim(),
        description: description.trim(),
        tags: [],
        is_public: false,
      })
      setName('')
      setDescription('')
      await refreshList(search)
    } catch {
      setError('创建失败（名字可能重复，或后端报错）')
    } finally {
      setSaving(false)
    }
  }

  async function onGenerate() {
    if (!name.trim()) {
      setError('请填写要生成的人物名')
      return
    }
    setError('')
    setGenerating(true)
    try {
      await api.post('/characters/generate', {
        name: name.trim(),
        description: description.trim(),
      })
      setName('')
      setDescription('')
      await refreshList(search)
    } catch {
      setError('生成失败（名字可能重复，或 LLM/后端报错）')
    } finally {
      setGenerating(false)
    }
  }

  async function onDelete(id: string, charName: string) {
    if (!window.confirm(`确定删除角色「${charName}」？`)) return
    setError('')
    try {
      await api.delete(`/characters/${id}`)
      setCharacters((prev) => prev.filter((c) => c.id !== id))
    } catch {
      setError('删除失败')
    }
  }

  async function onTogglePublic(id: string, current: boolean) {
    setError('')
    try {
      await api.put(`/characters/${id}`, { is_public: !current })
      setCharacters((prev) =>
        prev.map((c) => (c.id === id ? { ...c, is_public: !current } : c)),
      )
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
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <div className="row">
          <button type="submit" disabled={saving || generating}>
            {saving ? '创建中…' : '手动创建'}
          </button>
          <button
            type="button"
            disabled={saving || generating}
            onClick={() => onGenerate()}
          >
            {generating ? '提交生成…' : 'AI 生成 Skill'}
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

      {error && <p className="error">{error}</p>}
      {characters.length === 0 && !error && <p>暂无角色</p>}
      <ul className="checklist">
        {characters.map((c) => (
          <li key={c.id}>
            <strong>{c.name}</strong>
            <span> · {c.status}</span>
            {c.status === 'generating' && (
              <span className="muted">（后台生成中，约数十秒）</span>
            )}
            {c.description ? (
              <p className="quote">{c.description}</p>
            ) : null}
            {c.quotes && c.quotes.length > 1 && (
              <p className="muted">另有 {c.quotes.length - 1} 条引用语</p>
            )}
            <div className="row">
              <Link to={`/characters/${c.id}/skill`}>查看 / 编辑 Skill</Link>
              <button
                type="button"
                onClick={() => onTogglePublic(c.id, c.is_public)}
              >
                {c.is_public ? '设为私有' : '公开到画廊'}
              </button>
              <button type="button" onClick={() => onDelete(c.id, c.name)}>
                删除
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
