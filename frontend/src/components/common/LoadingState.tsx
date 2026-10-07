export type LoadingStateProps = {
  message?: string
}

function LoadingState({ message = 'Loading...' }: LoadingStateProps) {
  return (
    <div className="state-panel loading-state" role="status" aria-live="polite">
      <div className="state-spinner" aria-hidden="true" />
      <p>{message}</p>
    </div>
  )
}

export default LoadingState
