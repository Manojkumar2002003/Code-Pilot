function SettingsPage() {
  return (
    <section className="page-panel">
      <div className="page-header">
        <div>
          <p className="eyebrow page-eyebrow">Settings</p>
          <h1>CodePilot Environment</h1>
        </div>
      </div>

      <div className="settings-card">
        <div className="settings-row">
          <span>Environment</span>
          <strong>Development</strong>
        </div>
        <div className="settings-row">
          <span>Backend</span>
          <strong>Local</strong>
        </div>
        <div className="settings-row">
          <span>Database</span>
          <strong>SQLite</strong>
        </div>
      </div>
    </section>
  )
}

export default SettingsPage
