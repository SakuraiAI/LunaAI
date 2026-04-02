const projectTypes = [
  { id: 'investing', label: 'Investovani' },
  { id: 'home', label: 'Domaci ukoly' },
  { id: 'writing', label: 'Psani' },
  { id: 'travel', label: 'Cestovani' },
];

export default function ProjectModal({ visible, value, selectedType, onChange, onSelectType, onClose, onCreate }) {
  if (!visible) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="project-modal" onClick={(event) => event.stopPropagation()}>
        <div className="project-modal-head">
          <div>
            <h2>Vytvorit projekt</h2>
          </div>
          <div className="project-modal-actions">
            <button type="button" className="modal-icon-button" aria-label="Project settings">?</button>
            <button type="button" className="modal-icon-button" aria-label="Close" onClick={onClose}>?</button>
          </div>
        </div>

        <label className="project-field">
          <span>Nazev projektu</span>
          <input
            className="project-name-input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Vylet do Kodane"
          />
        </label>

        <div className="project-type-row">
          {projectTypes.map((type) => (
            <button
              key={type.id}
              type="button"
              className={`project-type-chip ${selectedType === type.id ? 'is-active' : ''}`}
              onClick={() => onSelectType(type.id)}
            >
              {type.label}
            </button>
          ))}
        </div>

        <div className="project-note">
          <p>V projektech se uchovavaji chaty, soubory a vlastni pokyny na jednom miste. Pouzivej je pro prubeznou praci nebo jen pro udrzeni poradku.</p>
        </div>

        <div className="project-modal-footer">
          <button type="button" className="primary-button project-create-button" onClick={onCreate} disabled={!value.trim()}>
            Vytvorit projekt
          </button>
        </div>
      </div>
    </div>
  );
}
