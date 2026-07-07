import { useState } from 'react'
import Markdown from './Markdown'
import MathInput from './MathInput'
import { streamText } from '../api/stream'

export interface ProblemPartPublic {
  prompt_md: string
  answer_type: string
  choices: string[] | null
}

export interface ProblemPublic {
  generator_key: string
  seed: number
  difficulty: number
  statement_md: string
  parts: ProblemPartPublic[]
}

export interface PartResult {
  correct: boolean
  feedback: string | null
}

interface Props {
  problem: ProblemPublic
  submitting: boolean
  result: {
    correct: boolean
    part_results: PartResult[]
    solution_md: string
    canonical?: string[]
  } | null
  onSubmit: (answers: string[], hintsUsed: number) => void
  onNext: () => void
  mode?: 'practice' | 'diagnostic'
}

export default function ProblemCard({ problem, submitting, result, onSubmit, onNext, mode = 'practice' }: Props) {
  const [answers, setAnswers] = useState<string[]>(() => problem.parts.map(() => ''))
  const [hintText, setHintText] = useState('')
  const [hintBusy, setHintBusy] = useState(false)
  const [hintsUsed, setHintsUsed] = useState(0)
  const [explainText, setExplainText] = useState('')
  const [explainBusy, setExplainBusy] = useState(false)

  const setAnswer = (i: number, v: string) => {
    setAnswers((prev) => prev.map((a, j) => (j === i ? v : a)))
  }

  const answered = result !== null
  const canSubmit = !submitting && !answered && answers.every((a) => a.trim() !== '')

  const submit = () => {
    if (canSubmit) onSubmit(answers, hintsUsed)
  }

  const getHint = async () => {
    setHintBusy(true)
    setHintText('')
    setHintsUsed((h) => h + 1)
    try {
      await streamText(
        '/api/llm/hint',
        {
          statement_md: problem.statement_md,
          parts: problem.parts,
          wrong_answers: answers.some((a) => a.trim()) ? answers : null,
        },
        (chunk) => setHintText((t) => t + chunk),
      )
    } catch {
      setHintText('Hint unavailable — is Ollama running?')
    } finally {
      setHintBusy(false)
    }
  }

  const getExplanation = async () => {
    if (!result?.canonical) return
    setExplainBusy(true)
    setExplainText('')
    try {
      await streamText(
        '/api/llm/explain',
        {
          statement_md: problem.statement_md,
          parts: problem.parts,
          user_answers: answers,
          canonical: result.canonical,
        },
        (chunk) => setExplainText((t) => t + chunk),
      )
    } catch {
      setExplainText('Explanation unavailable — is Ollama running?')
    } finally {
      setExplainBusy(false)
    }
  }

  return (
    <div className="problem-card">
      <div className="statement">
        <Markdown>{problem.statement_md}</Markdown>
      </div>

      {problem.parts.map((part, i) => {
        const partStatus = answered ? (result.part_results[i]?.correct ? 'correct' : 'incorrect') : null
        return (
          <div className="part-block" key={i}>
            {part.prompt_md && (
              <div className="prompt">
                <Markdown>{part.prompt_md}</Markdown>
              </div>
            )}
            {part.answer_type === 'multiple_choice' && part.choices ? (
              <div className="choices">
                {part.choices.map((choice, ci) => {
                  const selected = answers[i] === String(ci)
                  let cls = 'choice'
                  if (answered && selected) cls += partStatus === 'correct' ? ' correct' : ' incorrect'
                  else if (selected) cls += ' selected'
                  return (
                    <button
                      key={ci}
                      type="button"
                      className={cls}
                      disabled={answered}
                      onClick={() => setAnswer(i, String(ci))}
                    >
                      <Markdown>{choice}</Markdown>
                    </button>
                  )
                })}
              </div>
            ) : (
              <MathInput
                value={answers[i]}
                onChange={(v) => setAnswer(i, v)}
                answerType={part.answer_type}
                disabled={answered}
                status={partStatus}
                onEnter={submit}
              />
            )}
            {answered && result.part_results[i]?.feedback && (
              <div className="feedback-banner hint">{result.part_results[i].feedback}</div>
            )}
          </div>
        )
      })}

      {hintText && (
        <div className="solution-reveal" style={{ borderLeftColor: 'var(--blue)', background: 'rgba(46,93,116,0.06)' }}>
          <div className="lbl" style={{ color: 'var(--blue)' }}>Hint</div>
          <Markdown>{hintText}</Markdown>
        </div>
      )}

      {answered ? (
        <>
          <div className={`feedback-banner ${result.correct ? 'good' : 'bad'}`}>
            {result.correct ? '✓ Correct' : '✗ Not quite'}
          </div>
          {!result.correct && result.solution_md && (
            <div className="solution-reveal">
              <div className="lbl">Solution</div>
              <Markdown>{result.solution_md}</Markdown>
            </div>
          )}
          {explainText && (
            <div className="solution-reveal" style={{ borderLeftColor: 'var(--blue)', background: 'rgba(46,93,116,0.06)' }}>
              <div className="lbl" style={{ color: 'var(--blue)' }}>Tutor</div>
              <Markdown>{explainText}</Markdown>
            </div>
          )}
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn" onClick={onNext} autoFocus>
              Next problem →
            </button>
            {!result.correct && mode === 'practice' && result.canonical && !explainText && (
              <button className="btn secondary" onClick={getExplanation} disabled={explainBusy}>
                {explainBusy ? 'Thinking…' : 'Explain my mistake'}
              </button>
            )}
          </div>
        </>
      ) : (
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn" onClick={submit} disabled={!canSubmit}>
            {submitting ? 'Checking…' : 'Check answer'}
          </button>
          {mode === 'practice' && (
            <button className="btn secondary" onClick={getHint} disabled={hintBusy}>
              {hintBusy ? 'Thinking…' : hintText ? 'Another hint' : 'Get a hint'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
