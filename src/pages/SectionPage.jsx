import PanelCard from '../sections/PanelCard';

export default function SectionPage({ title, subtitle, items, actionLabel, onAction, onItemClick, onItemContext }) {
  return (
    <div className="section-page-grid">
      <PanelCard title={title} subtitle={subtitle}>
        {actionLabel && onAction ? (
          <div className="section-toolbar">
            <button type="button" className="secondary-button section-action-button" onClick={onAction}>
              {actionLabel}
            </button>
          </div>
        ) : null}
        <div className="stack-list">
          {items.map((item) => {
            const content = (
              <>
                <div>
                  <strong>{item.title || item.name}</strong>
                  <p>{item.meta || item.detail || item.nextStep || 'LunaAI system item'}</p>
                </div>
              </>
            );

            if (onItemClick) {
              return (
                <button
                  key={item.id}
                  type="button"
                  className="stack-card stack-card-button"
                  onClick={() => onItemClick(item)}
                  onContextMenu={onItemContext ? (event) => onItemContext(event, item) : undefined}
                >
                  {content}
                </button>
              );
            }

            return (
              <article
                key={item.id}
                className="stack-card"
                onContextMenu={onItemContext ? (event) => onItemContext(event, item) : undefined}
              >
                {content}
              </article>
            );
          })}
        </div>
      </PanelCard>

      <PanelCard title="System Surface" subtitle="A layered detail zone for state, preview, and future AI system integrations.">
        <div className="surface-preview">
          <div className="surface-preview-core" />
          <h4>{title}</h4>
          <p>{subtitle}</p>
          <div className="surface-preview-tags">
            <span>Monochrome</span>
            <span>Structured</span>
            <span>Desktop AI</span>
          </div>
        </div>
      </PanelCard>
    </div>
  );
}
