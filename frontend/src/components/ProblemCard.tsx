import { useState } from 'react'
import Markdown from './Markdown'
import MathInput from './MathInput'

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
  result: { correct: boolean; part_results: PartResult[]; solution_md: string } | null
  onSubmit: (answers: string[]) => void
  onNext: () => void
}

export default function ProblemCard({ problem, submitting, result, onSubmit, onNext }: Props) {
  const [answers, setAnswers] = useState<string[]>(() => problem.parts.map(() => ''))

  const setAnswer = (i: number, v: string) => {
    setAnswers((prev) => prev.map((a, j) => (j === i ? v : a)))
  }

  const answered = result !== null
  const canSubmit = !submitting && !answered && answers.every((a) => a.trim() !== '')

  const submit = () => {
    if (canSubmit) onSubmit(answers)
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
          <button className="btn" onClick={onNext} autoFocus>
            Next problem →
          </button>
        </>
      ) : (
        <button className="btn" onClick={submit} disabled={!canSubmit}>
          {submitting ? 'Checking…' : 'Check answer'}
        </button>
      )}
    </div>
  )
}
