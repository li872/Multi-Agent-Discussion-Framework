import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import LogoutButton from '../components/LogoutButton'

type Stats = {
  characters: number
  discussions: number
}

export default function Home() {
  const [stats, setStats] = useState<Stats>({ characters: 0, discussions: 0 })
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<ApiResult<{ items: unknown[] }>>('/characters'),
      api.get<ApiResult<{ items: unknown[] }>>('/discussions'),
    ])
      .then(([cRes, dRes]) => {
        setStats({
          characters: cRes.data.data.items?.length || 0,
          discussions: dRes.data.data.items?.length || 0,
        })
      })
      .catch(() => setError('加载统计失败'))
  }, [])

  return (
    <div className="page">
      <div className="row">
        <span>MADF</span>
        <Link to="/profile">个人中心</Link>
        <LogoutButton />
      </div>
      <h1>多智能体圆桌讨论</h1>
      {error && <p className="error">{error}</p>}

      <div className="row" style={{ gap: 16, marginTop: 24, justifyContent: 'center' }}>
        <div className="card" style={{ minWidth: 140, textAlign: 'center' }}>
          <h2>{stats.characters}</h2>
          <p>我的角色</p>
          <Link to="/characters">管理角色</Link>
        </div>
        <div className="card" style={{ minWidth: 140, textAlign: 'center' }}>
          <h2>{stats.discussions}</h2>
          <p>我的讨论</p>
          <Link to="/discussions">查看讨论</Link>
        </div>
      </div>

      <div className="row" style={{ marginTop: 32, justifyContent: 'center' }}>
        <Link to="/discussions/new">
          <button>新建讨论</button>
        </Link>
        <Link to="/generate" style={{ marginLeft: 12 }}>
          <button>AI 生成角色</button>
        </Link>
        <Link to="/gallery" style={{ marginLeft: 12 }}>
          <button>公开画廊</button>
        </Link>
      </div>
    </div>
  )
}
