import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { TopicDetail } from '../api/types'
import Markdown from '../components/Markdown'

export default function TopicPage() {
  const { topicId } = useParams()
  const { data: topic, isLoading } = useQuery({
    queryKey: ['topic', topicId],
    queryFn: () => api<TopicDetail>(`/api/topics/${topicId}`),
  })

  if (isLoading) return <p className="muted">Loading…</p>
  if (!topic) return <p className="muted">Topic not found.</p>

  const unmetPrereqs = topic.prereqs.filter(
    (p) => p.mastery !== 'learned' && p.mastery !== 'mastered',
  )

  return (
    <>
      <div className="page-kicker rise">
        <Link to={`/courses/${topic.course_slug}`}>{topic.course_title}</Link> · {topic.unit}
      </div>
      <h1 className="page-title rise rise-1">{topic.title}</h1>
      <p className="page-sub rise rise-2" style={{ marginBottom: 18 }}>
        {topic.description}
      </p>
      <div className="rise rise-2" style={{ marginBottom: 30 }}>
        <span className={`pill ${topic.mastery}`}>{topic.mastery}</span>
      </div>

      {topic.mastery === 'locked' && (
        <section className="rise rise-3" style={{ marginBottom: 30 }}>
          <h3>Not yet unlocked</h3>
          <p className="muted">Finish these prerequisites first:</p>
          <ul>
            {unmetPrereqs.map((p) => (
              <li key={p.id}>
                <Link to={`/topics/${p.id}`}>{p.title}</Link>{' '}
                <span className={`pill ${p.mastery}`}>{p.mastery}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {topic.mastery !== 'locked' && (
        <div className="rise rise-3" style={{ marginBottom: 34 }}>
          <Link to={`/learn/${topic.id}`} className="btn">
            {topic.mastery === 'learning' ? 'Continue lesson →' : 'Start lesson →'}
          </Link>
        </div>
      )}

      {topic.lesson && (
        <section className="rise rise-4">
          <div className="lesson-body">
            <Markdown>{topic.lesson.content_md}</Markdown>
          </div>
          {topic.lesson.worked_examples.map((ex, i) => (
            <div key={i} className="example-card">
              <div className="ex-label">Worked example {i + 1}</div>
              <div className="ex-problem">
                <Markdown>{ex.problem_md}</Markdown>
              </div>
              <div className="ex-solution">
                <Markdown>{ex.solution_md}</Markdown>
              </div>
            </div>
          ))}
        </section>
      )}

      {topic.resources.length > 0 && (
        <section className="rise rise-4" style={{ marginTop: 34 }}>
          <h3>Further material</h3>
          <ul className="resource-list">
            {topic.resources.map((r) => (
              <li key={r.url}>
                <span className="kind">{r.kind}</span>
                <a href={r.url} target="_blank" rel="noreferrer">
                  {r.title}
                </a>
                {r.note && <span className="muted"> — {r.note}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}
