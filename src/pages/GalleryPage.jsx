import PanelCard from '../sections/PanelCard';

function GalleryPreview({ item }) {
  return (
    <div className={`gallery-preview ${item.type === 'video' ? 'is-video' : 'is-image'}`}>
      <span className="gallery-preview-badge">{item.type === 'video' ? 'VIDEO' : 'IMAGE'}</span>
    </div>
  );
}

function GalleryGroup({ label, items }) {
  return (
    <section className="gallery-group">
      <div className="gallery-group-head">
        <h4>{label}</h4>
        <span>{items.length}</span>
      </div>

      {items.length === 0 ? (
        <div className="gallery-group-empty">No {label.toLowerCase()} yet</div>
      ) : null}

      {items.map((item) => (
        <article key={item.id} className="gallery-card">
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

export default function GalleryPage({ title, subtitle, items }) {
  const images = items.filter((item) => item.type === 'image');
  const videos = items.filter((item) => item.type === 'video');
  const latestVideo = videos[0] || null;

  return (
    <div className="section-page-grid gallery-page-grid">
      <PanelCard title={title} subtitle={subtitle}>
        <div className="gallery-list">
          {items.length === 0 ? (
            <div className="surface-preview">
              <h4>Photos</h4>
              <p>Jakmile Luna vytvori obrazek, objevi se tady jako soucast foto archivu.</p>
              <div className="surface-preview-tags">
                <span>Photos</span>
                <span>AI archiv</span>
              </div>
            </div>
          ) : (
            <>
              <GalleryGroup label="Images" items={images} />
              <GalleryGroup label="Videos" items={videos} />
            </>
          )}
        </div>
      </PanelCard>

      <PanelCard title="Videa" subtitle="Vsechna AI videa se ukladaji sem, aby v nich byl poradek a byly vzdy po ruce.">
        <div className="gallery-detail">
          {latestVideo ? (
            <>
              <GalleryPreview item={latestVideo} />
              <div className="gallery-detail-copy">
                <h4>{latestVideo.title}</h4>
                <p>{latestVideo.meta}</p>
                {latestVideo.prompt ? <span>{latestVideo.prompt}</span> : null}
              </div>
            </>
          ) : (
            <div className="surface-preview">
              <h4>Videa</h4>
              <p>Jakmile Luna vytvori video, objevi se tady jako soucast video archivu.</p>
              <div className="surface-preview-tags">
                <span>Videa</span>
                <span>AI archiv</span>
              </div>
            </div>
          )}
        </div>
      </PanelCard>
    </div>
  );
}
