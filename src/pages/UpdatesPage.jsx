import { useEffect, useMemo, useState } from 'react';
import PanelCard from '../sections/PanelCard';

function fallbackFeed(items) {
  const first = items[0] || null;
  return {
    currentVersion: '0.1.0',
    latestVersion: first?.version || '0.1.0',
    publishedAt: first?.date || '',
    channel: 'stable',
    updateAvailable: false,
    downloadUrl: '',
    entries: items,
  };
}

export default function UpdatesPage({ title, subtitle, items, currentVersion: runtimeVersion, onStatusChange }) {
  const [feed, setFeed] = useState(() => fallbackFeed(items));
  const [selectedId, setSelectedId] = useState(items[0]?.id || '');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadFeed() {
      const api = window.lunaDesktop?.updates;
      if (!api?.getFeed) {
        if (active) {
          setFeed(fallbackFeed(items));
        }
        return;
      }

      try {
        const nextFeed = await api.getFeed();
        if (!active) return;
        setFeed({
          ...fallbackFeed(items),
          ...nextFeed,
          entries: Array.isArray(nextFeed?.entries) && nextFeed.entries.length ? nextFeed.entries : items,
          currentVersion: nextFeed?.currentVersion || runtimeVersion || '0.1.0',
        });
      } catch {
        if (active) {
          setFeed(fallbackFeed(items));
        }
      }
    }

    loadFeed();
    return () => {
      active = false;
    };
  }, [items, runtimeVersion]);

  const entries = useMemo(() => (Array.isArray(feed.entries) ? feed.entries : items), [feed.entries, items]);

  useEffect(() => {
    if (!entries.length) {
      setSelectedId('');
      return;
    }
    setSelectedId((current) => (entries.some((item) => item.id === current) ? current : entries[0].id));
  }, [entries]);

  const selected = entries.find((item) => item.id === selectedId) || entries[0] || null;

  async function handleCheckUpdates() {
    const api = window.lunaDesktop?.updates;
    if (!api?.check) {
      onStatusChange?.('Desktop updater check je pripraveny az v Electron okne.');
      return;
    }

    setBusy(true);
    try {
      const nextFeed = await api.check();
      setFeed({
        ...fallbackFeed(items),
        ...nextFeed,
        entries: Array.isArray(nextFeed?.entries) && nextFeed.entries.length ? nextFeed.entries : items,
        currentVersion: nextFeed?.currentVersion || runtimeVersion || '0.1.0',
      });
      onStatusChange?.(
        nextFeed?.updateAvailable
          ? `Nova verze ${nextFeed.latestVersion} je pripravena.`
          : 'LunaAI je uz na nejnovejsi verzi.'
      );
    } catch {
      onStatusChange?.('Update check se nepodaril dokoncit.');
    } finally {
      setBusy(false);
    }
  }

  async function handleDownloadUpdate() {
    const api = window.lunaDesktop?.updates;
    if (!api?.download) {
      onStatusChange?.('Download update funguje az v Electron desktop shellu.');
      return;
    }

    setBusy(true);
    try {
      const result = await api.download(feed.downloadUrl || '');
      onStatusChange?.(result?.message || 'Update download action finished.');
    } catch {
      onStatusChange?.('Update download se nepodarilo otevrit.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="updates-page-grid">
      <PanelCard title={title} subtitle={subtitle} className="updates-panel-card">
        <div className="updates-summary-card">
          <div className="updates-summary-copy">
            <span className="updates-summary-label">Current version</span>
            <strong>{feed.currentVersion || runtimeVersion || '0.1.0'}</strong>
            <p>
              {feed.updateAvailable
                ? `Nova verze ${feed.latestVersion} je pripravena ke stazeni.`
                : 'LunaAI je aktualne synchronizovana s dostupnym release feedem.'}
            </p>
          </div>
          <div className="updates-summary-meta">
            <div>
              <span>Latest</span>
              <strong>{feed.latestVersion || runtimeVersion || '0.1.0'}</strong>
              <small>{feed.publishedAt || 'Release feed pending'}</small>
            </div>
            <div>
              <span>Channel</span>
              <strong>{feed.channel || 'stable'}</strong>
              <small>{feed.updateAvailable ? 'Update available' : 'Up to date'}</small>
            </div>
          </div>
          <div className="updates-summary-actions">
            <button type="button" className="secondary-button updates-action-button" onClick={handleCheckUpdates} disabled={busy}>
              Check updates
            </button>
            <button
              type="button"
              className="primary-button updates-action-button"
              onClick={handleDownloadUpdate}
              disabled={busy || !feed.updateAvailable}
            >
              Download update
            </button>
          </div>
        </div>

        <div className="updates-list">
          {entries.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`update-card ${selected?.id === item.id ? 'is-active' : ''}`}
              onClick={() => setSelectedId(item.id)}
            >
              <div className="update-card-top">
                <span className="update-badge">{item.status}</span>
                <small>{item.date}</small>
              </div>
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
            </button>
          ))}
        </div>
      </PanelCard>

      <PanelCard
        title={selected?.title || 'Update'}
        subtitle={selected ? `${selected.version} ? ${selected.date}` : 'LunaAI system update detail'}
        className="updates-panel-card"
      >
        {selected ? (
          <div className="update-detail-surface">
            <div className="update-detail-meta">
              <span className="update-badge">{selected.status}</span>
              <span className="update-version-chip">{selected.version}</span>
            </div>
            <p className="update-detail-copy">{selected.detail}</p>
            <div className="update-notes-block">
              <span>What changed</span>
              <div className="update-notes-list">
                {selected.notes?.map((note, index) => (
                  <div key={`${selected.id}-note-${index}`} className="update-note-item">
                    <strong>{String(index + 1).padStart(2, '0')}</strong>
                    <p>{note}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </PanelCard>
    </div>
  );
}
