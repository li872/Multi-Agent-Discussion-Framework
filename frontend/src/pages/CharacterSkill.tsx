// 查看 / 编辑角色 SKILL.md（人设文件）
// 技术：已有 GET/PUT /characters/{id}/files?path=SKILL.md + textarea 编辑（Monaco 以后再上）

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import LogoutButton from '../components/LogoutButton'

type Character = {
  id: string
  name: string
  status: string
}

export default function CharacterSkill() {
  const { id } = useParams<{ id: string }>()
  const [character, setCharacter] = useState<Character | null>(null)
  const [content, setContent] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savedHint, setSavedHint] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError('')
    Promise.all([
      api.get<ApiResult<Character>>(`/characters/${id}`),
      // path=SKILL.md：读磁盘上的人设正文（Result.data 为 string）
      api.get<ApiResult<string>>(`/characters/${id}/files`, {
        params: { path: 'SKILL.md' },
      }),
    ])
      .then(([cRes, fRes]) => {
        setCharacter(cRes.data.data)
        setContent(fRes.data.data || '')
      })
      .catch(() => setError('无法读取技能文件（可能还在生成中，或文件缺失）'))
      .finally(() => setLoading(false))
  }, [id])

  async function onSave() {
    if (!id) return
    setSaving(true)
    setError('')
    setSavedHint('')
    try {
      await api.put(`/characters/${id}/files`, {
        path: 'SKILL.md',
        content,
      })
      setSavedHint('已保存')
    } catch {
      setError('保存失败（无权限或后端报错）')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page wide">
      <div className="row">
        <Link to="/characters">← 我的角色</Link>
        <LogoutButton />
      </div>
      <h1>{character ? `${character.name} · Skill` : '角色 Skill'}</h1>
      {character && <p className="muted">状态：{character.status}</p>}
      {loading && <p className="muted">加载中…</p>}
      {error && <p className="error">{error}</p>}
      {savedHint && <p className="muted">{savedHint}</p>}
      {!loading && !error && (
        <>
          <textarea
            className="skill-editor"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            spellCheck={false}
          />
          <div className="row" style={{ marginTop: 12 }}>
            <button type="button" onClick={onSave} disabled={saving}>
              {saving ? '保存中…' : '保存 SKILL.md'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
