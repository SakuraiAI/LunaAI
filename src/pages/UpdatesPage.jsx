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

export default function UpdatesPage({
  title,
  subtitle,
  items,
  currentVersion: runtimeVersion,
  initialFeed = null,
  onFeedChange,
  onStatusChange,
}) {
  const [feed, setFeed] = useState(() => initialFeed || fallbackFeed(items));
  const [selectedId, setSelectedId] = useState(items[0]?.id || '');
  const [busy, setBusy] = useState(false);

  function applyFeed(nextFeed) {
    const normalized = {
      ...fallbackFeed(items),
      ...nextFeed,
      entries: Array.isArray(nextFeed?.entries) && nextFeed.entries.length ? nextFeed.entries : items,
      currentVersion: nextFeed?.currentVersion || runtimeVersion || '0.1.0',
    };
    setFeed(normalized);
    onFeedChange?.(normalized);
  }

  useEffect(() => {
    if (initialFeed) {
      setFeed(initialFeed);
    }
  }, [initialFeed]);

  useEffect(() => {
    let active = true;

    async function loadFeed() {
      const api = window.lunaDesktop?.updates;
      if (!api?.getFeed) {
        if (active) {
          applyFeed(fallbackFeed(items));
        }
        return;
      }

      try {
        const nextFeed = await api.getFeed();
        if (!active) return;
        applyFeed(nextFeed);
      } catch {
        if (active) {
          applyFeed(fallbackFeed(items));
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
      onStatusChange?.('Kontrola update\u016f je p\u0159ipraven\u00e1 a\u017e v Electron okn\u011b.');
      return;
    }

    setBusy(true);
    try {
      const nextFeed = await api.check();
      applyFeed(nextFeed);
      onStatusChange?.(
        nextFeed?.updateAvailable
          ? `Nov\u00e1 verze ${nextFeed.latestVersion} je p\u0159ipraven\u00e1.`
          : 'LunaAI u\u017e b\u011b\u017e\u00ed na nejnov\u011bj\u0161\u00ed verzi.'
      );
    } catch {
      onStatusChange?.('Kontrolu update\u016f se nepoda\u0159ilo dokon\u010dit.');
    } finally {
      setBusy(false);
    }
  }

  async function handleDownloadUpdate() {
    const api = window.lunaDesktop?.updates;
    if (!api?.download) {
      onStatusChange?.('Sta\u017een\u00ed update funguje a\u017e v Electron desktop shellu.');
      return;
    }

    setBusy(true);
    try {
      const result = await api.download(feed.downloadUrl || '');
      onStatusChange?.(result?.message || 'Sta\u017een\u00ed update bylo spu\u0161t\u011bn\u00e9.');
    } catch {
      onStatusChange?.('Sta\u017een\u00ed update se nepoda\u0159ilo otev\u0159\u00edt.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="updates-page-grid">
      <PanelCard title={title} subtitle={subtitle} className="updates-panel-card">
        <div className="updates-summary-card">
          <div className="updates-summary-copy">
            <span className="updates-summary-label">Aktu\u00e1ln\u00ed verze</span>
            <strong>{feed.currentVersion || runtimeVersion || '0.1.0'}</strong>
            <p>
              {feed.updateAvailable
                ? `Nov\u00e1 verze ${feed.latestVersion} je p\u0159ipraven\u00e1 ke sta\u017een\u00ed.`
                : 'LunaAI je te\u010f synchronizovan\u00e1 s dostupn\u00fdm release feedem.'}
            </p>
          </div>
          <div className="updates-summary-meta">
            <div>
              <span>Nejnov\u011bj\u0161\u00ed</span>
              <strong>{feed.latestVersion || runtimeVersion || '0.1.0'}</strong>
              <small>{feed.publishedAt || '\u010cek\u00e1 se na release feed'}</small>
            </div>
            <div>
              <span>Kan\u00e1l</span>
              <strong>{feed.channel || 'stable'}</strong>
              <small>{feed.updateAvailable ? 'Update je k dispozici' : 'V\u0161echno je aktu\u00e1ln\u00ed'}</small>
            </div>
          </div>
          <div className="updates-summary-actions">
            <button type="button" className="secondary-button updates-action-button" onClick={handleCheckUpdates} disabled={busy}>
              Zkontrolovat update
            </button>
            <button
              type="button"
              className="primary-button updates-action-button"
              onClick={handleDownloadUpdate}
              disabled={busy || !feed.updateAvailable}
            >
              St\u00e1hnout update
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
        subtitle={selected ? `${selected.version} \u00b7 ${selected.date}` : 'Detail syst\u00e9mov\u00e9ho update LunaAI'}
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
              <span>Co se zm\u011bnilo</span>
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
