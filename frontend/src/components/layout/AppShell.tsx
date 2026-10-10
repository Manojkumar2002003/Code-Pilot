import { Route, Routes } from 'react-router-dom'

import Header from './Header'
import Sidebar from './Sidebar'
import DashboardPage from '../../pages/Dashboard'
import CreateProjectPage from '../../pages/CreateProjectPage'
import EditProjectPage from '../../pages/EditProjectPage'
import ProjectsPage from '../../pages/Projects'
import NotFoundPage from '../../pages/NotFoundPage'
import KnowledgePage from '../../pages/Knowledge'
import SettingsPage from '../../pages/Settings'
import ProjectWorkspaceLayout from '../workspace/ProjectWorkspaceLayout'
import ProjectWorkspaceOverviewPage from '../../pages/ProjectWorkspaceOverviewPage'
import ProjectWorkspacePlaceholderPage from '../../pages/ProjectWorkspacePlaceholderPage'
import RequirementsPage from '../../pages/RequirementsPage'

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
            <Route path="/projects/new" element={<CreateProjectPage />} />
            <Route path="/projects/:projectId/*" element={<ProjectWorkspaceLayout />}>
              <Route index element={<ProjectWorkspaceOverviewPage />} />
              <Route path="requirements" element={<RequirementsPage />} />
              <Route
                path="architecture"
                element={
                  <ProjectWorkspacePlaceholderPage
                    title="Architecture"
                    description="The architecture workspace for this project is planned for a future sprint."
                  />
                }
              />
              <Route
                path="tasks"
                element={
                  <ProjectWorkspacePlaceholderPage
                    title="Tasks"
                    description="The task workspace for this project is planned for a future sprint."
                  />
                }
              />
              <Route
                path="activity"
                element={
                  <ProjectWorkspacePlaceholderPage
                    title="Activity"
                    description="The activity workspace for this project is planned for a future sprint."
                  />
                }
              />
            </Route>
            <Route path="/projects/:projectId/edit" element={<EditProjectPage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default AppShell
