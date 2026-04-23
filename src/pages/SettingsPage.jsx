import { useEffect, useState } from 'react';
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

function ApplicationsSettingsSection({
  items,
  selectedAppId,
  onSelectApp,
  onOpenApp,
  onSavePath,
}) {
  const selected = items.find((item) => item.id === selectedAppId) || items[0] || null;
  const [pathDraft, setPathDraft] = useState('');

  useEffect(() => {
    setPathDraft(selected?.path || '');
  }, [selected?.id, selected?.path]);

  return (
    <div className="settings-applications-section applications-page-grid">
      <PanelCard
        title="Applications"
        subtitle="Tady spravujes napojene desktop aplikace, jejich cesty a to, co muze Luna primo otevirat."
        className="applications-panel-card"
      >
        <div className="applications-list">
          {items.length ? items.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`application-card ${selected?.id === item.id ? 'is-active' : ''}`}
              onClick={() => onSelectApp(item.id)}
            >
              <div className="application-card-copy">
                <strong>{item.title}</strong>
                <p>{item.detail}</p>
              </div>
              <span className={`application-status ${item.connected ? 'is-connected' : 'is-missing'}`}>
                {item.status}
              </span>
            </button>
          )) : (
            <div className="applications-empty">
              <strong>Zatim tu nejsou zadne napojene aplikace</strong>
              <p>Jakmile Luna nacte desktop appky z backend settings, objevi se tady.</p>
            </div>
          )}
        </div>
      </PanelCard>

      <PanelCard
        title={selected?.title || 'Application Detail'}
        subtitle={selected?.connected ? 'Tahleta aplikace je pripravena pro Luna desktop akce.' : 'Tady muzes doplnit nebo upravit cestu k aplikaci.'}
        className="applications-panel-card"
      >
        {selected ? (
          <div className="application-detail-surface">
            <div className="application-detail-block">
              <span>Stav</span>
              <strong>{selected.status}</strong>
              <small>{selected.connected ? 'Luna ji umi otevrit primo z desktop shellu.' : 'Po ulozeni platne cesty se prepne do connected stavu.'}</small>
            </div>
            <div className="application-detail-block">
              <span>Cesta</span>
              <input
                className="application-path-input"
                type="text"
                value={pathDraft}
                onChange={(event) => setPathDraft(event.target.value)}
                placeholder="Zadej cestu k .exe souboru"
              />
              <small>Napojeni se uklada do backend settings, aby UI i system pouzivaly stejny zdroj pravdy.</small>
            </div>
            <div className="application-detail-actions">
              <button
                type="button"
                className="secondary-button application-save-button"
                onClick={() => onSavePath(selected, pathDraft)}
              >
                Save path
              </button>
              <button
                type="button"
                className="primary-button application-open-button"
                onClick={() => onOpenApp(selected)}
                disabled={!selected.connected}
              >
                {selected.ctaLabel || 'Open'}
              </button>
            </div>
          </div>
        ) : null}
      </PanelCard>
    </div>
  );
}

export default function SettingsPage({
  settings,
  onChange,
  onSave,
  appMeta,
  applications,
  selectedAppId,
  onSelectApp,
  onOpenApp,
  onSavePath,
}) {
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

      <ApplicationsSettingsSection
        items={applications}
        selectedAppId={selectedAppId}
        onSelectApp={onSelectApp}
        onOpenApp={onOpenApp}
        onSavePath={onSavePath}
      />
    </div>
  );
}
