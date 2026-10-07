import { Navigate, Route, Routes } from 'react-router-dom'

import Header from './Header'
import Sidebar from './Sidebar'
import DashboardPage from '../../pages/Dashboard'
import ProjectsPage from '../../pages/Projects'
import KnowledgePage from '../../pages/Knowledge'
import SettingsPage from '../../pages/Settings'

function AppShell() {
  return (
    <div className="app-layout">
      <Sidebar />

      <div className="content-shell">
        <Header />

        <main className="content-area" aria-label="Main content area">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default AppShell
