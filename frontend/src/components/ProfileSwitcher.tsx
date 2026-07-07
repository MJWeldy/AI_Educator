import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

interface ProfileOut {
  id: number
  name: string
  total_xp: number
}

interface ProfilesOut {
  current_id: number
  profiles: ProfileOut[]
}

export default function ProfileSwitcher() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [busy, setBusy] = useState(false)

  const { data } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => api<ProfilesOut>('/api/profiles'),
  })

  if (!data) return null
  const current = data.profiles.find((p) => p.id === data.current_id)

  const select = async (id: number) => {
    if (id === data.current_id) {
      setOpen(false)
      return
    }
    setBusy(true)
    try {
      await api(`/api/profiles/${id}/select`, { method: 'POST' })
      setOpen(false)
      queryClient.invalidateQueries() // every view is per-profile
    } finally {
      setBusy(false)
    }
  }

  const create = async () => {
    const name = newName.trim()
    if (!name) return
    setBusy(true)
    try {
      const p = await api<ProfileOut>('/api/profiles', {
        method: 'POST',
        body: JSON.stringify({ name }),
      })
      setNewName('')
      await select(p.id)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="profile-switcher">
      {open && (
        <div className="profile-panel">
          {data.profiles.map((p) => (
            <button
              key={p.id}
              className={`profile-item ${p.id === data.current_id ? 'active' : ''}`}
              disabled={busy}
              onClick={() => select(p.id)}
            >
              <span>{p.name}</span>
              <span className="xp">{p.total_xp} XP</span>
            </button>
          ))}
          <div className="profile-new">
            <input
              className="answer-input"
              style={{ width: '100%', fontSize: 13, padding: '6px 10px' }}
              placeholder="new learner…"
              value={newName}
              maxLength={40}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && create()}
            />
          </div>
        </div>
      )}
      <button className="profile-current" onClick={() => setOpen(!open)}>
        <span className="dot" />
        {current?.name ?? 'Learner'}
        <span className="chev">{open ? '▾' : '▸'}</span>
      </button>
    </div>
  )
}
