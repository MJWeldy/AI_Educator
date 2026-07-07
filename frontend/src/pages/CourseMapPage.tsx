import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { CourseDetail } from '../api/types'

const LEGEND: [string, string][] = [
  ['locked', 'locked'],
  ['unlocked', 'ready'],
  ['learning', 'in progress'],
  ['learned', 'learned'],
  ['mastered', 'mastered'],
]

export default function CourseMapPage() {
  const { slug } = useParams()
  const { data: course, isLoading } = useQuery({
    queryKey: ['course', slug],
    queryFn: () => api<CourseDetail>(`/api/courses/${slug}`),
  })

  if (isLoading) return <p className="muted">Loading…</p>
  if (!course) return <p className="muted">Course not found.</p>

  return (
    <>
      <div className="page-kicker rise">Course{course.level ? ` · ${course.level}` : ''}</div>
      <h1 className="page-title rise rise-1">{course.title}</h1>
      <p className="page-sub rise rise-2">{course.description}</p>

      <div className="legend rise rise-3">
        {LEGEND.map(([k, label]) => (
          <span key={k}>
            <i className={`mark ${k}`} /> {label}
          </span>
        ))}
      </div>

      {course.units.map((unit, ui) => (
        <section key={unit.title} className="unit rise rise-4">
          <div className="unit-head">
            <span className="n">{String(ui + 1).padStart(2, '0')}</span>
            <h2>{unit.title}</h2>
          </div>
          {unit.topics.map((t) => (
            <Link
              key={t.id}
              to={`/topics/${t.id}`}
              className={`topic-row ${t.mastery === 'locked' ? 'locked' : ''}`}
            >
              <i className={`mark ${t.mastery}`} />
              <div style={{ minWidth: 0 }}>
                <div className="t-title">{t.title}</div>
                {t.description && <div className="t-desc">{t.description}</div>}
              </div>
              <span className="t-min">{t.est_minutes} min</span>
            </Link>
          ))}
        </section>
      ))}
    </>
  )
}
