import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import ProblemCard, { type PartResult, type ProblemPublic } from '../components/ProblemCard'

interface TaskProblem extends ProblemPublic {
  index: number
  topic_id: number
  topic_title: string
  done: boolean
  correct: boolean | null
}

interface TaskDetail {
  id: number
  type: string
  status: string
  xp_value: number
  problems: TaskProblem[]
}

interface TaskAttemptOut {
  correct: boolean
  part_results: PartResult[]
  solution_md: string
  task_status: string
  task_complete: boolean
  xp_awarded: number
  next_index: number | null
}

export default function TaskPage() {
  const { taskId } = useParams()
  const queryClient = useQueryClient()
  const [task, setTask] = useState<TaskDetail | null>(null)
  const [index, setIndex] = useState<number | null>(null)
  const [result, setResult] = useState<TaskAttemptOut | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [correctCount, setCorrectCount] = useState(0)
  const [startedAt, setStartedAt] = useState(Date.now())

  useEffect(() => {
    api<TaskDetail>(`/api/tasks/${taskId}`)
      .then((t) => {
        setTask(t)
        setCorrectCount(t.problems.filter((p) => p.done && p.correct).length)
        const first = t.problems.find((p) => !p.done)
        setIndex(first ? first.index : null)
      })
      .catch((e) => setError(e.message))
  }, [taskId])

  if (error) return <p className="muted">{error}</p>
  if (!task) return <p className="muted">Loading…</p>

  const current = index === null ? null : task.problems[index]
  const finished = task.status === 'done' || index === null

  const submit = async (answers: string[]) => {
    if (!current) return
    setSubmitting(true)
    try {
      const out = await api<TaskAttemptOut>(`/api/tasks/${task.id}/attempt`, {
        method: 'POST',
        body: JSON.stringify({ index: current.index, answers, time_ms: Date.now() - startedAt }),
      })
      setResult(out)
      if (out.correct) setCorrectCount((c) => c + 1)
      setTask((t) => (t ? { ...t, status: out.task_status } : t))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const next = () => {
    const n = result?.next_index ?? null
    setIndex(n)
    setResult(null)
    setStartedAt(Date.now())
    if (n === null) {
      queryClient.invalidateQueries({ queryKey: ['today'] })
    }
  }

  const doneCount = task.problems.filter((p) => p.done).length + (result && current && !current.done ? 1 : 0)

  return (
    <>
      <div className="page-kicker rise">
        <Link to="/">today</Link> · {task.type}
      </div>
      <h1 className="page-title rise rise-1">
        {task.type === 'quiz' ? 'Quiz' : 'Review'}
      </h1>
      <div className="tier-track rise rise-2">
        <span className="mono">
          {Math.min(doneCount, task.problems.length)} / {task.problems.length}
        </span>
        <div className="tier">
          <div
            className="fill"
            style={{ width: `${(100 * doneCount) / task.problems.length}%` }}
          />
        </div>
      </div>

      {finished && !current ? (
        <div className="complete-card">
          <h2>{task.type === 'quiz' ? 'Quiz complete' : 'Review complete'}</h2>
          <p>
            {correctCount} of {task.problems.length} correct.
          </p>
          {result && result.xp_awarded > 0 && <div className="xp">+{result.xp_awarded} XP</div>}
          <div style={{ marginTop: 22 }}>
            <Link to="/" className="btn">
              Back to Today
            </Link>
          </div>
        </div>
      ) : current ? (
        <div className="rise rise-3" key={current.index}>
          <p className="muted" style={{ margin: '0 0 8px' }}>
            <span className="mono" style={{ fontSize: 12 }}>
              topic · {current.topic_title}
            </span>
          </p>
          <ProblemCard
            problem={current}
            submitting={submitting}
            result={result}
            onSubmit={submit}
            onNext={next}
          />
        </div>
      ) : null}
    </>
  )
}
