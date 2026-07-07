import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import Markdown from '../components/Markdown'
import type { DocumentOut } from './UploadPage'

interface ReviewProblem {
  id: number
  statement_md: string
  parts: { prompt_md: string; answer_type: string; canonical: string; choices?: string[] }[]
  solution_md: string
  difficulty: number
  answer_verified: boolean
}

interface ReviewTopic {
  id: number
  title: string
  unit: string
  description: string
  est_minutes: number
  prereq_titles: string[]
  lesson_md: string | null
  worked_examples: { problem_md: string; solution_md: string }[]
  problems: ReviewProblem[]
}

interface ReviewOut {
  document: DocumentOut
  course_slug: string | null
  course_title: string | null
  topics: ReviewTopic[]
}

export default function DocumentReviewPage() {
  const { docId } = useParams()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [open, setOpen] = useState<number | null>(null)
  const [publishing, setPublishing] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['doc-review', docId],
    queryFn: () => api<ReviewOut>(`/api/documents/${docId}/review`),
  })

  if (isLoading || !data) return <p className="muted">Loading…</p>

  const removeTopic = async (topicId: number) => {
    await api(`/api/documents/${docId}/topics/${topicId}`, { method: 'DELETE' })
    queryClient.invalidateQueries({ queryKey: ['doc-review', docId] })
  }

  const removeProblem = async (problemId: number) => {
    await api(`/api/documents/${docId}/problems/${problemId}`, { method: 'DELETE' })
    queryClient.invalidateQueries({ queryKey: ['doc-review', docId] })
  }

  const publish = async () => {
    setPublishing(true)
    try {
      await api(`/api/documents/${docId}/publish`, { method: 'POST' })
      queryClient.invalidateQueries()
      if (data.course_slug) navigate(`/courses/${data.course_slug}`)
    } finally {
      setPublishing(false)
    }
  }

  const published = data.document.status === 'published'
  const units = [...new Set(data.topics.map((t) => t.unit))]

  return (
    <>
      <div className="page-kicker rise">
        <Link to="/upload">your books</Link> · {published ? 'published' : 'review'}
      </div>
      <h1 className="page-title rise rise-1">{data.course_title ?? data.document.title}</h1>
      <p className="page-sub rise rise-2">
        {data.topics.length} topics derived from {data.document.page_count} pages. Check
        the lessons and problems below — remove anything wrong or off-target, then publish.
        Problems that failed automatic answer verification are marked{' '}
        <span className="pill locked">unverified</span> and stay out of quizzes.
      </p>

      {!published && data.document.status === 'review' && (
        <div className="rise rise-2" style={{ marginBottom: 28 }}>
          <button className="btn" onClick={publish} disabled={publishing || data.topics.length === 0}>
            {publishing ? 'Publishing…' : `Publish course (${data.topics.length} topics) →`}
          </button>
        </div>
      )}

      {units.map((unit) => (
        <section className="unit rise rise-3" key={unit}>
          <div className="unit-head">
            <h2>{unit}</h2>
          </div>
          {data.topics
            .filter((t) => t.unit === unit)
            .map((t) => (
              <div key={t.id} style={{ borderBottom: '1px solid var(--rule)' }}>
                <div
                  className="topic-row"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setOpen(open === t.id ? null : t.id)}
                >
                  <span className="mono muted" style={{ fontSize: 11 }}>
                    {open === t.id ? '▾' : '▸'}
                  </span>
                  <div style={{ minWidth: 0 }}>
                    <div className="t-title">{t.title}</div>
                    <div className="t-desc">{t.description}</div>
                  </div>
                  <span className="t-min">
                    {t.problems.length} problems ·{' '}
                    {t.problems.filter((p) => p.answer_verified).length} verified
                  </span>
                  {!published && (
                    <button
                      className="btn secondary"
                      style={{ padding: '3px 10px', fontSize: 11 }}
                      onClick={(e) => {
                        e.stopPropagation()
                        removeTopic(t.id)
                      }}
                    >
                      remove
                    </button>
                  )}
                </div>
                {open === t.id && (
                  <div style={{ padding: '10px 6px 24px 30px' }}>
                    {t.prereq_titles.length > 0 && (
                      <p className="mono muted" style={{ fontSize: 12 }}>
                        requires: {t.prereq_titles.join(' · ')}
                      </p>
                    )}
                    {t.lesson_md && (
                      <div className="lesson-body" style={{ fontSize: 15.5 }}>
                        <Markdown>{t.lesson_md}</Markdown>
                      </div>
                    )}
                    {t.problems.map((p) => (
                      <div key={p.id} className="example-card">
                        <div className="ex-label" style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                          problem · difficulty {p.difficulty}
                          {p.answer_verified ? (
                            <span className="pill learned">verified</span>
                          ) : (
                            <span className="pill locked">unverified</span>
                          )}
                          {!published && (
                            <button
                              className="btn secondary"
                              style={{ padding: '2px 8px', fontSize: 10, marginLeft: 'auto' }}
                              onClick={() => removeProblem(p.id)}
                            >
                              remove
                            </button>
                          )}
                        </div>
                        <div className="ex-problem">
                          <Markdown>{p.statement_md}</Markdown>
                          {p.parts.map((part, i) => (
                            <div key={i} className="mono muted" style={{ fontSize: 12 }}>
                              {part.prompt_md} — <em>{part.answer_type}</em>, answer:{' '}
                              <code>{String(part.canonical)}</code>
                            </div>
                          ))}
                        </div>
                        {p.solution_md && (
                          <div className="ex-solution">
                            <Markdown>{p.solution_md}</Markdown>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
        </section>
      ))}
    </>
  )
}
