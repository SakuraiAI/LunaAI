export default function PanelCard({ title, subtitle, children, className = '' }) {
  return (
    <section className={`panel-card ${className}`.trim()}>
      <header className="panel-card-head">
        <h3>{title}</h3>
        {subtitle ? <p>{subtitle}</p> : null}
      </header>
      <div className="panel-card-body">{children}</div>
    </section>
  );
}
