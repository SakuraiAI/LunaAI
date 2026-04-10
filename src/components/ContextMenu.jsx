export default function ContextMenu({ visible, x, y, onRename, onPin, onDelete, onArchive, onClose, labels = {}, showArchive = true, showPin = true }) {
  if (!visible) return null;

  const renameLabel = labels.rename || 'Rename';
  const pinLabel = labels.pin || 'Pin Chat';
  const deleteLabel = labels.delete || 'Delete';
  const archiveLabel = labels.archive || 'Archive';

  return (
    <>
      <button className="context-backdrop" onClick={onClose} aria-label="Close context menu" />
      <div className="context-menu" style={{ left: x, top: y }} role="menu">
        <button type="button" onClick={onRename}>{renameLabel}</button>
        {showPin ? <button type="button" onClick={onPin}>{pinLabel}</button> : null}
        <button type="button" onClick={onDelete}>{deleteLabel}</button>
        {showArchive ? <button type="button" onClick={onArchive}>{archiveLabel}</button> : null}
      </div>
    </>
  );
}
