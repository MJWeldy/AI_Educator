import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { LessonOut } from '../api/types'
import Markdown from '../components/Markdown'
import ProblemCard, { type PartResult, type ProblemPublic } from '../components/ProblemCard'

interface LearnState {
  topic_id: number
  topic_title: string
  course_slug: string
  mastery: string
  progress: { tier: number; streak: number; misses: number; done: number }
  lesson: LessonOut | null
  problem: ProblemPublic | null
}

interface AttemptOut {
  correct: boolean
  part_results: PartResult[]
  solution_md: string
  canonical: string[]
  events: { tier_advanced: boolean; lesson_complete: boolean; show_examples: boolean }
  progress: LearnState['progress']
  mastery: string
  xp_awarded: number
  next_problem: ProblemPublic | null
}

type Phase = 'reading' | 'practice' | 'complete'

export default function LearnPage() {
  const { topicId } = useParams()
  const queryClient = useQueryClient()
  const [state, setState] = useState<LearnState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('reading')
  const [problem, setProblem] = useState<ProblemPublic | null>(null)
  const [result, setResult] = useState<AttemptOut | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [showExamples, setShowExamples] = useState(false)
  const [xpEarned, setXpEarned] = useState(0)
  const [startedAt, setStartedAt] = useState(Date.now())
  const [generating, setGenerating] = useState(false)

  const generateLesson = async () => {
    setGenerating(true)
    try {
      const lesson = await api<LessonOut>(`/api/llm/topics/${topicId}/lesson`, { method: 'POST' })
      setState((s) => (s ? { ...s, lesson } : s))
      setPhase('reading')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setGenerating(false)
    }
  }

  useEffect(() => {
    api<LearnState>(`/api/learn/${topicId}`)
      .then((s) => {
        setState(s)
        setProblem(s.problem)
        // Skip straight to practice when already mid-lesson or there is no lesson text.
        if (s.progress.done > 0 || !s.lesson) setPhase('practice')
        if (s.mastery === 'learned' || s.mastery === 'mastered') setPhase('practice')
      })
      .catch((e) => setError(e.message))
  }, [topicId])

  if (error) return <p className="muted">{error}</p>
  if (!state) return <p className="muted">Loading…</p>

  const submit = async (answers: string[], hintsUsed: number) => {
    if (!problem) return
    setSubmitting(true)
    try {
      const out = await api<AttemptOut>(`/api/learn/${topicId}/attempt`, {
        method: 'POST',
        body: JSON.stringify({
          generator_key: problem.generator_key,
          seed: problem.seed,
          difficulty: problem.difficulty,
          answers,
          hints_used: hintsUsed,
          time_ms: Date.now() - startedAt,
        }),
      })
      setResult(out)
      setXpEarned((x) => x + out.xp_awarded)
      setState((s) => (s ? { ...s, progress: out.progress, mastery: out.mastery } : s))
      if (out.events.show_examples) setShowExamples(true)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const next = () => {
    if (result?.events.lesson_complete) {
      setPhase('complete')
      queryClient.invalidateQueries({ queryKey: ['courses'] })
      queryClient.invalidateQueries({ queryKey: ['course'] })
      return
    }
    setProblem(result?.next_problem ?? null)
    setResult(null)
    setShowExamples(false)
    setStartedAt(Date.now())
  }

  const tierPct = (tier: number) => {
    const p = state.progress
    if (p.tier > tier) return 100
    if (p.tier < tier) return 0
    return Math.min(100, (p.streak / 2) * 100)
  }

  return (
    <>
      <div className="page-kicker rise">
        <Link to={`/courses/${state.course_slug}`}>course</Link> ·{' '}
        <Link to={`/topics/${state.topic_id}`}>topic</Link>
      </div>
      <h1 className="page-title rise rise-1">{state.topic_title}</h1>

      {phase === 'reading' && state.lesson && (
        <div className="rise rise-2">
          <div className="lesson-body">
            <Markdown>{state.lesson.content_md}</Markdown>
          </div>
          {state.lesson.worked_examples.map((ex, i) => (
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
          <div style={{ marginTop: 26 }}>
            <button className="btn" onClick={() => setPhase('practice')}>
              Begin practice →
            </button>
          </div>
        </div>
      )}

      {phase === 'practice' && (
        <>
          {!state.lesson && state.progress.done === 0 && (
            <div className="feedback-banner hint rise" style={{ marginBottom: 18 }}>
              This topic has no written lesson yet.{' '}
              <button
                className="btn secondary"
                style={{ marginLeft: 10, padding: '4px 12px', fontSize: 12 }}
                onClick={generateLesson}
                disabled={generating}
              >
                {generating ? 'Writing… (can take a minute)' : 'Write one with AI'}
              </button>
            </div>
          )}
          <div className="tier-track rise rise-2">
            <span>warm-up</span>
            {[1, 2, 3].map((t) => (
              <div key={t} className={`tier ${state.progress.tier > t ? 'passed' : ''}`}>
                <div className="fill" style={{ width: `${tierPct(t)}%` }} />
              </div>
            ))}
            <span>mastery</span>
          </div>

          {showExamples && state.lesson && (
            <div className="rise" style={{ marginBottom: 20 }}>
              <div className="feedback-banner hint">
                Tough one — here's the worked example again.
              </div>
              {state.lesson.worked_examples.slice(0, 1).map((ex, i) => (
                <div key={i} className="example-card">
                  <div className="ex-label">Worked example</div>
                  <div className="ex-problem">
                    <Markdown>{ex.problem_md}</Markdown>
                  </div>
                  <div className="ex-solution">
                    <Markdown>{ex.solution_md}</Markdown>
                  </div>
                </div>
              ))}
            </div>
          )}

          {problem ? (
            <div className="rise rise-3" key={`${problem.generator_key}-${problem.seed}`}>
              <ProblemCard
                problem={problem}
                submitting={submitting}
                result={result}
                onSubmit={submit}
                onNext={next}
              />
            </div>
          ) : (
            <p className="muted rise rise-3">
              This topic has no practice problems yet — mark it done from the lesson for now.
            </p>
          )}
        </>
      )}

      {phase === 'complete' && (
        <div className="complete-card">
          <h2>Topic learned</h2>
          <p>
            <em>{state.topic_title}</em> joins your review rotation — it'll come back at
            just the right moment.
          </p>
          <div className="xp">+{xpEarned} XP</div>
          <div style={{ marginTop: 22 }}>
            <Link to={`/courses/${state.course_slug}`} className="btn">
              Back to course map
            </Link>
          </div>
        </div>
      )}
    </>
  )
}
