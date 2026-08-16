// 角色 Skill 目录编辑器
// 功能：左侧文件树列出 skill 目录全部文件，右侧用 Monaco 编辑当前文件
// 技术：
// - GET /characters/{id}/files 列出相对路径（无 path 参数）
// - GET /characters/{id}/files?path=xxx 读文件内容
// - PUT /characters/{id}/files {path, content} 写回磁盘（会记 skill.file_write 审计）
// - @monaco-editor/react：VS Code 内核编辑器，Markdown 语法高亮

import { useEffect, useState } from 'react'
import Editor from '@monaco-editor/react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

type Character = {
  id: string
  name: string
  status: string
}

function languageOf(path: string): string {
  const lower = path.toLowerCase()
  if (lower.endsWith('.md')) return 'markdown'
  if (lower.endsWith('.json')) return 'json'
  if (lower.endsWith('.yml') || lower.endsWith('.yaml')) return 'yaml'
  if (lower.endsWith('.ts') || lower.endsWith('.tsx')) return 'typescript'
  if (lower.endsWith('.js')) return 'javascript'
  return 'plaintext'
}

export default function CharacterSkill() {
  const { id } = useParams<{ id: string }>()
  const [character, setCharacter] = useState<Character | null>(null)
  const [files, setFiles] = useState<string[]>([])
  const [activePath, setActivePath] = useState('SKILL.md')
  const [content, setContent] = useState('')
  const [dirty, setDirty] = useState(false)
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
      api.get<ApiResult<string[]>>(`/characters/${id}/files`),
    ])
      .then(([cRes, listRes]) => {
        setCharacter(cRes.data.data)
        const listed = listRes.data.data || []
        setFiles(listed)
        const initial = listed.includes('SKILL.md') ? 'SKILL.md' : listed[0] || ''
        setActivePath(initial)
      })
      .catch(() => setError('无法读取技能目录（可能还在生成中，或文件缺失）'))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!id || !activePath) return
    setSavedHint('')
    api
      .get<ApiResult<string>>(`/characters/${id}/files`, {
        params: { path: activePath },
      })
      .then((fRes) => {
        setContent(fRes.data.data || '')
        setDirty(false)
      })
      .catch(() => {
        setError(`无法读取 ${activePath}`)
        setContent('')
      })
  }, [id, activePath])

  async function onSave() {
    if (!id || !activePath) return
    setSaving(true)
    setError('')
    setSavedHint('')
    try {
      await api.put(`/characters/${id}/files`, {
        path: activePath,
        content,
      })
      setDirty(false)
      setSavedHint(`已保存 ${activePath}`)
    } catch {
      setError('保存失败（无权限或后端报错）')
    } finally {
      setSaving(false)
    }
  }

  async function onSelectFile(path: string) {
    if (path === activePath) return
    if (dirty) {
      const ok = window.confirm('当前文件未保存，切换后会丢失修改。继续？')
      if (!ok) return
    }
    setActivePath(path)
  }

  return (
    <div className="page wide">
      <div className="row">
        <Link to="/characters">← 我的角色</Link>
      </div>
      <h1>{character ? `${character.name} · Skill` : '角色 Skill'}</h1>
      {character && <p className="muted">状态：{character.status}</p>}
      {loading && <p className="muted">加载中…</p>}
      {error && <p className="error">{error}</p>}
      {savedHint && <p className="muted">{savedHint}</p>}
      {!loading && files.length === 0 && !error && (
        <p className="error">无法读取技能文件</p>
      )}
      {!loading && files.length > 0 && (
        <div className="skill-layout">
          <aside className="skill-tree">
            <p className="muted">文件</p>
            <ul>
              {files.map((path) => (
                <li key={path}>
                  <button
                    type="button"
                    className={path === activePath ? 'active' : ''}
                    onClick={() => onSelectFile(path)}
                  >
                    {path}
                  </button>
                </li>
              ))}
            </ul>
          </aside>
          <section className="skill-main">
            <div className="row">
              <span className="muted">
                {activePath}
                {dirty ? ' · 未保存' : ''}
              </span>
              <button type="button" onClick={onSave} disabled={saving || !dirty}>
                {saving ? '保存中…' : '保存'}
              </button>
            </div>
            <div className="skill-monaco">
              <Editor
                height="520px"
                theme="vs-dark"
                language={languageOf(activePath)}
                value={content}
                onChange={(value) => {
                  setContent(value ?? '')
                  setDirty(true)
                }}
                options={{
                  minimap: { enabled: false },
                  wordWrap: 'on',
                  fontSize: 14,
                  scrollBeyondLastLine: false,
                }}
              />
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
