import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import type { AuthUser, MeOut } from '../api/types'

export default function LoginPage() {
  const queryClient = useQueryClient()
  const { data: me } = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => api<MeOut>('/api/auth/me'),
    retry: false,
  })
  const allowSignup = me?.allow_signup ?? false
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api<AuthUser>(`/api/auth/${mode}`, {
        method: 'POST',
        body: JSON.stringify({ username: username.trim(), password }),
      })
      // AuthGate re-checks /api/auth/me and swaps in the app.
      await queryClient.invalidateQueries({ queryKey: ['auth-me'] })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="wordmark" style={{ marginBottom: 4 }}>
          Educa<em>tor</em>
        </div>
        <div className="tagline" style={{ marginBottom: 22 }}>Adaptive learning</div>

        <h1 style={{ fontSize: 22, marginBottom: 4 }}>
          {mode === 'login' ? 'Welcome back' : 'Create your account'}
        </h1>
        <p className="muted" style={{ fontSize: 14, marginBottom: 20 }}>
          {mode === 'login'
            ? 'Log in to pick up where you left off.'
            : 'Your progress, courses, and reviews are yours alone.'}
        </p>

        <form onSubmit={submit}>
          <label className="auth-label">Username</label>
          <input
            className="answer-input auth-input"
            autoFocus
            autoComplete="username"
            value={username}
            maxLength={40}
            onChange={(e) => setUsername(e.target.value)}
          />
          <label className="auth-label">Password</label>
          <input
            className="answer-input auth-input"
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <div className="feedback-banner bad" style={{ marginTop: 14 }}>{error}</div>}

          <button
            className="btn"
            type="submit"
            disabled={busy || !username.trim() || !password}
            style={{ width: '100%', marginTop: 18 }}
          >
            {busy ? '…' : mode === 'login' ? 'Log in' : 'Sign up'}
          </button>
        </form>

        {allowSignup ? (
          <button
            type="button"
            className="auth-switch"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError(null)
            }}
          >
            {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Log in'}
          </button>
        ) : (
          <p className="muted" style={{ fontSize: 12.5, marginTop: 16, textAlign: 'center' }}>
            Sign-ups are closed — ask the owner to create an account for you.
          </p>
        )}
      </div>
    </div>
  )
}
