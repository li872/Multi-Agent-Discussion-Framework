import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './queryClient'
import Layout from './components/Layout'
import PageFallback from './components/PageFallback'

const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const Home = lazy(() => import('./pages/Home'))
const NewDiscussion = lazy(() => import('./pages/NewDiscussion'))
const DiscussionRoom = lazy(() => import('./pages/DiscussionRoom'))
const Characters = lazy(() => import('./pages/Characters'))
const Discussions = lazy(() => import('./pages/Discussions'))
const CharacterSkill = lazy(() => import('./pages/CharacterSkill'))
const Gallery = lazy(() => import('./pages/Gallery'))
const GenerateSkill = lazy(() => import('./pages/GenerateSkill'))
const Profile = lazy(() => import('./pages/Profile'))

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
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
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
