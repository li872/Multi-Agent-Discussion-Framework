import { useNavigate } from 'react-router-dom'

export default function LogoutButton() {
  const navigate = useNavigate()

  function onLogout() {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <button type="button" onClick={onLogout}>
      退出登录
    </button>
  )
}
