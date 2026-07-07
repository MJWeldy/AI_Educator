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
import Placeholder from './pages/Placeholder'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      {
        path: '/',
        element: (
          <Placeholder
            title="Today"
            note="Your daily task queue — new lessons, due reviews, and quizzes — arrives in Phase 3."
          />
        ),
      },
      { path: '/courses', element: <CoursesPage /> },
      { path: '/courses/:slug', element: <CourseMapPage /> },
      { path: '/topics/:topicId', element: <TopicPage /> },
      { path: '/learn/:topicId', element: <LearnPage /> },
      {
        path: '/upload',
        element: (
          <Placeholder
            title="Upload a book"
            note="Turn any textbook PDF into a course the app can teach. Arrives in Phase 6."
          />
        ),
      },
      {
        path: '/stats',
        element: (
          <Placeholder title="Stats" note="XP history, streaks, and mastery over time. Arrives in Phase 3." />
        ),
      },
      {
        path: '/settings',
        element: (
          <Placeholder
            title="Settings"
            note="AI providers (Ollama / Claude), daily goal, and preferences. Arrives in Phase 5."
          />
        ),
      },
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
