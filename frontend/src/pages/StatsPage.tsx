import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface StatsOut {
  total_xp: number
  xp_today: number
  daily_goal: number
  streak: number
  mastery_counts: Record<string, number>
  xp_by_day: { date: string; xp: number }[]
  attempts_total: number
  attempts_correct: number
}

export default function StatsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api<StatsOut>('/api/stats'),
    refetchOnMount: 'always',
  })

  if (isLoading || !data) return <p className="muted">Loading…</p>

  const max = Math.max(data.daily_goal, ...data.xp_by_day.map((d) => d.xp))
  const accuracy = data.attempts_total
    ? Math.round((100 * data.attempts_correct) / data.attempts_total)
    : null

  const m = data.mastery_counts

  return (
    <>
      <div className="page-kicker rise">Progress</div>
      <h1 className="page-title rise rise-1">Stats</h1>

      <div className="stat-grid rise rise-2">
        <div className="stat">
          <div className="n">{data.total_xp}</div>
          <div className="l">total XP</div>
        </div>
        <div className="stat">
          <div className="n">{data.streak}</div>
          <div className="l">day streak</div>
        </div>
        <div className="stat">
          <div className="n">{(m.learned ?? 0) + (m.mastered ?? 0)}</div>
          <div className="l">topics learned</div>
        </div>
        <div className="stat">
          <div className="n">{m.mastered ?? 0}</div>
          <div className="l">mastered</div>
        </div>
        <div className="stat">
          <div className="n">{accuracy === null ? '—' : `${accuracy}%`}</div>
          <div className="l">accuracy</div>
        </div>
      </div>

      <h3 className="rise rise-3" style={{ margin: '30px 0 12px' }}>
        Last 30 days
      </h3>
      <div className="xp-chart rise rise-3">
        {data.xp_by_day.map((d) => (
          <div key={d.date} className="col" title={`${d.date}: ${d.xp} XP`}>
            <div
              className={`bar ${d.xp >= data.daily_goal ? 'met' : ''}`}
              style={{ height: `${max ? Math.max(2, (100 * d.xp) / max) : 2}%` }}
            />
          </div>
        ))}
      </div>
      <div className="mono muted rise rise-3" style={{ fontSize: 11, marginTop: 6 }}>
        bars reaching the goal ({data.daily_goal} XP) turn gold
      </div>
    </>
  )
}
