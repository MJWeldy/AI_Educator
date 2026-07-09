import { NavLink, Outlet } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MeOut } from '../api/types'
import ProfileSwitcher from './ProfileSwitcher'

const links = [
  { to: '/', label: 'Today' },
  { to: '/courses', label: 'Courses' },
  { to: '/upload', label: 'Upload a book' },
  { to: '/stats', label: 'Stats' },
  { to: '/settings', label: 'Settings' },
]

function AccountMenu({ name }: { name: string }) {
  const queryClient = useQueryClient()
  const logout = async () => {
    await api('/api/auth/logout', { method: 'POST' })
    queryClient.clear() // drop this user's cached data before the login screen
    await queryClient.invalidateQueries({ queryKey: ['auth-me'] })
  }
  return (
    <div className="account-menu">
      <div className="account-name">
        <span className="dot" />
        {name}
      </div>
      <button className="account-logout" onClick={logout}>
        Log out
      </button>
    </div>
  )
}

export default function Layout() {
  const { data: me } = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => api<MeOut>('/api/auth/me'),
    retry: false,
  })
  const serverMode = me?.require_auth ?? false

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="wordmark">
          Educa<em>tor</em>
        </div>
        <div className="tagline">Adaptive mathematics</div>
        <nav>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.to === '/'}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        {serverMode ? <AccountMenu name={me?.user?.name ?? 'Account'} /> : <ProfileSwitcher />}
        <div className="foot">{serverMode ? 'server · multi-user' : 'local · offline-first'}</div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
