import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

interface LLMStatus {
  ollama_available: boolean
  ollama_models: string[]
  anthropic_key_set: boolean
}

interface SettingsOut {
  daily_xp_goal: number
  default_provider: string
  ollama_model: string
  anthropic_key_set: boolean
  anthropic_model: string | null
  use_claude_for_ingestion: boolean
}

const CLAUDE_MODELS = ['claude-opus-4-8', 'claude-sonnet-4-6', 'claude-haiku-4-5']

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const { data: status } = useQuery({
    queryKey: ['llm-status'],
    queryFn: () => api<LLMStatus>('/api/llm/status'),
  })
  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api<SettingsOut>('/api/settings'),
  })

  const [goal, setGoal] = useState(30)
  const [ollamaModel, setOllamaModel] = useState('gpt-oss:20b')
  const [apiKey, setApiKey] = useState('')
  const [claudeModel, setClaudeModel] = useState('claude-sonnet-4-6')
  const [useClaudeIngest, setUseClaudeIngest] = useState(false)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (settings) {
      setGoal(settings.daily_xp_goal)
      setOllamaModel(settings.ollama_model)
      setClaudeModel(settings.anthropic_model ?? 'claude-sonnet-4-6')
      setUseClaudeIngest(settings.use_claude_for_ingestion)
    }
  }, [settings])

  const save = async () => {
    setBusy(true)
    setSaved(false)
    try {
      await api<SettingsOut>('/api/settings', {
        method: 'PUT',
        body: JSON.stringify({
          daily_xp_goal: goal,
          ollama_model: ollamaModel,
          anthropic_api_key: apiKey || undefined,
          anthropic_model: claudeModel,
          use_claude_for_ingestion: useClaudeIngest,
        }),
      })
      setApiKey('')
      setSaved(true)
      queryClient.invalidateQueries()
    } finally {
      setBusy(false)
    }
  }

  if (!settings) return <p className="muted">Loading…</p>

  return (
    <>
      <div className="page-kicker rise">Preferences</div>
      <h1 className="page-title rise rise-1">Settings</h1>

      <section className="rise rise-2" style={{ maxWidth: 560 }}>
        <h3 style={{ marginBottom: 12 }}>Daily goal</h3>
        <label className="mono" style={{ fontSize: 13 }}>
          XP per day (≈ minutes of focused work){' '}
          <input
            className="answer-input"
            style={{ width: 90, marginLeft: 10 }}
            type="number"
            min={5}
            max={240}
            value={goal}
            onChange={(e) => setGoal(Number(e.target.value))}
          />
        </label>

        <h3 style={{ margin: '34px 0 12px' }}>Local AI (Ollama)</h3>
        <p className="muted" style={{ fontSize: 14, marginTop: 0 }}>
          Free and private — powers hints, explanations, and generated lessons by default.
          {status && !status.ollama_available && (
            <strong style={{ color: 'var(--accent)' }}> Ollama isn't reachable right now.</strong>
          )}
        </p>
        <select
          className="answer-input"
          style={{ width: 300 }}
          value={ollamaModel}
          onChange={(e) => setOllamaModel(e.target.value)}
        >
          {(status?.ollama_models ?? [ollamaModel]).map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

        <h3 style={{ margin: '34px 0 12px' }}>Claude API (optional)</h3>
        <p className="muted" style={{ fontSize: 14, marginTop: 0 }}>
          Pay-per-use. Recommended for turning textbook PDFs into courses, where quality
          matters most. Your key is stored locally in the app database.
        </p>
        <input
          className="answer-input"
          style={{ width: '100%' }}
          type="password"
          placeholder={settings.anthropic_key_set ? 'key saved — paste to replace' : 'sk-ant-…'}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <div style={{ marginTop: 12 }}>
          <select
            className="answer-input"
            style={{ width: 300 }}
            value={claudeModel}
            onChange={(e) => setClaudeModel(e.target.value)}
          >
            {CLAUDE_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
        <label style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 14, fontSize: 15 }}>
          <input
            type="checkbox"
            checked={useClaudeIngest}
            onChange={(e) => setUseClaudeIngest(e.target.checked)}
            disabled={!settings.anthropic_key_set && !apiKey}
          />
          Use Claude for textbook ingestion and lesson writing
        </label>

        <div style={{ marginTop: 30, display: 'flex', gap: 14, alignItems: 'center' }}>
          <button className="btn" onClick={save} disabled={busy}>
            {busy ? 'Saving…' : 'Save settings'}
          </button>
          {saved && <span className="mono" style={{ color: 'var(--green)', fontSize: 13 }}>saved ✓</span>}
        </div>
      </section>
    </>
  )
}
