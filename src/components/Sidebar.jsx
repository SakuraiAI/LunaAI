export default function Sidebar({
  collapsed,
  search,
  onSearchChange,
  sections,
  currentPage,
  onSelectPage,
  regularChats,
  currentChatId,
  onNewChat,
  onChatOpen,
  onChatContext,
  onOpenSettings,
}) {
  return (
    <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''}`}>
      <div className="sidebar-top">
        <div className="sidebar-section-label">
          <span className="sidebar-section-label-full">Luna Control</span>
          <span className="sidebar-section-label-short">L</span>
        </div>
        <div className="sidebar-search-wrap">
          <input
            className="sidebar-search"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search"
          />
        </div>

        <button className="new-chat-button" type="button" onClick={onNewChat}>
          <span className="new-chat-button-full">+ New Chat</span>
          <span className="new-chat-button-short">+</span>
        </button>

        <nav className="sidebar-nav">
          {sections.map((section) => (
            <button
              key={section.key}
              type="button"
              className={`sidebar-nav-item ${currentPage === section.key ? 'is-active' : ''}`}
              onClick={() => onSelectPage(section.key)}
            >
              <span className="sidebar-nav-mark" />
              <span className="sidebar-nav-label-full">{section.label}</span>
              <span className="sidebar-nav-label-short">{section.label.charAt(0)}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="sidebar-chat-panel">
        <span className="sidebar-label">
          <span className="sidebar-label-full">Chat History</span>
          <span className="sidebar-label-short">C</span>
        </span>
        <div className="sidebar-chat-list">
          {regularChats.length === 0 && <div className="sidebar-empty">No chats yet</div>}
          {regularChats.map((chat) => (
            <button
              key={chat.id}
              type="button"
              className={`chat-list-item ${currentChatId === chat.id ? 'is-active' : ''}`}
              onClick={() => onChatOpen(chat.id)}
              onContextMenu={(event) => onChatContext(event, chat)}
            >
              <span className="chat-list-item-full">{chat.title}</span>
              <span className="chat-list-item-short">{chat.title.charAt(0)}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-settings-wrap">
          <button className="settings-button" type="button" onClick={onOpenSettings}>
            <span className="settings-button-full">Settings</span>
            <span className="settings-button-short">S</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
