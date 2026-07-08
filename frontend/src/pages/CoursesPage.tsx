import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { CourseSummary } from '../api/types'

function CourseCard({ c, delay }: { c: CourseSummary; delay: number }) {
  const learnedPct = c.topic_count ? (100 * c.learned_count) / c.topic_count : 0
  const masteredPct = c.topic_count ? (100 * c.mastered_count) / c.topic_count : 0
  return (
    <Link to={`/courses/${c.slug}`} className={`course-card rise rise-${Math.min(delay, 4)}`}>
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
      </div>
    </Link>
  )
}

export default function CoursesPage() {
  const { data: courses, isLoading } = useQuery({
    queryKey: ['courses'],
    queryFn: () => api<CourseSummary[]>('/api/courses'),
  })

  const builtIn = (courses ?? []).filter((c) => c.source !== 'document')
  const uploads = (courses ?? []).filter((c) => c.source === 'document')

  return (
    <>
      <div className="page-kicker rise">Curriculum</div>
      <h1 className="page-title rise rise-1">Courses</h1>
      <p className="page-sub rise rise-2">
        Every course is a prerequisite graph of topics. Learn on the frontier, and what
        you've learned comes back for review at exactly the right time.
      </p>
      {isLoading && <p className="muted">Loading…</p>}

      {uploads.length > 0 && (
        <>
          <div className="section-head rise rise-2">
            <h2>Your uploads</h2>
            <span className="mono muted">
              from books and papers you added · <Link to="/upload">add another</Link>
            </span>
          </div>
          {uploads.map((c, i) => (
            <CourseCard key={c.slug} c={c} delay={i + 2} />
          ))}
          <div className="section-head rise rise-3" style={{ marginTop: 34 }}>
            <h2>Built-in curriculum</h2>
            <span className="mono muted">Early Math through Mathematics for ML</span>
          </div>
        </>
      )}

      {builtIn.map((c, i) => (
        <CourseCard key={c.slug} c={c} delay={i + 2} />
      ))}
    </>
  )
}
