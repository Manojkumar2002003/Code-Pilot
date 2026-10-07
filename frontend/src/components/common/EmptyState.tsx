export type EmptyStateProps = {
  title?: string
  description?: string
}

function EmptyState({
  title = 'No data available',
  description = 'There is nothing to display yet.',
}: EmptyStateProps) {
  return (
    <div className="state-panel empty-state" role="status" aria-live="polite">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  )
}

export default EmptyState
