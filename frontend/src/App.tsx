import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Home from './pages/Home'
import NewDiscussion from './pages/NewDiscussion'
import DiscussionRoom from './pages/DiscussionRoom'
import Characters from './pages/Characters'
import Discussions from './pages/Discussions'
import CharacterSkill from './pages/CharacterSkill'
import Gallery from './pages/Gallery'
import GenerateSkill from './pages/GenerateSkill'
import Profile from './pages/Profile'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        {/* 需登录的业务页统一走 Layout（导航 + 鉴权） */}
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/discussions/new" element={<NewDiscussion />} />
          <Route path="/discussions/:id" element={<DiscussionRoom />} />
          <Route path="/discussions" element={<Discussions />} />
          <Route path="/characters/:id/skill" element={<CharacterSkill />} />
          <Route path="/characters" element={<Characters />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/generate" element={<GenerateSkill />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
