import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import '@fontsource-variable/fraunces/index.css'
import '@fontsource-variable/newsreader/index.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import './index.css'
import { api } from './api/client'
import type { MeOut } from './api/types'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import CoursesPage from './pages/CoursesPage'
import CourseMapPage from './pages/CourseMapPage'
import TopicPage from './pages/TopicPage'
import LearnPage from './pages/LearnPage'
import TodayPage from './pages/TodayPage'
import TaskPage from './pages/TaskPage'
import StatsPage from './pages/StatsPage'
import DiagnosticPage from './pages/DiagnosticPage'
import SettingsPage from './pages/SettingsPage'
import UploadPage from './pages/UploadPage'
import DocumentReviewPage from './pages/DocumentReviewPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <TodayPage /> },
      { path: '/task/:taskId', element: <TaskPage /> },
      { path: '/courses', element: <CoursesPage /> },
      { path: '/courses/:slug', element: <CourseMapPage /> },
      { path: '/topics/:topicId', element: <TopicPage /> },
      { path: '/learn/:topicId', element: <LearnPage /> },
      { path: '/upload', element: <UploadPage /> },
      { path: '/documents/:docId', element: <DocumentReviewPage /> },
      { path: '/stats', element: <StatsPage /> },
      { path: '/diagnostic', element: <DiagnosticPage /> },
      { path: '/settings', element: <SettingsPage /> },
    ],
  },
])

// Gate the whole app behind login when the server requires it. In local mode
// (require_auth false) this always falls straight through to the app.
function AuthGate() {
  const { data, isLoading } = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => api<MeOut>('/api/auth/me'),
    retry: false,
  })
  if (isLoading) return <div className="muted" style={{ padding: 40 }}>Loading…</div>
  if (data?.require_auth && !data.user) return <LoginPage />
  return <RouterProvider router={router} />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthGate />
    </QueryClientProvider>
  </StrictMode>,
)
