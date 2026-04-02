export default function ContextMenu({ visible, x, y, onRename, onPin, onDelete, onArchive, onClose }) {
  if (!visible) return null;

  return (
    <>
      <button className="context-backdrop" onClick={onClose} aria-label="Close context menu" />
      <div className="context-menu" style={{ left: x, top: y }} role="menu">
        <button type="button" onClick={onRename}>Rename</button>
        <button type="button" onClick={onPin}>Pin Chat</button>
        <button type="button" onClick={onDelete}>Delete</button>
        <button type="button" onClick={onArchive}>Archive</button>
      </div>
    </>
  );
}
