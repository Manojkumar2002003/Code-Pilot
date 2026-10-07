import { useEffect, useState } from 'react'

import { getHealth } from '../../services/api'

type ConnectionState = 'checking' | 'connected' | 'disconnected'

function Header() {
  const [connectionState, setConnectionState] = useState<ConnectionState>('checking')

  useEffect(() => {
    let isMounted = true

    async function verifyHealth() {
      try {
        await getHealth()

        if (isMounted) {
          setConnectionState('connected')
        }
      } catch (error) {
        if (isMounted) {
          setConnectionState('disconnected')
        }
      }
    }

    verifyHealth()

    return () => {
      isMounted = false
    }
  }, [])

  const statusLabel =
    connectionState === 'checking'
      ? 'Checking...'
      : connectionState === 'connected'
        ? 'Backend Connected'
        : 'Backend Disconnected'

  const statusClass = `topbar-status ${connectionState}`

  return (
    <header className="topbar">
      <div className="topbar-title">CodePilot</div>
      <div className={statusClass} aria-live="polite" aria-label="Backend connection status">
        <span className="status-dot" aria-hidden="true" />
        <span>{statusLabel}</span>
      </div>
    </header>
  )
}

export default Header
