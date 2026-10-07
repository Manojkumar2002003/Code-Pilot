import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '⌂' },
  { to: '/projects', label: 'Projects', icon: '▣' },
  { to: '/knowledge', label: 'Knowledge', icon: '◈' },
  { to: '/settings', label: 'Settings', icon: '⚙' },
]

function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Main navigation">
      <div className="brand-block">
        <div className="brand-mark">C</div>
        <div>
          <div className="brand-name">CodePilot</div>
        </div>
      </div>

      <nav className="nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'nav-item-active' : ''}`
            }
            aria-label={item.label}
          >
            <span className="nav-icon" aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="sidebar-label">Local Development</span>
      </div>
    </aside>
  )
}

export default Sidebar
