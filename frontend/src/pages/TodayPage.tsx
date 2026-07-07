import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

interface TaskOut {
  id: number
  type: 'lesson' | 'review' | 'quiz'
  status: string
  xp_value: number
  xp_awarded: number
  title: string
  topic_ids: number[]
  total_problems: number
  done_problems: number
}

interface TodayOut {
  date: string
  daily_goal: number
  xp_today: number
  streak: number
  tasks: TaskOut[]
}

const TYPE_LABEL = { lesson: 'Lesson', review: 'Review', quiz: 'Quiz' }

export default function TodayPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['today'],
    queryFn: () => api<TodayOut>('/api/tasks/today'),
    refetchOnMount: 'always',
  })
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api<{ attempts_total: number }>('/api/stats'),
  })

  if (isLoading || !data) return <p className="muted">Loading…</p>

  const brandNew = stats !== undefined && stats.attempts_total === 0

  const pct = Math.min(100, (100 * data.xp_today) / data.daily_goal)
  const goalMet = data.xp_today >= data.daily_goal

  return (
    <>
      <div className="page-kicker rise">
        {new Date(data.date + 'T00:00:00').toLocaleDateString(undefined, {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
        })}
      </div>
      <h1 className="page-title rise rise-1">Today</h1>

      {brandNew && (
        <div className="feedback-banner hint rise rise-1" style={{ marginBottom: 24 }}>
          New here? Take the <Link to="/diagnostic">placement diagnostic</Link> so the
          queue starts at your level instead of from scratch.
        </div>
      )}

      <div className="goal-bar rise rise-2">
        <div className="rail">
          <div className={`fill ${goalMet ? 'met' : ''}`} style={{ width: `${pct}%` }} />
        </div>
        <div className="numbers">
          <span className="mono">
            {data.xp_today} / {data.daily_goal} XP
          </span>
          {data.streak > 0 && <span className="streak">🔥 {data.streak}-day streak</span>}
          {goalMet && <span className="mono" style={{ color: 'var(--green)' }}>goal met ✓</span>}
        </div>
      </div>

      <div className="rise rise-3">
        {data.tasks.length === 0 && (
          <p className="muted">Nothing queued — visit a course and start any unlocked topic.</p>
        )}
        {data.tasks.map((t) => {
          const done = t.status === 'done'
          const to = t.type === 'lesson' ? `/learn/${t.topic_ids[0]}` : `/task/${t.id}`
          return (
            <Link key={t.id} to={to} className={`task-row ${done ? 'done' : ''}`}>
              <span className={`task-chip ${t.type}`}>{TYPE_LABEL[t.type]}</span>
              <span className="task-title">{t.title}</span>
              {t.total_problems > 0 && !done && (
                <span className="mono muted">
                  {t.done_problems}/{t.total_problems}
                </span>
              )}
              <span className="task-xp mono">{done ? `+${t.xp_awarded} ✓` : `${t.xp_value} XP`}</span>
            </Link>
          )
        })}
      </div>
    </>
  )
}
