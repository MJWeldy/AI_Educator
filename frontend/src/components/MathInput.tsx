import { useEffect, useRef, useState } from 'react'
import katex from 'katex'

interface Props {
  value: string
  onChange: (v: string) => void
  answerType: string
  disabled?: boolean
  status?: 'correct' | 'incorrect' | null
  onEnter?: () => void
}

/** Text input for math answers with a live "we read this as" KaTeX preview. */
export default function MathInput({ value, onChange, answerType, disabled, status, onEnter }: Props) {
  const [preview, setPreview] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout>>(null)

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    if (!value.trim()) {
      setPreview(null)
      return
    }
    if (answerType === 'expression') {
      timer.current = setTimeout(async () => {
        try {
          const res = await fetch(`/api/learn/preview/expression?expr=${encodeURIComponent(value)}`)
          const body = await res.json()
          setPreview(body.ok ? body.latex : null)
        } catch {
          setPreview(null)
        }
      }, 350)
    } else {
      // numeric / fraction: cheap local rendering
      const m = value.trim().match(/^(-?)(\d+)\s*\/\s*(\d+)$/)
      if (m) setPreview(`${m[1]}\\dfrac{${m[2]}}{${m[3]}}`)
      else if (/^-?[\d.,]+$/.test(value.trim())) setPreview(value.trim().replace(/,/g, '{,}'))
      else setPreview(null)
    }
  }, [value, answerType])

  const placeholder =
    answerType === 'expression' ? 'e.g. 7x + 2 or 3/4 x' : 'e.g. 42, -1.5, or 3/4'

  return (
    <div>
      <input
        className={`answer-input ${status ?? ''}`}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && onEnter) onEnter()
        }}
        autoComplete="off"
        spellCheck={false}
      />
      <div className="input-preview">
        {preview && (
          <>
            <span className="lbl">reads as</span>
            <span
              dangerouslySetInnerHTML={{
                __html: katex.renderToString(preview, { throwOnError: false }),
              }}
            />
          </>
        )}
      </div>
    </div>
  )
}
