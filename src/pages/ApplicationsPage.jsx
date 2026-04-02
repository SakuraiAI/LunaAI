import { useEffect, useState } from 'react';
import PanelCard from '../sections/PanelCard';

export default function ApplicationsPage({ title, subtitle, items, selectedAppId, onSelectApp, onOpenApp, onSavePath }) {
  const selected = items.find((item) => item.id === selectedAppId) || items[0] || null;
  const [pathDraft, setPathDraft] = useState('');

  useEffect(() => {
    setPathDraft(selected?.path || '');
  }, [selected?.id, selected?.path]);

  return (
    <div className="applications-page-grid">
      <PanelCard title={title} subtitle={subtitle} className="applications-panel-card">
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
              <strong>No connected applications yet</strong>
              <p>Jakmile Luna nacte napojene desktop appky z backend settings, objevi se tady.</p>
            </div>
          )}
        </div>
      </PanelCard>

      <PanelCard
        title={selected?.title || 'Applications'}
        subtitle={selected?.connected ? 'Tato aplikace je napojena a Luna ji muze otevrit.' : 'Tady muzes doplnit nebo upravit cestu k aplikaci.'}
        className="applications-panel-card"
      >
        {selected ? (
          <div className="application-detail-surface">
            <div className="application-detail-block">
              <span>Stav</span>
              <strong>{selected.status}</strong>
              <small>{selected.connected ? 'Luna muze aplikaci spustit primo z desktop shellu.' : 'Kdyz ulozis platnou cestu, aplikace se prepne do connected stavu.'}</small>
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
              <small>Napojeni se uklada do Luna backend settings, aby UI i system pouzivaly stejny zdroj pravdy.</small>
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
