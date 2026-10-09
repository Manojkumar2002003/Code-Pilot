import { Link, useOutletContext } from 'react-router-dom'

import type { WorkspaceOutletContext } from '../components/workspace/ProjectWorkspaceLayout'

type ProjectWorkspacePlaceholderPageProps = {
  title: string
  description: string
}

function ProjectWorkspacePlaceholderPage({ title, description }: ProjectWorkspacePlaceholderPageProps) {
  const { project } = useOutletContext<WorkspaceOutletContext>()

  return (
    <div className="workspace-placeholder-panel">
      <div className="workspace-placeholder-icon">◌</div>
      <p className="eyebrow page-eyebrow">{title}</p>
      <h2>{title}</h2>
      <p>
        {description} This module is not implemented yet for <strong>{project.name}</strong>.
      </p>
      <Link to={`/projects/${project.id}`} className="secondary-button">
        Return to Overview
      </Link>
    </div>
  )
}

export default ProjectWorkspacePlaceholderPage
