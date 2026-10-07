export type ErrorStateProps = {
  title?: string
  message: string
  onRetry?: () => void
  retryLabel?: string
}

function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  retryLabel = 'Retry',
}: ErrorStateProps) {
  return (
    <div className="state-panel error-state" role="alert" aria-live="assertive">
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="retry-button" onClick={onRetry}>
          {retryLabel}
        </button>
      ) : null}
    </div>
  )
}

export default ErrorState
