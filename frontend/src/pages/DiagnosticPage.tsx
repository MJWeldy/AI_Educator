import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { CourseSummary } from '../api/types'
import ProblemCard, { type PartResult, type ProblemPublic } from '../components/ProblemCard'

interface ProbeOut extends ProblemPublic {
  topic_id: number
  topic_title: string
}

interface SessionOut {
  session_id: number
  status: string
  asked_count: number
  max_questions: number
  probe: ProbeOut | null
}

interface FinishOut {
  placed_mastered: number
  questions_asked: number
}

export default function DiagnosticPage() {
  const queryClient = useQueryClient()
  const { data: courses } = useQuery({
    queryKey: ['courses'],
    queryFn: () => api<CourseSummary[]>('/api/courses'),
  })
  const [selected, setSelected] = useState<string[]>([])
  const [session, setSession] = useState<SessionOut | null>(null)
  const [result, setResult] = useState<{ correct: boolean; part_results: PartResult[]; solution_md: string } | null>(null)
  const [finish, setFinish] = useState<FinishOut | null>(null)
  const [busy, setBusy] = useState(false)

  const toggle = (slug: string) =>
    setSelected((s) => (s.includes(slug) ? s.filter((x) => x !== slug) : [...s, slug]))

  const start = async () => {
    setBusy(true)
    try {
      const s = await api<SessionOut>('/api/diagnostic/start', {
        method: 'POST',
        body: JSON.stringify({ course_slugs: selected }),
      })
      setSession(s)
    } finally {
      setBusy(false)
    }
  }

  const submit = async (answers: string[], _hintsUsed: number) => {
    if (!session?.probe) return
    setBusy(true)
    try {
      const out = await api<{ correct: boolean; part_results: PartResult[]; session: SessionOut }>(
        `/api/diagnostic/${session.session_id}/answer`,
        {
          method: 'POST',
          body: JSON.stringify({
            topic_id: session.probe.topic_id,
            generator_key: session.probe.generator_key,
            seed: session.probe.seed,
            difficulty: session.probe.difficulty,
            answers,
          }),
        },
      )
      // In a diagnostic we never reveal solutions — just move on.
      setSession(out.session)
      setResult(null)
      if (!out.session.probe) {
        const fin = await api<FinishOut>(`/api/diagnostic/${session.session_id}/finish`, {
          method: 'POST',
        })
        setFinish(fin)
        queryClient.invalidateQueries()
      }
    } finally {
      setBusy(false)
    }
  }

  if (finish) {
    return (
      <div className="complete-card" style={{ marginTop: 40 }}>
        <h2>Placement complete</h2>
        <p>
          After {finish.questions_asked} questions, {finish.placed_mastered} topics were
          marked as already known. They'll resurface as reviews over the next few weeks
          to confirm — your daily queue now starts right at your learning edge.
        </p>
        <div style={{ marginTop: 22 }}>
          <Link to="/" className="btn">
            Go to Today
          </Link>
        </div>
      </div>
    )
  }

  if (session?.probe) {
    return (
      <>
        <div className="page-kicker rise">Placement diagnostic</div>
        <h1 className="page-title rise rise-1">Where should you start?</h1>
        <div className="tier-track rise rise-2">
          <span className="mono">
            question {session.asked_count + 1} · max {session.max_questions}
          </span>
          <div className="tier">
            <div
              className="fill"
              style={{ width: `${(100 * session.asked_count) / session.max_questions}%` }}
            />
          </div>
        </div>
        <p className="muted rise rise-2" style={{ fontSize: 14 }}>
          Answer honestly — skipping ahead only muddles your placement. If you don't know
          it, give it your best guess and move on.
        </p>
        <div className="rise rise-3" key={`${session.probe.generator_key}-${session.probe.seed}`}>
          <ProblemCard
            problem={session.probe}
            submitting={busy}
            result={result}
            onSubmit={submit}
            onNext={() => {}}
            mode="diagnostic"
          />
        </div>
      </>
    )
  }

  return (
    <>
      <div className="page-kicker rise">Placement diagnostic</div>
      <h1 className="page-title rise rise-1">Skip what you already know</h1>
      <p className="page-sub rise rise-2">
        A short adaptive quiz (about 15–25 questions) finds your knowledge frontier.
        Topics you clearly know are marked mastered and gently re-verified over the
        coming weeks; everything else stays ahead of you to learn.
      </p>
      <div className="rise rise-3">
        <h3 style={{ marginBottom: 10 }}>Choose the courses to place into</h3>
        {courses?.map((c) => (
          <label key={c.slug} className="task-row" style={{ cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={selected.includes(c.slug)}
              onChange={() => toggle(c.slug)}
            />
            <span className="task-title">{c.title}</span>
            <span className="task-xp mono">{c.topic_count} topics</span>
          </label>
        ))}
        <div style={{ marginTop: 18 }}>
          <button className="btn" disabled={selected.length === 0 || busy} onClick={start}>
            {busy ? 'Starting…' : 'Start diagnostic →'}
          </button>
        </div>
      </div>
    </>
  )
}
