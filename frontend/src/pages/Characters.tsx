// 角色下拉列表显示

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import type { FormEvent } from 'react'
import LogoutButton from '../components/LogoutButton'

type Character = {
    id: string
    name: string
    description: string
    status: string
}

export default function Characters() {
    const [characters, setCharacters] = useState<Character[]>([])
    const [error, setError] = useState('')
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [saving, setSaving] = useState(false)

    useEffect(() => {
        api
            .get<ApiResult<{ items: Character[] }>>('/characters')
            .then((res) => setCharacters(res.data.data.items || []))
            .catch(() => setError('加载角色失败'))
    }, [])
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
            const res = await api.get<ApiResult<{ items: Character[] }>>('/characters')
            setCharacters(res.data.data.items || [])
        } catch {
            setError('创建失败（名字可能重复，或后端报错）')
        } finally {
            setSaving(false)
        }
    }
    async function onDelete(id: string, name: string) {
    if (!window.confirm(`确定删除角色「${name}」？`)) return
    setError('')
    try {
        await api.delete(`/characters/${id}`)
        setCharacters((prev) => prev.filter((c) => c.id !== id))
    } catch {
        setError('删除失败')
    }
    }


    return (
        <div className="page">
            <div className="row">
                <Link to="/discussions">我的讨论</Link>
                <LogoutButton />
            </div>
            <h1>我的角色</h1>
            <form className="card" onSubmit={onCreate}>
                <label>
                    角色名
                    <input value={name} onChange={(e) => setName(e.target.value)} />
                </label>
                <label>
                    描述
                    <input
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                    />
                </label>
                <button type="submit" disabled={saving}>
                    {saving ? '创建中…' : '创建角色'}
                </button>
            </form>
            {error && <p className="error">{error}</p>}
            {characters.length === 0 && !error && <p>暂无角色</p>}
            <ul className="checklist">
                {characters.map((c) => (
                    <li key={c.id}>
                        <strong>{c.name}</strong>
                        <span> · {c.status}</span>
                        {c.description ? <p>{c.description}</p> : null}
                        <button type="button" onClick={() => onDelete(c.id, c.name)}>
                          删除
                        </button>
                    </li>
                ))}
            </ul>
        </div>
    )
}