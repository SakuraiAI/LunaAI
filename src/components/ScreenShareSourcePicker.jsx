export default function ScreenShareSourcePicker({
  picker,
  onClose,
  onRefresh,
  onSelectSource,
}) {
  if (!picker?.open) return null;

  const sources = Array.isArray(picker.sources) ? picker.sources : [];

  return (
    <div className="screen-share-picker-backdrop" role="presentation" onClick={onClose}>
      <section
        className="screen-share-picker"
        role="dialog"
        aria-modal="true"
        aria-label="Vyber zdroj sdileni obrazovky"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="screen-share-picker-head">
          <div>
            <h3>Vyber, co chces sdilet</h3>
            <p>Po vyberu uvidis zivy nahled a Luna s Xenem dostanou obnovovane framy z vybraneho zdroje.</p>
          </div>
          <button type="button" className="screen-share-picker-close" onClick={onClose}>
            Zavrit
          </button>
        </div>

        <div className="screen-share-picker-actions">
          <button type="button" className="secondary-button" onClick={onRefresh} disabled={picker.loading}>
            {picker.loading ? 'Nacitam...' : 'Obnovit zdroje'}
          </button>
          {picker.error ? <span className="screen-share-picker-error">{picker.error}</span> : null}
        </div>

        <div className="screen-share-picker-grid">
          {sources.map((source) => (
            <button
              key={source.id}
              type="button"
              className="screen-share-source-card"
              onClick={() => onSelectSource(source)}
              disabled={picker.loading || picker.selectingId === source.id}
            >
              <div className="screen-share-source-preview">
                {source.thumbnailDataUrl ? (
                  <img src={source.thumbnailDataUrl} alt={source.name} />
                ) : (
                  <div className="screen-share-source-empty">{source.kind === 'screen' ? 'MONITOR' : 'OKNO'}</div>
                )}
              </div>
              <div className="screen-share-source-copy">
                <strong>{source.name}</strong>
                <span>{source.kind === 'screen' ? 'Cely monitor' : 'Jedno okno'}</span>
              </div>
            </button>
          ))}

          {!picker.loading && sources.length === 0 ? (
            <div className="screen-share-source-none">
              <strong>Nenasel se zadny zdroj sdileni.</strong>
              <p>Zkus znovu nacist zdroje nebo otevrit jine okno mimo LunaAI.</p>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
