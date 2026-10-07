import { useCallback, useEffect, useMemo, useState } from 'react'

import EmptyState from '../components/common/EmptyState'
import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import { ApiError, getDependencyHealth, type SystemHealthResponse } from '../services/api'

type StatusValue = 'idle' | 'loading' | 'success' | 'empty' | 'error'

const statusText: Record<string, string> = {
  success: 'Healthy',
  error: 'Unreachable',
  loading: 'Checking system status...',
  idle: 'Idle',
  empty: 'No data available',
}

function SettingsPage() {
  const [systemHealth, setSystemHealth] = useState<SystemHealthResponse | null>(null)
  const [status, setStatus] = useState<StatusValue>('loading')
  const [error, setError] = useState<ApiError | null>(null)
  const [lastChecked, setLastChecked] = useState<string>('Not checked yet')

  const loadHealth = useCallback(async () => {
    setStatus('loading')
    setError(null)

    try {
      const response = await getDependencyHealth()
      setSystemHealth(response)
      setStatus(response && response.dependencies ? 'success' : 'empty')
      setLastChecked(
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      )
    } catch (requestError) {
      const apiError =
        requestError instanceof ApiError
          ? requestError
          : new ApiError('Unable to retrieve system status.', null, 'REQUEST_FAILED')
      setError(apiError)
      setStatus('error')
      setLastChecked('Unavailable')
    }
  }, [])

  useEffect(() => {
    void loadHealth()
  }, [loadHealth])

  const backendStatus = systemHealth?.dependencies.backend?.status ?? 'unhealthy'
  const databaseStatus = systemHealth?.dependencies.database?.status ?? 'unhealthy'
  const environment = systemHealth?.environment ?? 'Unknown'

  const overallStatus = useMemo(() => {
    if (status === 'loading') return 'Checking system status...'
    if (status === 'error') return 'Unable to retrieve system status.'
    if (status === 'empty') return 'No system data available.'
    return statusText[status] ?? 'Healthy'
  }, [status])

  const renderStatusBadge = (value: string) => {
    const normalizedValue = value === 'unknown' ? 'unhealthy' : value
    const token =
      normalizedValue === 'healthy' || normalizedValue === 'degraded' || normalizedValue === 'unhealthy'
        ? normalizedValue
        : 'success'

    return (
      <span className={`status-badge ${token}`} aria-live="polite">
        {statusText[token] ?? 'Healthy'}
      </span>
    )
  }

  if (status === 'loading') {
    return (
      <section className="page-panel">
        <div className="page-header">
          <div>
            <p className="eyebrow page-eyebrow">Settings</p>
            <h1>System Status</h1>
          </div>
        </div>
        <LoadingState message="Checking system status..." />
      </section>
    )
  }

  if (status === 'error') {
    return (
      <section className="page-panel">
        <div className="page-header">
          <div>
            <p className="eyebrow page-eyebrow">Settings</p>
            <h1>System Status</h1>
          </div>
        </div>
        <ErrorState
          title="Something went wrong"
          message={error?.message ?? 'Unable to retrieve system status.'}
          onRetry={() => void loadHealth()}
        />
      </section>
    )
  }

  if (status === 'empty') {
    return (
      <section className="page-panel">
        <div className="page-header">
          <div>
            <p className="eyebrow page-eyebrow">Settings</p>
            <h1>System Status</h1>
          </div>
        </div>
        <EmptyState
          title="No system data available"
          description="The backend is reachable, but there is no health data to display yet."
        />
      </section>
    )
  }

  return (
    <section className="page-panel">
      <div className="page-header">
        <div>
          <p className="eyebrow page-eyebrow">Settings</p>
          <h1>System Status</h1>
        </div>
      </div>

      <div className="system-status-panel">
        <div className="status-header-row">
          <div>
            <p className="status-label">Overall status</p>
            <h2>{overallStatus}</h2>
          </div>
          <button className="refresh-button" type="button" onClick={() => void loadHealth()}>
            Refresh
          </button>
        </div>

        <div className="status-grid">
          <div className="status-card">
            <div className="status-card-header">
              <span>Backend</span>
              {renderStatusBadge(backendStatus)}
            </div>
            <p>{systemHealth ? 'FastAPI application is reachable.' : 'FastAPI service is unreachable.'}</p>
          </div>

          <div className="status-card">
            <div className="status-card-header">
              <span>Database</span>
              {renderStatusBadge(databaseStatus)}
            </div>
            <p>{systemHealth ? 'SQLite database is reachable.' : 'Database status unavailable.'}</p>
          </div>

          <div className="status-card">
            <div className="status-card-header">
              <span>Environment</span>
              {renderStatusBadge(systemHealth ? 'healthy' : 'unhealthy')}
            </div>
            <p>{environment}</p>
          </div>
        </div>

        <div className="last-checked-row">
          <span>Last checked:</span>
          <strong>{lastChecked}</strong>
        </div>
      </div>
    </section>
  )
}

export default SettingsPage
