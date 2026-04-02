import { useEffect, useMemo, useState } from 'react';
import AppShell from './layouts/AppShell';
import TopBar from './components/TopBar';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import ChatInput from './components/ChatInput';
import ContextMenu from './components/ContextMenu';
import ProfilePanel from './components/ProfilePanel';
import NotificationsPanel from './components/NotificationsPanel';
import ProjectModal from './components/ProjectModal';
import GalleryPage from './pages/GalleryPage';
import SectionPage from './pages/SectionPage';
import SettingsPage from './pages/SettingsPage';
import ApplicationsPage from './pages/ApplicationsPage';
import UpdatesPage from './pages/UpdatesPage';
import {
  sidebarSections,
  initialChats,
  initialMessages,
  galleryItems,
  projectCards,
  updates,
} from './data/mockData';

const sectionTitles = {
  chat: { title: 'Luna Workspace', subtitle: 'A calm command surface for Luna, Xeno, the agent layer, and future local reasoning.' },
  gallery: { title: 'Photos', subtitle: 'AI obrazky se ukladaji sem, aby zustaly prehledne a pohromade.' },
  projects: { title: 'Projects', subtitle: 'Long-term workspaces, execution tracks, and structured system memory.' },
  applications: { title: 'Applications', subtitle: 'Connected desktop tools, launch bridges, and future deep integrations.' },
  updates: { title: 'Updates', subtitle: 'Patch-note style system feed for LunaAI and internal layer changes.' },
  friends: { title: 'Friends / Groups', subtitle: 'Visible and hidden AI entities arranged as connected system relationships.' },
  settings: { title: 'Settings', subtitle: 'Runtime, identity, and control surfaces prepared for a desktop AI system.' },
};

const fallbackMeta = {
  version: '0.1.0',
  deviceName: 'LunaAI Desktop',
  os: 'Windows',
  arch: 'x64',
  cpu: 'Unknown CPU',
  gpu: 'Unavailable',
  gpuVendor: 'unknown',
  cpuUsagePercent: null,
  gpuUsagePercent: null,
  memoryGb: 0,
  memoryUsedGb: 0,
  memoryUsagePercent: null,
  platform: 'desktop',
};

const STORAGE_KEYS = {
  chats: 'lunaai-react-chats',
  currentChatId: 'lunaai-react-current-chat-id',
  messages: 'lunaai-react-chat-messages',
  projects: 'lunaai-react-projects',
  gallery: 'lunaai-react-gallery',
  settings: 'lunaai-react-settings',
};

const defaultRuntimeSettings = {
  profile: 'balanced',
  cpuLimit: 55,
  gpuLimit: 60,
  memoryLimit: 50,
};

const initialNotifications = [
  { id: 'n-1', kind: 'invite', label: 'Invite', title: 'Friend request ready', detail: 'Tady se pozdeji ukazou pozvanky od pratel a lidi z webu.' },
  { id: 'n-2', kind: 'group', label: 'Group', title: 'Group layer prepared', detail: 'Pozvanky do skupin a sdilenych mistnosti se budou zobrazovat tady.' },
  { id: 'n-3', kind: 'system', label: 'System', title: 'Notification bell online', detail: 'Top-right zvonek je pripraveny pro social a system udalosti.' },
];

function readStoredJson(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function buildInitialChatThreads() {
  if (initialChats.length === 0 || initialMessages.length === 0) return {};
  const firstId = initialChats[0]?.id;
  return firstId ? { [firstId]: initialMessages } : {};
}


function inferGeneratedMediaType(text, pendingGenerationType) {
  if (pendingGenerationType) return pendingGenerationType;
  if (/\b(video|clip|animation|motion)\b/i.test(text)) return 'video';
  if (/\b(image|render|illustration|portrait|photo|poster)\b/i.test(text)) return 'image';
  return '';
}

function buildGalleryTitle(text, mediaType) {
  const cleaned = text.replace(/generate/gi, '').replace(/image|video|clip|animation|render/gi, '').trim();
  if (!cleaned) return mediaType === 'video' ? 'LunaAI Video Output' : 'LunaAI Image Output';
  return cleaned.slice(0, 48);
}

function buildRendererFallbackMeta() {
  const ua = navigator.userAgent || '';
  const platform = navigator.userAgentData?.platform || navigator.platform || 'desktop';
  const memoryGb = Number(navigator.deviceMemory || 0);
  const cpuCores = Number(navigator.hardwareConcurrency || 0);

  let os = 'Desktop';
  if (/Windows/i.test(ua)) os = 'Windows';
  else if (/Mac/i.test(ua)) os = 'macOS';
  else if (/Linux/i.test(ua)) os = 'Linux';

  return {
    deviceName: 'This device',
    os,
    arch: /64/.test(ua) ? 'x64' : 'unknown',
    cpu: cpuCores ? `${cpuCores} logical cores` : 'CPU available',
    gpu: 'Renderer mode',
    gpuVendor: 'renderer',
    memoryGb,
    memoryUsedGb: memoryGb ? Math.max(1, Math.round(memoryGb * 0.5)) : 0,
    memoryUsagePercent: memoryGb ? 50 : null,
    platform: String(platform || 'desktop').toLowerCase(),
  };
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState('chat');
  const [chats, setChats] = useState(() => readStoredJson(STORAGE_KEYS.chats, initialChats));
  const [currentChatId, setCurrentChatId] = useState(() => window.localStorage.getItem(STORAGE_KEYS.currentChatId) || initialChats[0]?.id || '');
  const [chatMessages, setChatMessages] = useState(() => readStoredJson(STORAGE_KEYS.messages, buildInitialChatThreads()));
  const [projects, setProjects] = useState(() => readStoredJson(STORAGE_KEYS.projects, projectCards));
  const [gallery, setGallery] = useState(() => readStoredJson(STORAGE_KEYS.gallery, galleryItems));
  const [runtimeSettings, setRuntimeSettings] = useState(() => readStoredJson(STORAGE_KEYS.settings, defaultRuntimeSettings));
  const [applicationsState, setApplicationsState] = useState([]);
  const [selectedApplicationId, setSelectedApplicationId] = useState('');
  const [composer, setComposer] = useState('');
  const [attachmentLabel, setAttachmentLabel] = useState('');
  const [status, setStatus] = useState('LunaAI desktop shell ready.');
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0, kind: 'chat', targetId: '', title: '' });
  const [appMeta, setAppMeta] = useState(fallbackMeta);
  const [signedInAs, setSignedInAs] = useState(() => window.localStorage.getItem('lunaai-signed-in') || '');
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [pendingGenerationType, setPendingGenerationType] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectType, setProjectType] = useState('investing');

  const profileName = signedInAs ? signedInAs.split('@')[0] : 'Sakurai Haise';
  const notificationCount = initialNotifications.length;
  const pageData = sectionTitles[page] || sectionTitles.chat;
  const messages = currentChatId ? chatMessages[currentChatId] || [] : [];

  useEffect(() => {
    const api = window.lunaDesktop;

    async function refreshMeta() {
      if (!api?.app?.getMeta) {
        setAppMeta((current) => ({ ...current, ...buildRendererFallbackMeta() }));
        return;
      }

      try {
        const meta = await api.app.getMeta();
        setAppMeta((current) => ({ ...current, ...meta }));
        if (meta?.runtimeSettings) {
          setRuntimeSettings((current) => ({ ...current, ...meta.runtimeSettings }));
        }
      } catch {
        setAppMeta((current) => ({ ...current, ...buildRendererFallbackMeta() }));
      }
    }

    async function refreshApplications() {
      if (!api?.apps?.list) {
        return;
      }
      try {
        const nextApps = await api.apps.list();
        setApplicationsState(Array.isArray(nextApps) ? nextApps : []);
      } catch {
        setApplicationsState([]);
      }
    }

    refreshMeta();
    refreshApplications();
    const intervalId = window.setInterval(refreshMeta, 3000);
    const applicationsIntervalId = window.setInterval(refreshApplications, 6000);

    if (!api?.app?.getMeta) {
      setStatus('Renderer mode active. Desktop system details are partially estimated.');
    }

    return () => {
      window.clearInterval(intervalId);
      window.clearInterval(applicationsIntervalId);
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEYS.chats, JSON.stringify(chats));
  }, [chats]);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEYS.messages, JSON.stringify(chatMessages));
  }, [chatMessages]);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEYS.projects, JSON.stringify(projects));
  }, [projects]);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEYS.gallery, JSON.stringify(gallery));
  }, [gallery]);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEYS.settings, JSON.stringify(runtimeSettings));
  }, [runtimeSettings]);

  useEffect(() => {
    if (currentChatId) {
      window.localStorage.setItem(STORAGE_KEYS.currentChatId, currentChatId);
    } else {
      window.localStorage.removeItem(STORAGE_KEYS.currentChatId);
    }
  }, [currentChatId]);

  const filteredChats = useMemo(() => {
    const query = search.trim().toLowerCase();
    return chats
      .filter((chat) => !chat.archived)
      .filter((chat) => (query ? chat.title.toLowerCase().includes(query) : true))
      .sort((a, b) => Number(Boolean(b.pinned)) - Number(Boolean(a.pinned)) || a.title.localeCompare(b.title));
  }, [chats, search]);

  const regularChats = useMemo(() => filteredChats.filter((chat) => !chat.projectId), [filteredChats]);
  const visibleProjects = useMemo(() => projects.filter((project) => !project.archived).sort((a, b) => Number(Boolean(b.pinned)) - Number(Boolean(a.pinned)) || (a.title || '').localeCompare(b.title || '')), [projects]);

  useEffect(() => {
    if (!applicationsState.length) {
      setSelectedApplicationId('');
      return;
    }
    setSelectedApplicationId((current) => (
      current && applicationsState.some((item) => item.id === current)
        ? current
        : applicationsState[0].id
    ));
  }, [applicationsState]);

  function appendMessages(chatId, nextMessages) {
    setChatMessages((current) => ({
      ...current,
      [chatId]: [...(current[chatId] || []), ...nextMessages],
    }));
  }

  function ensureActiveChat() {
    if (currentChatId) return currentChatId;
    const chatId = `chat-${Date.now()}`;
    const newChat = { id: chatId, title: 'New Chat', pinned: false, archived: false, kind: 'chat' };
    setChats((current) => [newChat, ...current]);
    setCurrentChatId(chatId);
    setChatMessages((current) => ({ ...current, [chatId]: [] }));
    return chatId;
  }

  function handleSend() {
    const text = composer.trim();
    if (!text && !attachmentLabel) return;

    const activeChatId = ensureActiveChat();
    const baseText = text || 'Attachment prepared for LunaAI.';
    const decoratedText = attachmentLabel ? `${baseText}

[Attached file: ${attachmentLabel}]` : baseText;
    const mediaType = inferGeneratedMediaType(baseText, pendingGenerationType);

    appendMessages(activeChatId, [
      { id: `user-${Date.now()}`, role: 'user', author: 'You', content: decoratedText },
      {
        id: `assistant-${Date.now() + 1}`,
        role: 'assistant',
        author: 'Luna',
        content: mediaType
          ? `Luna prepared a ${mediaType} concept and saved it to Gallery.`
          : 'React + Electron shell accepted the request. IPC is prepared so Luna can later forward this to local AI, Xeno, or agent logic.',
      },
    ]);

    if (mediaType) {
      const galleryEntry = {
        id: `g-${Date.now()}`,
        type: mediaType,
        title: buildGalleryTitle(baseText, mediaType),
        meta: mediaType === 'video' ? 'AI video output' : 'AI image output',
        prompt: baseText,
        createdAt: Date.now(),
      };
      setGallery((current) => [galleryEntry, ...current]);
    }

    setChats((current) => current.map((chat) => (
      chat.id === activeChatId && chat.title === 'New Chat' && text
        ? { ...chat, title: text.slice(0, 36) }
        : chat
    )));

    setComposer('');
    setAttachmentLabel('');
    setPendingGenerationType('');
    setStatus('Message routed through the LunaAI renderer shell.');
    setPage('chat');
  }

  async function handleWindowAction(action) {
    const api = window.lunaDesktop?.window;

    if (api) {
      if (action === 'minimize') await api.minimize();
      if (action === 'maximize') await api.maximize();
      if (action === 'close') await api.close();
      return;
    }

    if (action === 'maximize') {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen?.();
        setStatus('Preview mode: fullscreen toggled because Electron window controls are not attached.');
      } else {
        document.exitFullscreen?.();
        setStatus('Preview mode: fullscreen restored.');
      }
      return;
    }

    if (action === 'minimize') {
      setStatus('Minimize works only inside the Electron desktop window.');
      return;
    }

    if (action === 'close') {
      window.close();
      setStatus('Close works only inside the Electron desktop window.');
    }
  }

  function handleNewChat() {
    const chatId = `chat-${Date.now()}`;
    const newChat = { id: chatId, title: 'New Chat', pinned: false, archived: false, kind: 'chat' };
    setChats((current) => [newChat, ...current]);
    setCurrentChatId(chatId);
    setChatMessages((current) => ({ ...current, [chatId]: [] }));
    setComposer('');
    setAttachmentLabel('');
    setPendingGenerationType('');
    setPage('chat');
    setStatus('New conversation created.');
  }

  function handleChatOpen(chatId) {
    setCurrentChatId(chatId);
    setPage('chat');
    setStatus('Conversation ready.');
  }

  function handleChatContext(event, chat) {
    event.preventDefault();
    setContextMenu({ visible: true, x: event.clientX, y: event.clientY, kind: 'chat', targetId: chat.id, title: chat.title });
  }

  function handleProjectContext(event, project) {
    event.preventDefault();
    setContextMenu({ visible: true, x: event.clientX, y: event.clientY, kind: 'project', targetId: project.id, title: project.title });
  }

  function closeContextMenu() {
    setContextMenu((current) => ({ ...current, visible: false }));
  }

  function renameChat() {
    const next = window.prompt('Rename chat', contextMenu.title);
    if (!next) return closeContextMenu();

    if (contextMenu.kind === 'project') {
      let linkedChatId = '';
      setProjects((current) => current.map((project) => {
        if (project.id !== contextMenu.targetId) return project;
        linkedChatId = project.chatId || '';
        return { ...project, title: next };
      }));
      if (linkedChatId) {
        setChats((current) => current.map((chat) => (chat.id === linkedChatId ? { ...chat, title: next } : chat)));
      }
      setStatus('Project title updated.');
      closeContextMenu();
      return;
    }

    setChats((current) => current.map((chat) => (chat.id === contextMenu.targetId ? { ...chat, title: next } : chat)));
    setStatus('Chat title updated.');
    closeContextMenu();
  }

  function pinChat() {
    if (contextMenu.kind === 'project') {
      setProjects((current) => current.map((project) => (project.id === contextMenu.targetId ? { ...project, pinned: !project.pinned } : project)));
      setStatus('Project pin state updated.');
      closeContextMenu();
      return;
    }

    setChats((current) => current.map((chat) => (chat.id === contextMenu.targetId ? { ...chat, pinned: !chat.pinned } : chat)));
    setStatus('Chat pin state updated.');
    closeContextMenu();
  }

  function deleteChat() {
    if (contextMenu.kind === 'project') {
      const linkedProject = projects.find((project) => project.id === contextMenu.targetId);
      const linkedChatId = linkedProject?.chatId || '';

      setProjects((current) => current.filter((project) => project.id !== contextMenu.targetId));
      if (linkedChatId) {
        const nextChats = chats.filter((chat) => chat.id !== linkedChatId);
        setChats(nextChats);
        setChatMessages((current) => {
          const next = { ...current };
          delete next[linkedChatId];
          return next;
        });
        if (currentChatId === linkedChatId) {
          setCurrentChatId(nextChats[0]?.id ?? '');
        }
      }
      setStatus('Project removed from the workspace.');
      closeContextMenu();
      return;
    }

    const nextChats = chats.filter((chat) => chat.id !== contextMenu.targetId);
    setChats(nextChats);
    setChatMessages((current) => {
      const next = { ...current };
      delete next[contextMenu.targetId];
      return next;
    });
    if (currentChatId === contextMenu.targetId) {
      setCurrentChatId(nextChats[0]?.id ?? '');
    }
    setStatus('Chat removed from the workspace.');
    closeContextMenu();
  }

  function archiveChat() {
    if (contextMenu.kind === 'project') {
      setProjects((current) => current.map((project) => (project.id === contextMenu.targetId ? { ...project, archived: true } : project)));
      setStatus('Project archived from Projects.');
      closeContextMenu();
      return;
    }

    setChats((current) => current.map((chat) => (chat.id === contextMenu.targetId ? { ...chat, archived: true } : chat)));
    setStatus('Chat archived from the main sidebar.');
    closeContextMenu();
  }

  function handleOpenNotifications() {
    setNotificationsOpen((current) => !current);
    setProfileOpen(false);
  }

  function handleSignIn() {
    const email = window.prompt('Sign in to LunaAI', signedInAs || 'operator@lunaai.local');
    if (!email) return;
    const cleaned = email.trim();
    if (!cleaned) return;
    setSignedInAs(cleaned);
    window.localStorage.setItem('lunaai-signed-in', cleaned);
    setStatus(`Signed in as ${cleaned}`);
  }

  function handleInputAction(action, payload) {
    if (action === 'file' && payload) {
      setAttachmentLabel(payload.name);
      setStatus(`Attached file: ${payload.name}`);
      return;
    }
    if (action === 'image') {
      setPendingGenerationType('image');
      setComposer((current) => current || 'Generate a black-and-white futuristic image for LunaAI.');
      setStatus('Image generation prompt loaded into the composer.');
      return;
    }
    const messagesByAction = {
      menu: 'Quick action surface is ready for file and image workflows.',
      mic: 'Microphone interaction is reserved for the voice layer.',
      voice: 'Voice mode shell is prepared for future conversational loops.',
    };
    setStatus(messagesByAction[action] || 'Action prepared.');
  }

  async function handleSaveApplicationPath(appItem, nextPath) {
    if (!appItem?.key) return;

    const api = window.lunaDesktop?.apps;
    if (!api?.updatePath) {
      setStatus('Application path editing works only inside the Electron desktop shell.');
      return;
    }

    try {
      const result = await api.updatePath(appItem.key, nextPath);
      if (Array.isArray(result?.apps)) {
        setApplicationsState(result.apps);
      }
      setStatus(result?.message || `${appItem.title} path saved.`);
    } catch {
      setStatus(`${appItem.title} path could not be saved.`);
    }
  }

  async function handleOpenApplication(appItem) {
    if (!appItem?.key) return;

    const api = window.lunaDesktop?.apps;
    if (!api?.launch) {
      setStatus('Application launch works only inside the Electron desktop shell.');
      return;
    }

    try {
      const result = await api.launch(appItem.key);
      setStatus(result?.message || `${appItem.title} action finished.`);
      if (api.list) {
        const nextApps = await api.list();
        setApplicationsState(Array.isArray(nextApps) ? nextApps : []);
      }
    } catch {
      setStatus(`${appItem.title} could not be launched.`);
    }
  }

  function handleAddFriends() {
    setStatus('Friend system can be connected next. The add-friends surface is ready.');
  }

  function handleRuntimeSettings(nextPartial) {
    setRuntimeSettings((current) => ({ ...current, ...nextPartial }));
    setStatus('Runtime resource limits adjusted.');
  }

  async function handleSaveRuntimeSettings() {
    window.localStorage.setItem(STORAGE_KEYS.settings, JSON.stringify(runtimeSettings));

    try {
      const api = window.lunaDesktop?.settings;
      if (api?.saveRuntime) {
        const saved = await api.saveRuntime(runtimeSettings);
        setRuntimeSettings((current) => ({ ...current, ...saved }));
        setStatus('Runtime resource limits saved to desktop settings.');
        return;
      }
    } catch {
      setStatus('Runtime settings were saved locally, but desktop sync failed.');
      return;
    }

    setStatus('Runtime resource limits saved.');
  }

  function handleOpenProjectModal() {
    setProjectModalOpen(true);
  }

  function handleCloseProjectModal() {
    setProjectModalOpen(false);
  }

  function handleCreateProject() {
    const name = projectName.trim();
    if (!name) return;

    const chatId = `project-chat-${Date.now()}`;
    const projectId = `p-${Date.now()}`;

    const typeLabels = {
      investing: 'Track goals and decisions in one place',
      home: 'Organize tasks, notes, and practical follow-ups',
      writing: 'Keep drafts, structure, and research aligned',
      travel: 'Collect plans, routes, and trip context',
    };

    const createdProject = {
      id: projectId,
      title: name,
      phase: projectType,
      nextStep: typeLabels[projectType] || 'Structured LunaAI project',
      tasks: 0,
      chatId,
    };

    setProjects((current) => [createdProject, ...current]);
    setChats((current) => [{ id: chatId, title: name, pinned: false, archived: false, projectId, kind: 'project' }, ...current]);
    setChatMessages((current) => ({ ...current, [chatId]: [] }));
    setCurrentChatId(chatId);
    setProjectModalOpen(false);
    setProjectName('');
    setProjectType('investing');
    setPage('chat');
    setStatus(`Project created: ${name}`);
  }

  function handleOpenProjectChat(project) {
    let targetChatId = project.chatId;

    if (!targetChatId) {
      targetChatId = `project-chat-${Date.now()}`;
      setProjects((current) => current.map((item) => (item.id === project.id ? { ...item, chatId: targetChatId } : item)));
      setChats((current) => [{ id: targetChatId, title: project.title, pinned: false, archived: false, projectId: project.id, kind: 'project' }, ...current]);
      setChatMessages((current) => ({ ...current, [targetChatId]: current[targetChatId] || [] }));
    } else if (!chats.some((chat) => chat.id === targetChatId)) {
      setChats((current) => [{ id: targetChatId, title: project.title, pinned: false, archived: false, projectId: project.id, kind: 'project' }, ...current]);
    }

    setCurrentChatId(targetChatId);
    setPage('chat');
    setStatus(`Project channel ready: ${project.title}`);
  }

  function renderMain() {
    if (page === 'chat') {
      const isEmptyChat = messages.length === 0;

      return (
        <div className={`chat-page ${isEmptyChat ? 'is-empty' : ''}`}>
          <ChatArea messages={messages} />
          <ChatInput
            value={composer}
            onChange={setComposer}
            onSend={handleSend}
            onAction={handleInputAction}
            attachmentLabel={attachmentLabel}
            onClearAttachment={() => setAttachmentLabel('')}
            centered={isEmptyChat}
          />
        </div>
      );
    }

    if (page === 'gallery') {
      return <GalleryPage title={pageData.title} subtitle={pageData.subtitle} items={gallery} />;
    }
    if (page === 'projects') {
      return <SectionPage title={pageData.title} subtitle={pageData.subtitle} items={visibleProjects} actionLabel="Create project" onAction={handleOpenProjectModal} onItemClick={handleOpenProjectChat} onItemContext={handleProjectContext} />;
    }
    if (page === 'applications') {
      return (
        <ApplicationsPage
          title={pageData.title}
          subtitle={pageData.subtitle}
          items={applicationsState}
          selectedAppId={selectedApplicationId}
          onSelectApp={setSelectedApplicationId}
          onOpenApp={handleOpenApplication}
          onSavePath={handleSaveApplicationPath}
        />
      );
    }
    if (page === 'updates') {
      return (
        <UpdatesPage
          title={pageData.title}
          subtitle={pageData.subtitle}
          items={updates}
          currentVersion={appMeta.version}
          onStatusChange={setStatus}
        />
      );
    }
    if (page === 'settings') {
      return <SettingsPage settings={runtimeSettings} onChange={handleRuntimeSettings} onSave={handleSaveRuntimeSettings} appMeta={appMeta} />;
    }
    if (page === 'friends') {
      return (
        <div className="friends-page">
          <div className="friends-empty-card">
            <div className="friends-empty-copy">
              <h2>Friends</h2>
              <p>Keep this surface clean until the social layer is properly connected.</p>
            </div>
            <button className="primary-button friends-add-button" type="button" onClick={handleAddFriends}>
              Add friends
            </button>
          </div>
        </div>
      );
    }
    return <SectionPage title={pageData.title} subtitle={pageData.subtitle} items={updates} />;
  }

  return (
    <>
      <AppShell
        topbar={
          <TopBar
            collapsed={sidebarCollapsed}
            onToggleSidebar={() => setSidebarCollapsed((current) => !current)}
            profileName={profileName}
            onOpenProfile={() => { setProfileOpen(true); setNotificationsOpen(false); }}
            onOpenNotifications={handleOpenNotifications}
            notificationCount={notificationCount}
            onWindowAction={handleWindowAction}
          />
        }
        sidebar={
          <Sidebar
            collapsed={sidebarCollapsed}
            search={search}
            onSearchChange={setSearch}
            sections={sidebarSections}
            currentPage={page}
            onSelectPage={setPage}
            regularChats={regularChats}
            currentChatId={currentChatId}
            onNewChat={handleNewChat}
            onChatOpen={handleChatOpen}
            onChatContext={handleChatContext}
            onOpenSettings={() => setPage('settings')}
          />
        }
        main={renderMain()}
        profilePanel={
          <ProfilePanel
            visible={profileOpen}
            profileName={profileName}
            appMeta={appMeta}
            signedInAs={signedInAs}
            signInLabel={signedInAs ? 'Switch account' : 'Sign in'}
            onSignIn={handleSignIn}
            onClose={() => setProfileOpen(false)}
          />
        }
        notificationsPanel={
          <NotificationsPanel
            visible={notificationsOpen}
            items={initialNotifications}
            onClose={() => setNotificationsOpen(false)}
          />
        }
        contextMenu={
          <ContextMenu
            visible={contextMenu.visible}
            x={contextMenu.x}
            y={contextMenu.y}
            onRename={renameChat}
            onPin={pinChat}
            onDelete={deleteChat}
            onArchive={archiveChat}
            onClose={closeContextMenu}
          />
        }
      />
      <ProjectModal
        visible={projectModalOpen}
        value={projectName}
        selectedType={projectType}
        onChange={setProjectName}
        onSelectType={setProjectType}
        onClose={handleCloseProjectModal}
        onCreate={handleCreateProject}
      />
    </>
  );
}
