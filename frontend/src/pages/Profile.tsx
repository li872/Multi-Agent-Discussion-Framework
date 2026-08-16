import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

type User = {
  id: string
  username: string
  phone: string | null
  created_at: string
}

export default function Profile() {
  const [username, setUsername] = useState('')
  const [phone, setPhone] = useState('')
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [saving, setSaving] = useState(false)

  const me = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const { data } = await api.get<ApiResult<User>>('/auth/me')
      if (data.code !== 200) throw new Error(data.message || '加载失败')
      return data.data
    },
  })

  useEffect(() => {
    if (!me.data) return
    setUsername(me.data.username)
    setPhone(me.data.phone || '')
  }, [me.data])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSaving(true)

    const payload: Record<string, string> = {}
    if (username.trim() && username !== me.data?.username) {
      payload.username = username.trim()
    }
    if (phone.trim() !== (me.data?.phone || '')) {
      payload.phone = phone.trim()
    }
    if (newPassword) {
      payload.old_password = oldPassword
      payload.new_password = newPassword
    }

    if (Object.keys(payload).length === 0) {
      setSuccess('没有修改')
      setSaving(false)
      return
    }

    try {
      const { data } = await api.put<ApiResult<User>>('/auth/me', payload)
      if (data.code !== 200) {
        setError(data.message || '更新失败')
        return
      }
      setOldPassword('')
      setNewPassword('')
      setSuccess('保存成功')
      me.refetch()
    } catch {
      setError('更新失败，请检查旧密码或后端是否启动')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page">
      <h1>个人中心</h1>
      {(error || me.isError) && <p className="error">{error || '加载用户信息失败'}</p>}
      {success && <p className="success">{success}</p>}
      <form onSubmit={onSubmit} className="card">
        <label>
          用户名
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          手机号
          <input value={phone} onChange={(e) => setPhone(e.target.value)} />
        </label>
        <hr />
        <label>
          旧密码（改密码时必填）
          <input
            type="password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            placeholder="不修改密码可留空"
          />
        </label>
        <label>
          新密码
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="不修改密码可留空"
          />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? '保存中…' : '保存'}
        </button>
      </form>
    </div>
  )
}
