import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

type Stats = {
  characters: number
  discussions: number
}

export default function Home() {
  const stats = useQuery({
    queryKey: ['home-stats'],
    queryFn: async (): Promise<Stats> => {
      const [cRes, dRes] = await Promise.all([
        api.get<ApiResult<{ items: unknown[] }>>('/characters'),
        api.get<ApiResult<{ items: unknown[] }>>('/discussions'),
      ])
      return {
        characters: cRes.data.data.items?.length || 0,
        discussions: dRes.data.data.items?.length || 0,
      }
    },
  })

  return (
    <div className="page">
      <h1>多智能体圆桌讨论</h1>
      {stats.isError && <p className="error">加载统计失败</p>}

      <div className="row" style={{ gap: 16, marginTop: 24, justifyContent: 'center' }}>
        <div className="card" style={{ minWidth: 140, textAlign: 'center' }}>
          <h2>{stats.data ? stats.data.characters : '…'}</h2>
          <p>我的角色</p>
          <Link to="/characters">管理角色</Link>
        </div>
        <div className="card" style={{ minWidth: 140, textAlign: 'center' }}>
          <h2>{stats.data ? stats.data.discussions : '…'}</h2>
          <p>我的讨论</p>
          <Link to="/discussions">查看讨论</Link>
        </div>
      </div>

      <div className="row" style={{ marginTop: 32, justifyContent: 'center' }}>
        <Link to="/discussions/new">
          <button type="button">新建讨论</button>
        </Link>
        <Link to="/generate" style={{ marginLeft: 12 }}>
          <button type="button">AI 生成角色</button>
        </Link>
        <Link to="/gallery" style={{ marginLeft: 12 }}>
          <button type="button">公开画廊</button>
        </Link>
      </div>
    </div>
  )
}
