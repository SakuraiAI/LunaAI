import PanelCard from '../sections/PanelCard';

function ResourceSlider({ label, value, onChange, meta, accentLabel }) {
  return (
    <div className="settings-resource-card">
      <div className="settings-resource-head">
        <div>
          <strong>{label}</strong>
          <span>{accentLabel}</span>
        </div>
        <div className="settings-resource-value">{value}%</div>
      </div>
      <input
        className="settings-range"
        type="range"
        min="10"
        max="100"
        step="5"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <div className="settings-resource-meta">
        <span>{meta.primary}</span>
        <span>{meta.secondary}</span>
      </div>
    </div>
  );
}

export default function SettingsPage({ settings, onChange, onSave, appMeta }) {
  const memoryTotal = Number(appMeta.memoryGb || 0);
  const memoryBudget = memoryTotal ? Math.max(0.5, (memoryTotal * settings.memoryLimit) / 100).toFixed(1) : '--';

  return (
    <div className="section-page-grid settings-page-grid">
      <PanelCard title="System Limits" subtitle="Rid, kolik vykonu muze LunaAI vyuzit pri lokalnim behu, modelech a agentnich akcich.">
        <div className="settings-stack">
          <div className="settings-mode-strip">
            <button type="button" className={`settings-pill ${settings.profile === 'balanced' ? 'is-active' : ''}`} onClick={() => onChange({ profile: 'balanced', cpuLimit: 55, gpuLimit: 60, memoryLimit: 50 })}>
              Balanced
            </button>
            <button type="button" className={`settings-pill ${settings.profile === 'focused' ? 'is-active' : ''}`} onClick={() => onChange({ profile: 'focused', cpuLimit: 75, gpuLimit: 85, memoryLimit: 70 })}>
              Focused
            </button>
            <button type="button" className={`settings-pill ${settings.profile === 'light' ? 'is-active' : ''}`} onClick={() => onChange({ profile: 'light', cpuLimit: 35, gpuLimit: 40, memoryLimit: 35 })}>
              Light
            </button>
          </div>

          <ResourceSlider
            label="CPU"
            value={settings.cpuLimit}
            onChange={(cpuLimit) => onChange({ cpuLimit, profile: 'custom' })}
            accentLabel="Kolik jader a procesoru muze AI zatizit"
            meta={{
              primary: appMeta.cpu || 'CPU unavailable',
              secondary: `Aktualni system load: ${appMeta.cpuUsagePercent ?? '--'}%`,
            }}
          />

          <ResourceSlider
            label="GPU"
            value={settings.gpuLimit}
            onChange={(gpuLimit) => onChange({ gpuLimit, profile: 'custom' })}
            accentLabel="Kolik grafickeho vykonu ma Luna pouzit"
            meta={{
              primary: appMeta.gpu || 'GPU unavailable',
              secondary: `Aktualni system load: ${appMeta.gpuUsagePercent ?? '--'}%`,
            }}
          />

          <ResourceSlider
            label="Memory"
            value={settings.memoryLimit}
            onChange={(memoryLimit) => onChange({ memoryLimit, profile: 'custom' })}
            accentLabel="Kolik RAM muze AI rezervovat pro modely a projekty"
            meta={{
              primary: memoryTotal ? `Celkem RAM: ${memoryTotal} GB` : 'RAM unavailable',
              secondary: memoryTotal ? `AI budget: ${memoryBudget} GB` : 'AI budget unavailable',
            }}
          />

          <div className="settings-actions">
            <button type="button" className="primary-button settings-save-button" onClick={onSave}>
              Save
            </button>
          </div>
        </div>
      </PanelCard>

      <PanelCard title="Resource Summary" subtitle="Pravy panel drzi prehled toho, jaky limit ma AI aktualne nastaveny.">
        <div className="settings-summary-surface">
          <div className="settings-summary-core">
            <span className="settings-summary-label">Luna Runtime</span>
            <h4>{settings.profile === 'custom' ? 'Custom profile' : `${settings.profile.charAt(0).toUpperCase()}${settings.profile.slice(1)} profile`}</h4>
            <p>Tyhle limity pripravuji system na budouci backend, model routing a vykonove guardrails.</p>
          </div>
          <div className="settings-summary-grid">
            <div>
              <span>CPU limit</span>
              <strong>{settings.cpuLimit}%</strong>
              <small>{appMeta.cpu || 'Local processor'}</small>
            </div>
            <div>
              <span>GPU limit</span>
              <strong>{settings.gpuLimit}%</strong>
              <small>{appMeta.gpu || 'Graphics layer'}</small>
            </div>
            <div>
              <span>Memory limit</span>
              <strong>{settings.memoryLimit}%</strong>
              <small>{memoryTotal ? `${memoryBudget} GB for AI` : 'Memory budget pending'}</small>
            </div>
            <div>
              <span>Device</span>
              <strong>{appMeta.deviceName || 'This device'}</strong>
              <small>{appMeta.os || 'Desktop'} - {appMeta.arch || 'x64'}</small>
            </div>
          </div>
        </div>
      </PanelCard>
    </div>
  );
}
