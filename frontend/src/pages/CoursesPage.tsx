import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { CourseSummary } from '../api/types'

export default function CoursesPage() {
  const { data: courses, isLoading } = useQuery({
    queryKey: ['courses'],
    queryFn: () => api<CourseSummary[]>('/api/courses'),
  })

  return (
    <>
      <div className="page-kicker rise">Curriculum</div>
      <h1 className="page-title rise rise-1">Courses</h1>
      <p className="page-sub rise rise-2">
        Every course is a prerequisite graph of topics. Learn on the frontier, and
        what you've learned comes back for review at exactly the right time.
      </p>
      {isLoading && <p className="muted">Loading…</p>}
      {courses?.map((c, i) => {
        const learnedPct = c.topic_count ? (100 * c.learned_count) / c.topic_count : 0
        const masteredPct = c.topic_count ? (100 * c.mastered_count) / c.topic_count : 0
        return (
          <Link
            key={c.slug}
            to={`/courses/${c.slug}`}
            className={`course-card rise rise-${Math.min(i + 2, 4)}`}
          >
            <h2>
              {c.title}
              {c.level && <span className="level-chip">{c.level}</span>}
            </h2>
            <p>{c.description}</p>
            <div className="progress-rail">
              <div className="learned" style={{ width: `${learnedPct}%` }} />
              <div className="mastered" style={{ width: `${masteredPct}%` }} />
            </div>
            <div className="course-meta">
              <span>{c.topic_count} topics</span>
              <span>{c.learned_count} learned</span>
              <span>{c.mastered_count} mastered</span>
              {c.source === 'document' && <span>from your upload</span>}
            </div>
          </Link>
        )
      })}
    </>
  )
}
