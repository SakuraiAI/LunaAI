import PanelCard from '../sections/PanelCard';

function GalleryPreview({ item }) {
  return (
    <div className={`gallery-preview ${item.type === 'video' ? 'is-video' : 'is-image'}`}>
      <span className="gallery-preview-badge">{item.type === 'video' ? 'VIDEO' : 'IMAGE'}</span>
      {item.saved ? <span className="gallery-saved-badge">ULOZENO</span> : null}
    </div>
  );
}

function GalleryGroup({ label, items, emptyLabel, onItemContext }) {
  return (
    <section className="gallery-group">
      <div className="gallery-group-head">
        <h4>{label}</h4>
        <span>{items.length}</span>
      </div>

      {items.length === 0 ? (
        <div className="gallery-group-empty">{emptyLabel}</div>
      ) : null}

      {items.map((item) => (
        <article
          key={item.id}
          className="gallery-card"
          onContextMenu={(event) => onItemContext?.(event, item)}
        >
          <GalleryPreview item={item} />
          <div className="gallery-card-copy">
            <strong>{item.title}</strong>
            <p>{item.meta}</p>
            {item.prompt ? <span>{item.prompt}</span> : null}
          </div>
        </article>
      ))}
    </section>
  );
}

export default function GalleryPage({ title, subtitle, items, onItemContext }) {
  const images = items.filter((item) => item.type === 'image');
  const videos = items.filter((item) => item.type === 'video');

  return (
    <div className="section-page-grid gallery-page-grid">
      <PanelCard title={title} subtitle={subtitle}>
        <div className="gallery-list">
          <GalleryGroup
            label="Photos"
            items={images}
            emptyLabel="No photos yet"
            onItemContext={onItemContext}
          />
        </div>
      </PanelCard>

      <PanelCard title="Videa" subtitle="Vsechna AI videa se ukladaji sem, aby v nich byl poradek a byly vzdy po ruce.">
        <div className="gallery-list gallery-video-list">
          <GalleryGroup
            label="Videa"
            items={videos}
            emptyLabel="No videos yet"
            onItemContext={onItemContext}
          />
        </div>
      </PanelCard>
    </div>
  );
}
