import { NavLink, Outlet } from 'react-router-dom'
import ProfileSwitcher from './ProfileSwitcher'

const links = [
  { to: '/', label: 'Today' },
  { to: '/courses', label: 'Courses' },
  { to: '/upload', label: 'Upload a book' },
  { to: '/stats', label: 'Stats' },
  { to: '/settings', label: 'Settings' },
]

export default function Layout() {
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
        <ProfileSwitcher />
        <div className="foot">local · offline-first</div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
