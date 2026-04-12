import { useEffect, useMemo, useRef, useState } from 'react';
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
  page: 'lunaai-react-page',
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

function shouldConsultXeno(text) {
  return /\b(navrhni|architektura|architekturu|rizika|tok dat|rozdelej|faze|f?ze|kroky|implementace|plan|pl[a?]n|workspace|strategi|system)\b/i.test(text);
}

function getRequestedSpeaker(text) {
  const normalized = String(text || '').trim().toLowerCase();
  if (!normalized) return null;
  if (/\bxeno(ai)?\b/.test(normalized)) return 'Xeno';
  if (/\bluna(ai)?\b/.test(normalized) || /\bluno\b/.test(normalized)) return 'Luna';
  return null;
}

function createThinkingState(text, { fallbackToLuna = true } = {}) {
  const requestedSpeaker = getRequestedSpeaker(text);
  const consultXeno = shouldConsultXeno(text);

  if (requestedSpeaker === 'Xeno') {
    return {
      visible: true,
      lunaActive: false,
      xenoActive: true,
      tracks: [
        {
          speaker: 'Xeno',
          title: 'Xeno direct',
          note: 'Prebira reasoning vrstvu a sklada odpoved.',
        },
      ],
    };
  }

  if (requestedSpeaker === 'Luna') {
    return {
      visible: true,
      lunaActive: true,
      xenoActive: consultXeno,
      tracks: consultXeno
        ? [
            {
              speaker: 'Luna',
              title: 'Luna',
              note: 'Drzi odpoved a posila Xeno strategic check.',
            },
            {
              speaker: 'Xeno',
              title: 'Xeno -> Luna',
              note: 'Kontroluje rizika, strukturu a dalsi nejlepsi krok.',
            },
          ]
        : [
            {
              speaker: 'Luna',
              title: 'Luna',
              note: 'Sklada primou odpoved bez Xeno handoffu.',
            },
          ],
    };
  }

  return {
    visible: true,
    lunaActive: fallbackToLuna,
    xenoActive: consultXeno,
    tracks: consultXeno
      ? [
          {
            speaker: 'Luna',
            title: 'Luna',
            note: 'Drzi hlavni odpoved a sklada uzivatelskou vrstvu.',
          },
          {
            speaker: 'Xeno',
            title: 'Xeno -> Luna',
            note: 'Pridava planning, rizika a strategic support.',
          },
        ]
      : fallbackToLuna
        ? [
            {
              speaker: 'Luna',
              title: 'Luna',
              note: 'Drzi primou odpoved bez druhe vrstvy.',
            },
          ]
        : [],
  };
}

const idleThinkingState = {
  visible: false,
  lunaActive: false,
  xenoActive: false,
  tracks: [],
};

function normalizeCoordinationState(coordination, fallbackText = '') {
  if (!coordination || typeof coordination !== 'object') {
    return fallbackText ? createThinkingState(fallbackText) : idleThinkingState;
  }

  const lunaActive = Boolean(coordination.lunaActive);
  const xenoActive = Boolean(coordination.xenoActive);
  const tracks = Array.isArray(coordination.tracks)
    ? coordination.tracks
      .map((item) => ({
        speaker: String(item?.speaker || '').trim(),
        title: String(item?.title || item?.speaker || '').trim(),
        note: String(item?.note || '').trim(),
      }))
      .filter((item) => item.speaker && item.note)
    : [];

  if (!lunaActive && !xenoActive && tracks.length === 0) {
    return fallbackText ? createThinkingState(fallbackText) : idleThinkingState;
  }

  return {
    visible: true,
    lunaActive,
    xenoActive,
    tracks,
  };
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
  const [page, setPage] = useState(() => window.localStorage.getItem(STORAGE_KEYS.page) || 'chat');
  const [chats, setChats] = useState(() => readStoredJson(STORAGE_KEYS.chats, initialChats));
  const [currentChatId, setCurrentChatId] = useState(() => window.localStorage.getItem(STORAGE_KEYS.currentChatId) || initialChats[0]?.id || '');
  const [chatMessages, setChatMessages] = useState(() => readStoredJson(STORAGE_KEYS.messages, buildInitialChatThreads()));
  const [projects, setProjects] = useState(() => readStoredJson(STORAGE_KEYS.projects, projectCards));
  const [gallery, setGallery] = useState(() => readStoredJson(STORAGE_KEYS.gallery, galleryItems));
  const [runtimeSettings, setRuntimeSettings] = useState(() => readStoredJson(STORAGE_KEYS.settings, defaultRuntimeSettings));
  const [applicationsState, setApplicationsState] = useState([]);
  const [selectedApplicationId, setSelectedApplicationId] = useState('');
  const [composer, setComposer] = useState('');
  const [attachment, setAttachment] = useState(null);
  const [status, setStatus] = useState('LunaAI desktop shell ready.');
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0, kind: 'chat', targetId: '', title: '', saved: false });
  const [appMeta, setAppMeta] = useState(fallbackMeta);
  const [signedInAs, setSignedInAs] = useState(() => window.localStorage.getItem('lunaai-signed-in') || '');
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [pendingGenerationType, setPendingGenerationType] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectType, setProjectType] = useState('investing');
  const [chatBusy, setChatBusy] = useState(false);
  const [thinkingState, setThinkingState] = useState(idleThinkingState);
  const [revealingMessage, setRevealingMessage] = useState(null);
  const [pendingAction, setPendingAction] = useState({ active: false, title: '' });
  const revealTimerRef = useRef(null);
  const revealActiveRef = useRef(false);

  const profileName = signedInAs ? signedInAs.split('@')[0] : 'Sakurai Haise';
  const notificationCount = initialNotifications.length;
  const pageData = sectionTitles[page] || sectionTitles.chat;
  const messages = currentChatId ? chatMessages[currentChatId] || [] : [];

  useEffect(() => () => {
    if (attachment?.previewUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(attachment.previewUrl);
    }
  }, [attachment]);

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
    window.localStorage.setItem(STORAGE_KEYS.page, page);
  }, [page]);

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

  function clearRevealTimer() {
    if (revealTimerRef.current) {
      window.cancelAnimationFrame(revealTimerRef.current);
      revealTimerRef.current = null;
    }
  }

  function applyChatState(result, overrideMessages = null) {
    if (!result?.ok) return false;
    if (Array.isArray(result.chats)) {
      setChats(result.chats);
    }
    if (typeof result.currentChatId === 'string') {
      setCurrentChatId(result.currentChatId);
    }
    setPendingAction({
      active: Boolean(result?.pendingAction?.active),
      title: String(result?.pendingAction?.title || ''),
    });
    if (Array.isArray(overrideMessages) && typeof result.currentChatId === 'string') {
      setChatMessages((current) => ({
        ...current,
        [result.currentChatId]: overrideMessages,
      }));
      return true;
    }
    if (Array.isArray(result.messages) && typeof result.currentChatId === 'string') {
      setChatMessages((current) => ({
        ...current,
        [result.currentChatId]: result.messages,
      }));
    }
    return true;
  }

  function startAssistantReveal({ chatId, author = 'Luna', fullText, commit }) {
    clearRevealTimer();
    const normalizedText = String(fullText || '').trim();
    if (!normalizedText) {
      revealActiveRef.current = false;
      commit?.();
      return;
    }

    revealActiveRef.current = true;
    setRevealingMessage({ chatId, author, content: '', fullText: normalizedText });
    let index = 0;
    let lastTick = 0;

    const step = (timestamp) => {
      if (!lastTick) lastTick = timestamp;
      const elapsed = timestamp - lastTick;
      if (elapsed >= 32) {
        lastTick = timestamp;
        const nextChunk = Math.max(2, Math.ceil(normalizedText.length / 56));
        index = Math.min(normalizedText.length, index + nextChunk);
        const nextContent = normalizedText.slice(0, index);
        setRevealingMessage({ chatId, author, content: nextContent, fullText: normalizedText });
      }

      if (index >= normalizedText.length) {
        clearRevealTimer();
        revealActiveRef.current = false;
        setRevealingMessage(null);
        commit?.();
        return;
      }

      revealTimerRef.current = window.requestAnimationFrame(step);
    };

    revealTimerRef.current = window.requestAnimationFrame(step);
  }

  function applyBackendChatState(result) {
    return applyChatState(result);
  }

  useEffect(() => () => {
    clearRevealTimer();
    revealActiveRef.current = false;
  }, []);

  useEffect(() => {
    const api = window.lunaDesktop?.luna;
    if (!api?.getState) return;

    let cancelled = false;

    async function loadChatState() {
      try {
        const result = await api.getState();
        if (cancelled) return;
        if (applyBackendChatState(result)) {
          setStatus('Luna backend chat connected.');
        }
      } catch {
        // keep local fallback state
      }
    }

    loadChatState();
    return () => {
      cancelled = true;
    };
  }, []);

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

  async function handleSend() {
    const text = composer.trim();
    if ((!text && !attachment?.name) || chatBusy) return;

    const api = window.lunaDesktop?.luna;
    const activeChatId = ensureActiveChat();
    const baseText = text || 'Attachment prepared for LunaAI.';
    const decoratedText = attachment?.name ? `${baseText}

[Attached file: ${attachment.name}]` : baseText;
    const mediaType = inferGeneratedMediaType(baseText, pendingGenerationType);

    if (api?.sendMessage) {
      setChatBusy(true);
      setThinkingState(createThinkingState(baseText));
      try {
        const result = await api.sendMessage({ chatId: activeChatId, text: decoratedText });
        if (handleBackendResponseResult(result, 'Luna backend replied.')) {
          // handled above
        } else {
          appendMessages(activeChatId, [
            { id: `user-${Date.now()}`, role: 'user', author: 'You', content: decoratedText },
            { id: `assistant-${Date.now() + 1}`, role: 'assistant', author: 'Luna', content: result?.message || 'Luna backend did not return a valid reply.' },
          ]);
          setStatus(result?.message || 'Luna backend did not return a valid reply.');
        }
      } catch {
        appendMessages(activeChatId, [
          { id: `user-${Date.now()}`, role: 'user', author: 'You', content: decoratedText },
          { id: `assistant-${Date.now() + 1}`, role: 'assistant', author: 'Luna', content: 'Spojeni s backendem se nepovedlo.' },
        ]);
        setStatus('Backend bridge failed.');
      } finally {
        setChatBusy(false);
        if (!revealActiveRef.current) {
          setThinkingState((current) => (current.visible ? idleThinkingState : current));
        }
      }
    } else {
      const fallbackResponse = mediaType
        ? `Luna prepared a ${mediaType} concept and saved it to Gallery.`
        : 'React + Electron shell accepted the request. IPC is prepared so Luna can later forward this to local AI, Xeno, or agent logic.';

      setThinkingState(createThinkingState(baseText));
      appendMessages(activeChatId, [
        { id: `user-${Date.now()}`, role: 'user', author: 'You', content: decoratedText },
      ]);
      setChats((current) => current.map((chat) => (
        chat.id === activeChatId && chat.title === 'New Chat' && text
          ? { ...chat, title: text.slice(0, 36) }
          : chat
      )));
      const requestedSpeaker = getRequestedSpeaker(baseText);
      const revealAuthor = requestedSpeaker === 'Xeno' ? 'Xeno' : 'Luna';

      startAssistantReveal({
        chatId: activeChatId,
        author: revealAuthor,
        fullText: fallbackResponse,
        commit: () => {
          appendMessages(activeChatId, [
            {
              id: `assistant-${Date.now() + 1}`,
              role: 'assistant',
              author: revealAuthor,
              content: fallbackResponse,
            },
          ]);
          setThinkingState(idleThinkingState);
          setStatus('Message routed through the LunaAI renderer shell.');
        },
      });
    }

    if (mediaType) {
      const galleryEntry = {
        id: `g-${Date.now()}`,
        type: mediaType,
        title: buildGalleryTitle(baseText, mediaType),
        meta: mediaType === 'video' ? 'AI video output' : 'AI image output',
        prompt: baseText,
        createdAt: Date.now(),
        saved: false,
      };
      setGallery((current) => [galleryEntry, ...current]);
    }

    setComposer('');
    setAttachment(null);
    setPendingGenerationType('');
    setPage('chat');
  }


  function handleBackendResponseResult(result, successStatus) {
    if (!result?.ok) {
      setThinkingState(idleThinkingState);
      setStatus(result?.message || 'Luna backend did not return a valid reply.');
      return false;
    }

    const backendMessages = Array.isArray(result.messages) ? result.messages : [];
    const lastBackendMessage = backendMessages[backendMessages.length - 1];
    const canRevealAssistant = lastBackendMessage?.role === 'assistant' && String(lastBackendMessage.content || '').trim();
    const coordinationState = normalizeCoordinationState(
      result?.coordination,
      String(lastBackendMessage?.content || ''),
    );

    if (canRevealAssistant) {
      applyChatState(result, backendMessages.slice(0, -1));
      setThinkingState(coordinationState);
      startAssistantReveal({
        chatId: result.currentChatId || currentChatId,
        author: lastBackendMessage.author || 'Luna',
        fullText: lastBackendMessage.content,
        commit: () => {
          applyBackendChatState(result);
          setThinkingState(idleThinkingState);
          setStatus(successStatus);
        },
      });
      return true;
    }

    applyBackendChatState(result);
    setThinkingState(idleThinkingState);
    setStatus(successStatus);
    return true;
  }

  async function handlePendingActionDecision(kind) {
    const api = window.lunaDesktop?.luna;
    if (!api) return;

    setChatBusy(true);
    setThinkingState({ visible: true, lunaActive: true, xenoActive: false });
    try {
      const result = kind === 'confirm'
        ? await api.confirmPendingAction()
        : await api.cancelPendingAction();
      const handled = handleBackendResponseResult(result, kind === 'confirm' ? 'Akce byla potvrzena.' : 'Akce byla zrusena.');
      if (kind === 'cancel' && handled) {
        const backendMessages = Array.isArray(result?.messages) ? result.messages : [];
        const lastBackendMessage = backendMessages[backendMessages.length - 1];
        if (lastBackendMessage?.role !== 'assistant') {
          const targetChatId = result?.currentChatId || currentChatId;
          appendMessages(targetChatId, [
            { id: `assistant-${Date.now()}`, role: 'assistant', author: 'Luna', content: 'Luna: Akci jsem zrusila.' },
          ]);
        }
      }
    } catch {
      setStatus(kind === 'confirm' ? 'Potvrzeni akce selhalo.' : 'Zruseni akce selhalo.');
    } finally {
      setChatBusy(false);
      if (!revealActiveRef.current) {
        setThinkingState((current) => (current.visible ? idleThinkingState : current));
      }
    }
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

  async function handleNewChat() {
    const api = window.lunaDesktop?.luna;
    if (api?.createChat) {
      try {
        const result = await api.createChat('New chat');
        if (applyBackendChatState(result)) {
          setStatus('New conversation created.');
        }
      } catch {
        setStatus('Creating a backend chat failed.');
      }
    } else {
      const chatId = `chat-${Date.now()}`;
      const newChat = { id: chatId, title: 'New Chat', pinned: false, archived: false, kind: 'chat' };
      setChats((current) => [newChat, ...current]);
      setCurrentChatId(chatId);
      setChatMessages((current) => ({ ...current, [chatId]: [] }));
      setStatus('New conversation created.');
    }
    setComposer('');
    setAttachment(null);
    setPendingGenerationType('');
    setPage('chat');
  }

  async function handleChatOpen(chatId) {
    const api = window.lunaDesktop?.luna;
    if (api?.switchChat) {
      try {
        const result = await api.switchChat(chatId);
        applyBackendChatState(result);
      } catch {
        setCurrentChatId(chatId);
      }
    } else {
      setCurrentChatId(chatId);
    }
    setPage('chat');
    setStatus('Conversation ready.');
  }

  function handleChatContext(event, chat) {
    event.preventDefault();
    setContextMenu({ visible: true, x: event.clientX, y: event.clientY, kind: 'chat', targetId: chat.id, title: chat.title, saved: false });
  }

  function handleProjectContext(event, project) {
    event.preventDefault();
    setContextMenu({ visible: true, x: event.clientX, y: event.clientY, kind: 'project', targetId: project.id, title: project.title, saved: false });
  }

  function handleGalleryContext(event, item) {
    event.preventDefault();
    setContextMenu({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      kind: 'gallery',
      targetId: item.id,
      title: item.title,
      saved: Boolean(item.saved),
    });
  }

  function closeContextMenu() {
    setContextMenu((current) => ({ ...current, visible: false }));
  }

  function renameChat() {
    const promptLabel = contextMenu.kind === 'gallery' ? 'Upravit nazev polozky' : 'Rename chat';
    const next = window.prompt(promptLabel, contextMenu.title);
    if (!next) return closeContextMenu();

    if (contextMenu.kind === 'gallery') {
      setGallery((current) => current.map((item) => (item.id === contextMenu.targetId ? { ...item, title: next } : item)));
      setStatus('Nazev polozky byl upraven.');
      closeContextMenu();
      return;
    }

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

    const api = window.lunaDesktop?.luna;
    if (api?.renameChat) {
      api.renameChat(contextMenu.targetId, next)
        .then((result) => {
          applyBackendChatState(result);
          setStatus('Chat title updated.');
        })
        .catch(() => {
          setChats((current) => current.map((chat) => (chat.id === contextMenu.targetId ? { ...chat, title: next } : chat)));
          setStatus('Chat title updated locally.');
        });
      closeContextMenu();
      return;
    }

    setChats((current) => current.map((chat) => (chat.id === contextMenu.targetId ? { ...chat, title: next } : chat)));
    setStatus('Chat title updated.');
    closeContextMenu();
  }

  function pinChat() {
    if (contextMenu.kind === 'gallery') {
      setGallery((current) => current.map((item) => (item.id === contextMenu.targetId ? { ...item, saved: true } : item)));
      setStatus('Polozka byla ulozena do galerie.');
      closeContextMenu();
      return;
    }

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
    if (contextMenu.kind === 'gallery') {
      setGallery((current) => current.filter((item) => item.id !== contextMenu.targetId));
      setStatus('Polozka byla vymazana z galerie.');
      closeContextMenu();
      return;
    }

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

    const api = window.lunaDesktop?.luna;
    if (api?.deleteChat) {
      api.deleteChat(contextMenu.targetId)
        .then((result) => {
          applyBackendChatState(result);
          setStatus('Chat removed from the workspace.');
        })
        .catch(() => {
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
          setStatus('Chat removed locally.');
        });
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
      const nextAttachment = {
        name: payload.name,
        type: payload.type || '',
        previewUrl: payload.type?.startsWith('image/') ? URL.createObjectURL(payload) : '',
      };
      setAttachment((current) => {
        if (current?.previewUrl?.startsWith('blob:')) URL.revokeObjectURL(current.previewUrl);
        return nextAttachment;
      });
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

  const contextMenuLabels = contextMenu.kind === 'gallery'
    ? { rename: 'Upravit', pin: contextMenu.saved ? 'Ulozeno' : 'Ulozit', delete: 'Vymazat' }
    : { rename: 'Rename', pin: 'Pin Chat', delete: 'Delete', archive: 'Archive' };

  function renderMain() {
    if (page === 'chat') {
      const isEmptyChat = messages.length === 0;

      return (
        <div className={`chat-page ${isEmptyChat ? 'is-empty' : ''}`}>
          <ChatArea
            messages={messages}
            chatId={currentChatId}
            thinkingState={thinkingState}
            revealingMessage={revealingMessage?.chatId === currentChatId ? revealingMessage : null}
            pendingAction={pendingAction}
            onConfirmPendingAction={() => handlePendingActionDecision('confirm')}
            onCancelPendingAction={() => handlePendingActionDecision('cancel')}
          />
          <ChatInput
            value={composer}
            onChange={setComposer}
            onSend={handleSend}
            onAction={handleInputAction}
            attachment={attachment}
            onClearAttachment={() => setAttachment(null)}
            centered={isEmptyChat}
          />
        </div>
      );
    }

    if (page === 'gallery') {
      return <GalleryPage title={pageData.title} subtitle={pageData.subtitle} items={gallery} onItemContext={handleGalleryContext} />;
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
            labels={contextMenuLabels}
            showArchive={contextMenu.kind !== 'gallery'}
            showPin={true}
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
