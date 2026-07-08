import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
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
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { data: course, isLoading } = useQuery({
    queryKey: ['course', slug],
    queryFn: () => api<CourseDetail>(`/api/courses/${slug}`),
  })

  const renameCourse = async () => {
    if (!course) return
    const title = window.prompt('New course name:', course.title)
    if (!title || title.trim() === '' || title === course.title) return
    await api(`/api/courses/${course.slug}`, {
      method: 'PATCH',
      body: JSON.stringify({ title: title.trim() }),
    })
    queryClient.invalidateQueries()
  }

  const deleteCourse = async () => {
    if (!course?.document_id) return
    if (
      !window.confirm(
        `Delete “${course.title}”?\n\nThis removes the uploaded book, this course and its topics, and any progress on them. This cannot be undone.`,
      )
    )
      return
    await api(`/api/documents/${course.document_id}`, { method: 'DELETE' })
    queryClient.invalidateQueries()
    navigate('/courses')
  }

  if (isLoading) return <p className="muted">Loading…</p>
  if (!course) return <p className="muted">Course not found.</p>

  return (
    <>
      <div className="page-kicker rise">Course{course.level ? ` · ${course.level}` : ''}</div>
      <h1 className="page-title rise rise-1">{course.title}</h1>
      <p className="page-sub rise rise-2">{course.description}</p>
      {course.document_id != null && (
        <div className="rise rise-2" style={{ margin: '-16px 0 26px', display: 'flex', gap: 10 }}>
          <button className="btn secondary" style={{ padding: '6px 14px', fontSize: 12 }} onClick={renameCourse}>
            Rename
          </button>
          <button className="btn secondary danger" style={{ padding: '6px 14px', fontSize: 12 }} onClick={deleteCourse}>
            Delete this course
          </button>
        </div>
      )}

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
