import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import '@fontsource-variable/fraunces/index.css'
import '@fontsource-variable/newsreader/index.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import './index.css'
import Layout from './components/Layout'
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

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
