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
import DesktopShareOverlay from './components/DesktopShareOverlay';
import ScreenShareSourcePicker from './components/ScreenShareSourcePicker';
import VoiceSessionOverlay from './components/VoiceSessionOverlay';
import GalleryPage from './pages/GalleryPage';
import SectionPage from './pages/SectionPage';
import SettingsPage from './pages/SettingsPage';
import UpdatesPage from './pages/UpdatesPage';
import { createTaskPlanner } from './planner/taskPlanner';
import { normalizeTransportText } from './utils/textRepair';
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
  seenUpdateVersion: 'lunaai-seen-update-version',
};

const defaultRuntimeSettings = {
  profile: 'balanced',
  cpuLimit: 55,
  gpuLimit: 60,
  memoryLimit: 50,
};

const screenShareFrameIntervalMs = 1000;
const screenShareVisionIntervalMs = 1000;
const spokenTextLimit = 720;

function detectSpeechLanguage(text) {
  // NVIDIA Magpie currently sounds more stable when the language follows the configured voice.
  // Forcing cs-CZ on an English voice makes Czech speech noticeably robotic.
  void text;
  return 'en-US';
}

function shapeTextForSpeech(text) {
  let value = normalizeTransportText(text || '')
    .replace(/\[Model debug\][\s\S]*$/i, '')
    .replace(/```[\s\S]*?```/g, 'Kód přeskočím, ať se to dobře poslouchá.')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/#{1,6}\s*/g, '')
    .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
    .replace(/https?:\/\/\S+/gi, 'odkaz')
    .replace(/^\s*(Luna|Xeno)\s*:\s*/i, '')
    .replace(/\s+(Luna|Xeno)\s*:\s*/gi, ' ')
    .replace(/[•*_>#~|]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!value) return '';

  if (value.length > spokenTextLimit) {
    const sentences = value.match(/[^.!?…]+[.!?…]+/g) || [];
    const compact = [];
    let total = 0;
    for (const sentence of sentences) {
      const next = sentence.trim();
      if (!next) continue;
      if (total + next.length > spokenTextLimit) break;
      compact.push(next);
      total += next.length + 1;
      if (compact.length >= 4) break;
    }
    value = compact.length ? compact.join(' ') : `${value.slice(0, spokenTextLimit).trim()}...`;
  }

  return value
    .replace(/\s*([.!?…])\s*/g, '$1 ')
    .replace(/\s*,\s*/g, ', ')
    .replace(/\s+/g, ' ')
    .trim();
}

function normalizeIntentText(value) {
  return normalizeTransportText(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function shouldForceVoiceActionExecution(value) {
  const text = normalizeIntentText(value);
  if (!text) return false;

  const destructiveSignals = [
    'smaz',
    'vymaz',
    'delete',
    'remove',
    'klik',
    'click',
    'napis',
    'type',
    'prepis',
    'overwrite',
    'append',
  ];
  if (destructiveSignals.some((signal) => text.includes(signal))) {
    return false;
  }

  return /^(otevri|otevrit|open|spust|spustit|start|launch|zapni|zapnout|run)\b/.test(text);
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function isStartDesktopShareIntent(value) {
  const text = normalizeIntentText(value);
  if (!text) return false;

  const hasShareWord = /\b(share|shere|sdileni|sdilet|sdilej)\b/.test(text);
  const hasDesktopWord = /\b(desktop|deskop|screen|obrazovk\w*|monitor)\b/.test(text);
  const hasStartWord = /\b(spust|spustit|sputil|pustim|pustit|pust|zapni|zapnout|start|startni|potrebuji|chci)\b/.test(text);

  return hasShareWord && hasDesktopWord && hasStartWord;
}

const defaultShareAutomationState = {
  debugPanelOpen: false,
  plannerSummary: '',
  confirmationRequest: null,
  lastAction: null,
  lastActionStatus: 'idle',
  lastActionMessage: '',
  debug: null,
};

const defaultScreenSharePickerState = {
  open: false,
  loading: false,
  sources: [],
  error: '',
  selectingId: '',
};

const baseNotifications = [];

function buildFallbackUpdateFeed(items, runtimeVersion = '0.1.0') {
  const first = items[0] || null;
  return {
    currentVersion: runtimeVersion || '0.1.0',
    latestVersion: first?.version || runtimeVersion || '0.1.0',
    publishedAt: first?.date || '',
    channel: 'stable',
    updateAvailable: false,
    downloadUrl: '',
    downloadStatus: 'none',
    readyToInstall: false,
    downloadedPath: '',
    autoDownloadSupported: false,
    entries: items,
  };
}

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

function toLocalFileUrl(filePath) {
  const normalized = String(filePath || '').trim().replace(/\\/g, '/');
  if (!normalized) return '';
  if (/^file:\/\//i.test(normalized)) return normalized;
  return encodeURI(`file:///${normalized.replace(/^\/+/, '')}`);
}

async function readLocalPreviewDataUrl(filePath) {
  const targetPath = String(filePath || '').trim();
  const api = window.lunaDesktop?.files;
  if (!targetPath || !api?.readAsDataUrl) return '';
  const result = await api.readAsDataUrl(targetPath).catch(() => null);
  return result?.ok && result?.dataUrl ? String(result.dataUrl) : '';
}

function mergeFloat32Chunks(chunks) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;
  chunks.forEach((chunk) => {
    merged.set(chunk, offset);
    offset += chunk.length;
  });
  return merged;
}

function downsampleFloat32Buffer(buffer, inputSampleRate, outputSampleRate = 16000) {
  if (inputSampleRate === outputSampleRate) return buffer;
  const ratio = inputSampleRate / outputSampleRate;
  const nextLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(nextLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let sum = 0;
    let count = 0;
    for (let index = offsetBuffer; index < nextOffsetBuffer && index < buffer.length; index += 1) {
      sum += buffer[index];
      count += 1;
    }
    result[offsetResult] = count ? sum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function encodePcm16Wav(samples, sampleRate = 16000) {
  const bytesPerSample = 2;
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
  const view = new DataView(buffer);

  const writeString = (offset, value) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * bytesPerSample, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, samples.length * bytesPerSample, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1, offset += 2) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  return new Blob([view], { type: 'audio/wav' });
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
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

function getLatestUserIntent(messageList) {
  const messages = Array.isArray(messageList) ? messageList : [];
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const candidate = messages[index];
    if (candidate?.role === 'user' && String(candidate?.content || '').trim()) {
      return String(candidate.content).trim();
    }
  }
  return '';
}

function buildActionKey(action) {
  if (!action?.type) return '';
  return JSON.stringify({
    type: action.type,
    target: action.target || '',
    args: action.args || {},
  });
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
  const [page, setPage] = useState(() => {
    const storedPage = window.localStorage.getItem(STORAGE_KEYS.page) || 'chat';
    if (storedPage === 'eyes') return 'chat';
    if (storedPage === 'applications') return 'settings';
    return storedPage;
  });
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
  const [observeModeEnabled, setObserveModeEnabled] = useState(false);
  const [pendingDesktopContext, setPendingDesktopContext] = useState(null);
  const [desktopObservation, setDesktopObservation] = useState(null);
  const [desktopPreviewUrl, setDesktopPreviewUrl] = useState('');
  const [screenShare, setScreenShare] = useState({
    active: false,
    label: '',
    stream: null,
    previewUrl: '',
    framePath: '',
    status: '',
    visionSummary: '',
    summaryStatus: 'idle',
    summaryStatusLabel: 'Ready',
    analyzing: false,
    frameCount: 0,
    lastFrameAt: 0,
  });
  const [status, setStatus] = useState('LunaAI desktop shell ready.');
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0, kind: 'chat', targetId: '', title: '', saved: false });
  const [appMeta, setAppMeta] = useState(fallbackMeta);
  const [signedInAs, setSignedInAs] = useState(() => window.localStorage.getItem('lunaai-signed-in') || '');
  const [seenUpdateVersion, setSeenUpdateVersion] = useState(() => window.localStorage.getItem(STORAGE_KEYS.seenUpdateVersion) || '');
  const [updateFeed, setUpdateFeed] = useState(() => buildFallbackUpdateFeed(updates, fallbackMeta.version));
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [pendingGenerationType, setPendingGenerationType] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectType, setProjectType] = useState('investing');
  const [chatBusy, setChatBusy] = useState(false);
  const [eyesBusy, setEyesBusy] = useState(false);
  const [micRecording, setMicRecording] = useState(false);
  const [speechPlaying, setSpeechPlaying] = useState(false);
  const [voiceLoopEnabled, setVoiceLoopEnabled] = useState(false);
  const [assistantModeEnabled, setAssistantModeEnabled] = useState(false);
  const [thinkingState, setThinkingState] = useState(idleThinkingState);
  const [revealingMessage, setRevealingMessage] = useState(null);
  const [pendingAction, setPendingAction] = useState({ active: false, title: '' });
  const [actionEnginePending, setActionEnginePending] = useState({ active: false, title: '' });
  const [shareAutomation, setShareAutomation] = useState(defaultShareAutomationState);
  const [screenSharePicker, setScreenSharePicker] = useState(defaultScreenSharePickerState);
  const messages = currentChatId ? chatMessages[currentChatId] || [] : [];
  const revealTimerRef = useRef(null);
  const revealActiveRef = useRef(false);
  const screenShareStreamRef = useRef(null);
  const screenShareIntervalRef = useRef(null);
  const screenShareVideoRef = useRef(null);
  const screenShareCanvasRef = useRef(null);
  const latestScreenSharePathRef = useRef('');
  const screenShareAnalysisBusyRef = useRef(false);
  const screenShareLastAnalyzedAtRef = useRef(0);
  const lastShareActionKeyRef = useRef('');
  const lastShareConfirmationKeyRef = useRef('');
  const announcedUpdateVersionRef = useRef('');
  const screenShareStateRef = useRef(screenShare);
  const shareAutomationRef = useRef(shareAutomation);
  const messagesRef = useRef(messages);
  const micSessionRef = useRef(null);
  const speechPlaybackRef = useRef(null);
  const voiceLoopRef = useRef(false);
  const taskPlanner = useMemo(() => createTaskPlanner(), []);

  const profileName = signedInAs ? signedInAs.split('@')[0] : 'Sakurai Haise';
  const notifications = useMemo(() => {
    const items = [...baseNotifications];
    const updateReady = Boolean(updateFeed?.readyToInstall);
    if (updateFeed?.updateAvailable && updateFeed.latestVersion && (updateReady || updateFeed.latestVersion !== seenUpdateVersion)) {
      items.unshift({
        id: `update-${updateFeed.latestVersion}`,
        kind: 'update',
        label: 'Update',
        title: updateReady ? `Nov\u00e1 verze ${updateFeed.latestVersion} je p\u0159ipraven\u00e1` : `Nov\u00fd update ${updateFeed.latestVersion}`,
        detail: updateReady
          ? 'Update je sta\u017een\u00fd. Kliknut\u00edm otev\u0159e\u0161 Restart & Update.'
          : updateFeed.downloadStatus === 'missing-url'
            ? 'Update je dostupn\u00fd, ale release manifest zat\u00edm nem\u00e1 downloadUrl.'
            : 'LunaAI p\u0159ipravuje update na pozad\u00ed.',
        version: updateFeed.latestVersion,
      });
    }
    return items;
  }, [seenUpdateVersion, updateFeed]);
  const notificationCount = notifications.length;
  const pageData = sectionTitles[page] || sectionTitles.chat;

  useEffect(() => () => {
    if (attachment?.previewUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(attachment.previewUrl);
    }
  }, [attachment]);

  useEffect(() => {
    screenShareStateRef.current = screenShare;
  }, [screenShare]);

  useEffect(() => {
    shareAutomationRef.current = shareAutomation;
  }, [shareAutomation]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    voiceLoopRef.current = voiceLoopEnabled;
  }, [voiceLoopEnabled]);

  useEffect(() => () => {
    if (screenShareIntervalRef.current) {
      window.clearInterval(screenShareIntervalRef.current);
      screenShareIntervalRef.current = null;
    }
    const currentStream = screenShareStreamRef.current;
    if (currentStream) {
      currentStream.getTracks().forEach((track) => track.stop());
      screenShareStreamRef.current = null;
    }
  }, []);

  useEffect(() => {
    const screenshotPath = String(desktopObservation?.screenshot_path || '').trim();
    const api = window.lunaDesktop?.files;

    if (!screenshotPath || !api?.readAsDataUrl) {
      setDesktopPreviewUrl('');
      return undefined;
    }

    let cancelled = false;

    async function loadPreview() {
      const result = await api.readAsDataUrl(screenshotPath).catch(() => null);
      if (cancelled) return;
      if (result?.ok && result?.dataUrl) {
        setDesktopPreviewUrl(String(result.dataUrl));
      } else {
        setDesktopPreviewUrl('');
      }
    }

    loadPreview();

    return () => {
      cancelled = true;
    };
  }, [desktopObservation?.screenshot_path]);

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
    window.localStorage.setItem(STORAGE_KEYS.seenUpdateVersion, seenUpdateVersion);
  }, [seenUpdateVersion]);

  useEffect(() => {
    if (page === 'updates' && updateFeed?.latestVersion) {
      setSeenUpdateVersion(String(updateFeed.latestVersion));
    }
  }, [page, updateFeed?.latestVersion]);

  useEffect(() => {
    const latestVersion = String(updateFeed?.latestVersion || '');
    const updateReady = Boolean(updateFeed?.readyToInstall);
    if (!updateFeed?.updateAvailable || !latestVersion || (!updateReady && latestVersion === seenUpdateVersion)) {
      return;
    }
    const announceKey = `${latestVersion}:${updateReady ? 'ready' : 'available'}`;
    if (announcedUpdateVersionRef.current === announceKey) {
      return;
    }

    announcedUpdateVersionRef.current = announceKey;
    setStatus(
      updateReady
        ? `Nov\u00e1 verze ${latestVersion} je p\u0159ipraven\u00e1. M\u016f\u017ee\u0161 d\u00e1t Restart & Update.`
        : `Je tu nov\u00fd update ${latestVersion}. LunaAI ho p\u0159ipravuje na pozad\u00ed.`
    );
  }, [seenUpdateVersion, updateFeed?.latestVersion, updateFeed?.readyToInstall, updateFeed?.updateAvailable]);

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
    if (typeof result?.observeModeEnabled === 'boolean') {
      setObserveModeEnabled(result.observeModeEnabled);
    }
    if (result?.lastObservation && typeof result.lastObservation === 'object') {
      setDesktopObservation(result.lastObservation);
    }
    if (result?.observation && typeof result.observation === 'object') {
      setDesktopObservation(result.observation);
    }
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

  function applyActionEnginePendingState(result) {
    const pending = result?.pendingAction || null;
    if (!pending?.active) {
      setActionEnginePending({ active: false, title: '' });
      return false;
    }

    const action = pending.action || {};
    const title = pending.title
      || `${action.type || 'Action Engine'}${action.target ? ` -> ${action.target}` : ''}`;
    setActionEnginePending({
      active: true,
      title,
      source: 'action-engine',
      message: pending.message || '',
    });
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
        if (voiceLoopRef.current) {
          handleTextToSpeech(normalizedText);
        }
        return;
      }

      revealTimerRef.current = window.requestAnimationFrame(step);
    };

    revealTimerRef.current = window.requestAnimationFrame(step);
  }

  function applyBackendChatState(result) {
    return applyChatState(result);
  }

  function clearScreenShareLoop() {
    if (screenShareIntervalRef.current) {
      window.clearInterval(screenShareIntervalRef.current);
      screenShareIntervalRef.current = null;
    }
  }

  function resetShareAutomationState() {
    lastShareActionKeyRef.current = '';
    lastShareConfirmationKeyRef.current = '';
    setShareAutomation(defaultShareAutomationState);
  }

  function stopScreenShare({ message } = {}) {
    clearScreenShareLoop();
    const currentStream = screenShareStreamRef.current;
    if (currentStream) {
      currentStream.getTracks().forEach((track) => track.stop());
      screenShareStreamRef.current = null;
    }
    if (screenShareVideoRef.current) {
      screenShareVideoRef.current.srcObject = null;
    }
    latestScreenSharePathRef.current = '';
    screenShareAnalysisBusyRef.current = false;
    screenShareLastAnalyzedAtRef.current = 0;
    resetShareAutomationState();
    const stoppedShareState = {
      active: false,
      label: '',
      stream: null,
      previewUrl: '',
      framePath: '',
      status: '',
      visionSummary: '',
      summaryStatus: 'idle',
      summaryStatusLabel: 'Ready',
      analyzing: false,
      frameCount: 0,
      lastFrameAt: 0,
    };
    screenShareStateRef.current = stoppedShareState;
    setScreenShare(stoppedShareState);
    if (message) {
      setStatus(message);
    }
  }

  function closeShareDebugPanel() {
    lastShareActionKeyRef.current = '';
    setShareAutomation((current) => ({
      ...current,
      debugPanelOpen: false,
      lastActionStatus: current.lastActionStatus === 'idle' ? 'idle' : 'closed',
      lastActionMessage: 'Interní debug panel byl zavřený.',
    }));
  }

  function ensureScreenShareNodes() {
    if (!screenShareVideoRef.current) {
      const video = document.createElement('video');
      video.autoplay = true;
      video.muted = true;
      video.playsInline = true;
      screenShareVideoRef.current = video;
    }
    if (!screenShareCanvasRef.current) {
      screenShareCanvasRef.current = document.createElement('canvas');
    }
    return {
      video: screenShareVideoRef.current,
      canvas: screenShareCanvasRef.current,
    };
  }

  async function waitForSharedVideoFrame(video, timeoutMs = 900) {
    if (!video) return false;
    if (video.videoWidth > 0 && video.videoHeight > 0 && video.readyState >= 2) {
      return true;
    }

    await video.play?.().catch(() => {});

    return new Promise((resolve) => {
      let settled = false;
      const finish = () => {
        if (settled) return;
        settled = true;
        video.removeEventListener('loadedmetadata', finish);
        video.removeEventListener('loadeddata', finish);
        video.removeEventListener('playing', finish);
        window.clearTimeout(timer);
        resolve(video.videoWidth > 0 && video.videoHeight > 0);
      };
      const timer = window.setTimeout(finish, timeoutMs);

      video.addEventListener('loadedmetadata', finish, { once: true });
      video.addEventListener('loadeddata', finish, { once: true });
      video.addEventListener('playing', finish, { once: true });
      if (typeof video.requestVideoFrameCallback === 'function') {
        video.requestVideoFrameCallback(finish);
      }
    });
  }

  async function persistScreenShareDataUrl(dataUrl, { status = '' } = {}) {
    const api = window.lunaDesktop?.files;
    const value = String(dataUrl || '').trim();
    if (!api?.writeTempDataUrl || !value.startsWith('data:image/')) {
      return '';
    }

    const result = await api.writeTempDataUrl({
      dataUrl: value,
      extension: value.startsWith('data:image/webp') ? 'webp' : (value.startsWith('data:image/png') ? 'png' : 'jpg'),
      previousPath: latestScreenSharePathRef.current,
    }).catch(() => null);

    if (!result?.ok || !result?.path) {
      return '';
    }

    const nextPath = String(result.path);
    const nextFrameAt = Date.now();
    latestScreenSharePathRef.current = nextPath;
    const nextStatus = status || 'Desktop share je aktivní. Luna a Xeno mají uložený poslední dostupný frame.';

    setScreenShare((current) => ({
      ...current,
      active: true,
      previewUrl: value,
      framePath: nextPath,
      status: nextStatus,
      lastFrameAt: nextFrameAt,
    }));
    screenShareStateRef.current = {
      ...screenShareStateRef.current,
      active: true,
      previewUrl: value,
      framePath: nextPath,
      status: nextStatus,
      lastFrameAt: nextFrameAt,
    };
    return nextPath;
  }

  async function captureSharedDesktopFrame() {
    const currentStream = screenShareStreamRef.current;
    const api = window.lunaDesktop?.files;
    if (!currentStream || !api?.writeTempDataUrl) return '';

    const { video, canvas } = ensureScreenShareNodes();
    await waitForSharedVideoFrame(video);
    if (!video.videoWidth || !video.videoHeight) {
      return '';
    }

    const targetWidth = Math.min(video.videoWidth, 1440);
    const scale = targetWidth / video.videoWidth;
    canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(video.videoHeight * scale));

    const context = canvas.getContext('2d', { alpha: false });
    if (!context) return '';

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.78);
    const savedPath = await persistScreenShareDataUrl(dataUrl, {
      status: 'Desktop share je aktivní. Luna a Xeno čtou průběžně obnovované framy ze sdílené obrazovky.',
    });
    if (!savedPath) return '';
    setScreenShare((current) => ({
      ...current,
      active: true,
      stream: current.stream,
      previewUrl: dataUrl,
      framePath: savedPath,
      status: 'Desktop share je aktivní. Luna a Xeno čtou průběžně obnovované framy ze sdílené obrazovky.',
      frameCount: Number(current.frameCount || 0) + 1,
      lastFrameAt: Date.now(),
    }));
    screenShareStateRef.current = {
      ...screenShareStateRef.current,
      active: true,
      previewUrl: dataUrl,
      framePath: savedPath,
      frameCount: Number(screenShareStateRef.current?.frameCount || 0) + 1,
      lastFrameAt: Date.now(),
    };
    return savedPath;
  }

  async function ensureLatestSharedFrameForMessage() {
    const currentShare = screenShareStateRef.current || screenShare;
    let framePath = await captureSharedDesktopFrame();
    if (framePath) return framePath;

    await wait(160);
    framePath = await captureSharedDesktopFrame();
    if (framePath) return framePath;

    const fallbackPath = latestScreenSharePathRef.current
      || currentShare?.framePath
      || screenShare.framePath
      || '';
    const fallbackFrameAt = Number(currentShare?.lastFrameAt || screenShare.lastFrameAt || 0);
    const fallbackIsFresh = fallbackFrameAt > 0 && (Date.now() - fallbackFrameAt < 15000);
    if (fallbackPath && fallbackIsFresh) {
      return fallbackPath;
    }

    const previewUrl = currentShare?.previewUrl || screenShare.previewUrl || '';
    return persistScreenShareDataUrl(previewUrl, {
      status: 'Desktop share je aktivní. Používám poslední dostupný náhled jako frame pro AI.',
    });
  }

  async function executeSharePlan({ framePath, visionSummary }) {
    const actionApi = window.lunaDesktop?.actionEngine;
    const currentShare = screenShareStateRef.current;
    const currentAutomation = shareAutomationRef.current;
    const userIntent = getLatestUserIntent(messagesRef.current);
    const plannerResult = taskPlanner.plan({
      userIntent,
      visionResult: {
        description: visionSummary,
      },
      shareState: {
        active: currentShare.active,
        label: currentShare.label,
        debugPanelOpen: currentAutomation.debugPanelOpen,
      },
    });

    setShareAutomation((current) => ({
      ...current,
      plannerSummary: plannerResult.summary,
      confirmationRequest: plannerResult.confirmationRequest || null,
      lastAction: plannerResult.action || null,
      debug: plannerResult.debug,
    }));

    const nextAction = plannerResult.action;
    if (!nextAction || !actionApi?.execute) {
      if (!nextAction) {
        lastShareActionKeyRef.current = '';
        lastShareConfirmationKeyRef.current = '';
      }
      return;
    }

    const actionKey = buildActionKey(nextAction);
    if (!actionKey) return;

    if (nextAction.requiresConfirmation) {
      if (lastShareConfirmationKeyRef.current === actionKey) return;
      lastShareConfirmationKeyRef.current = actionKey;
    } else if (lastShareActionKeyRef.current === actionKey) {
      return;
    } else {
      lastShareActionKeyRef.current = actionKey;
    }

    const executionResult = await actionApi.execute({
      action: nextAction,
      context: {
        source: 'screen-share',
        framePath,
        visionSummary,
        plannerSummary: plannerResult.summary,
        userIntent,
      },
    }).catch(() => null);

    if (!executionResult) {
      setShareAutomation((current) => ({
        ...current,
        lastActionStatus: 'error',
        lastActionMessage: 'Action engine nevratil odpoved.',
      }));
      return;
    }

    if (executionResult.confirmationRequest) {
      applyActionEnginePendingState(executionResult);
      setShareAutomation((current) => ({
        ...current,
        confirmationRequest: executionResult.confirmationRequest,
        lastActionStatus: executionResult.status || 'confirmation_required',
        lastActionMessage: executionResult.message || 'Akce ceka na potvrzeni.',
      }));
      return;
    }

    applyActionEnginePendingState(executionResult);
    setShareAutomation((current) => ({
      ...current,
      confirmationRequest: null,
      lastActionStatus: executionResult.status || (executionResult.executed ? 'executed' : 'idle'),
      lastActionMessage: executionResult.message || current.lastActionMessage,
    }));
  }

  async function refreshScreenShareVisionSummary(framePath, { force = false } = {}) {
    const api = window.lunaDesktop?.luna;
    const targetPath = String(framePath || '').trim();
    if (!targetPath || !api?.analyzeVisual) return '';

    const now = Date.now();
    if (!force && screenShareAnalysisBusyRef.current) return '';
    if (!force && now - screenShareLastAnalyzedAtRef.current < screenShareVisionIntervalMs) return '';

    screenShareAnalysisBusyRef.current = true;
    setScreenShare((current) => ({
      ...current,
      analyzing: true,
      summaryStatus: current.visionSummary ? current.summaryStatus : 'working',
      summaryStatusLabel: 'Reading',
    }));

      try {
        const result = await api.analyzeVisual({
          filePaths: [targetPath],
          query: 'Describe only this exact currently shared desktop frame for LunaAI and Xeno. Focus on the active app, visible UI, clearly readable text, and what the user appears to be doing right now. If something is unclear, say it is unclear. Do not infer previous frames, hidden windows, or older screen states.',
        });
        const summary = String(result?.summary || '').trim();
        screenShareLastAnalyzedAtRef.current = Date.now();
        setScreenShare((current) => ({
          ...current,
        analyzing: false,
        visionSummary: summary || current.visionSummary || 'Vision model did not return a useful summary.',
        summaryStatus: summary ? 'ok' : 'warning',
        summaryStatusLabel: summary ? 'Live' : 'No summary',
      }));
        if (summary) {
          await executeSharePlan({
            framePath: targetPath,
            visionSummary: summary,
          });
        }
        return summary;
      } catch {
        setScreenShare((current) => ({
          ...current,
          analyzing: false,
          summaryStatus: 'error',
          summaryStatusLabel: 'Unavailable',
          visionSummary: current.visionSummary || 'Vision summary is temporarily unavailable.',
        }));
        return '';
      } finally {
        screenShareAnalysisBusyRef.current = false;
      }
    }

  async function startScreenShare() {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      const message = 'Sdílení obrazovky v tomhle prostředí není dostupné.';
      setStatus(message);
      setScreenSharePicker((current) => ({ ...current, loading: false, selectingId: '', error: message }));
      return false;
    }

    stopScreenShare({});

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          frameRate: { ideal: 8, max: 12 },
        },
        audio: false,
      });

      const track = stream.getVideoTracks()[0];
      if (!track) {
        const message = 'Sdílení obrazovky nevrátilo video stopu.';
        stopScreenShare({ message });
        setScreenSharePicker((current) => ({
          ...current,
          loading: false,
          selectingId: '',
          error: message,
        }));
        return false;
      }

      track.addEventListener('ended', () => {
        stopScreenShare({ message: 'Sdílení obrazovky bylo ukončeno.' });
      });

      const { video } = ensureScreenShareNodes();
      video.srcObject = stream;
      if (video.readyState < 1) {
        await new Promise((resolve) => {
          const handleLoaded = () => {
            video.removeEventListener('loadedmetadata', handleLoaded);
            resolve();
          };
          video.addEventListener('loadedmetadata', handleLoaded);
        });
      }
      await video.play().catch(() => {});

      screenShareStreamRef.current = stream;
      const startedShareState = {
        active: true,
        label: track.label || 'Desktop share',
        stream,
        previewUrl: '',
        framePath: '',
        status: 'Desktop share běží. Připravuju první frame a vision shrnutí.',
        visionSummary: '',
        summaryStatus: 'working',
        summaryStatusLabel: 'Starting',
        analyzing: false,
        frameCount: 0,
        lastFrameAt: 0,
      };
      screenShareStateRef.current = startedShareState;
      setScreenShare(startedShareState);

      const firstFramePath = await captureSharedDesktopFrame();
      if (firstFramePath) {
        await refreshScreenShareVisionSummary(firstFramePath, { force: true });
      }

      clearScreenShareLoop();
      screenShareIntervalRef.current = window.setInterval(() => {
        captureSharedDesktopFrame().then((nextFramePath) => {
          if (nextFramePath) {
            refreshScreenShareVisionSummary(nextFramePath);
          }
        });
      }, screenShareFrameIntervalMs);

      setStatus('Desktop share je aktivní. Luna a Xeno čtou obnovované framy ze sdílené obrazovky.');
      return true;
    } catch (error) {
      const message = String(error?.message || '').trim()
        ? `Sdílení obrazovky se nespustilo: ${String(error.message).trim()}`
        : 'Sdílení obrazovky se nespustilo.';
      stopScreenShare({ message });
      setScreenSharePicker((current) => ({ ...current, loading: false, selectingId: '', error: message }));
      return false;
    }
  }

  async function refreshScreenShareSources() {
    const api = window.lunaDesktop?.screenShare;
    if (!api?.listSources) {
      const message = 'Vyber zdroje sdileni v tomhle buildu jeste neni dostupny.';
      setScreenSharePicker({
        ...defaultScreenSharePickerState,
        open: true,
        error: message,
      });
      setStatus(message);
      return;
    }

    setStatus('Nacitam zdroje pro desktop share...');
    setScreenSharePicker((current) => ({
      ...current,
      open: true,
      loading: true,
      error: '',
      selectingId: '',
    }));

    try {
      const result = await api.listSources();
      const sources = Array.isArray(result?.sources) ? result.sources : [];
      const error = result?.ok === false ? String(result.message || 'Nepodarilo se nacist zdroje sdileni.') : '';
      setScreenSharePicker({
        open: true,
        loading: false,
        sources,
        error,
        selectingId: '',
      });
      if (error) {
        setStatus(error);
      } else if (sources.length === 0) {
        setStatus('Nebyl nalezen zadny zdroj pro sdileni. Otevri jine okno nebo zkus cely monitor.');
      } else {
        setStatus('Vyber zdroj, ktery chces sdilet.');
      }
    } catch (error) {
      const message = String(error?.message || 'Nepodarilo se nacist zdroje sdileni.');
      setScreenSharePicker({
        ...defaultScreenSharePickerState,
        open: true,
        error: message,
      });
      setStatus(message);
    }
  }

  function closeScreenSharePicker() {
    setScreenSharePicker(defaultScreenSharePickerState);
  }

  async function handleSelectScreenShareSource(source) {
    const sourceId = String(source?.id || '').trim();
    const sourceName = String(source?.name || '').trim();
    const api = window.lunaDesktop?.screenShare;

    if (!sourceId || !api?.selectSource) {
      const message = 'Vybrany zdroj nejde predat do Electron capture vrstvy.';
      setScreenSharePicker((current) => ({
        ...current,
        error: message,
      }));
      setStatus(message);
      return;
    }

    setStatus(`Připravuju sdílení: ${sourceName || 'vybraný zdroj'}.`);
    setScreenSharePicker((current) => ({
      ...current,
      loading: true,
      selectingId: sourceId,
      error: '',
    }));

    try {
      const result = await api.selectSource(sourceId);
      if (!result?.ok) {
        const message = String(result?.message || 'Zdroj se nepodarilo pripravit.');
        setScreenSharePicker((current) => ({
          ...current,
          loading: false,
          selectingId: '',
          error: message,
        }));
        setStatus(message);
        return;
      }

      const started = await startScreenShare();
      if (started) {
        closeScreenSharePicker();
      }
    } catch (error) {
      const message = String(error?.message || 'Sdílení obrazovky se nepodařilo spustit.');
      setScreenSharePicker((current) => ({
        ...current,
        loading: false,
        selectingId: '',
        error: message,
      }));
      setStatus(message);
    }
  }

  async function requestDesktopObservation(includeScreenshot = false, { silent = false } = {}) {
    const api = window.lunaDesktop?.luna;
    if (!api?.observeDesktop) {
      if (!silent) {
        setStatus('Desktop observe works only inside the Electron desktop shell.');
      }
      return null;
    }

    try {
      setEyesBusy(true);
      const result = await api.observeDesktop({ includeScreenshot });
      applyBackendChatState(result);

      const context = String(result?.context || '').trim();
      if (context) {
        setPendingDesktopContext({
          context,
          includeScreenshot,
          summary: String(result?.summary || '').trim(),
        });
      }

      const screenshotPath = String(result?.observation?.screenshot_path || '').trim();
      if (includeScreenshot && screenshotPath) {
        const previewDataUrl = await readLocalPreviewDataUrl(screenshotPath);
        setAttachment((current) => {
          if (current?.previewUrl?.startsWith('blob:')) URL.revokeObjectURL(current.previewUrl);
          return {
            name: screenshotPath.split(/[/\\]/).pop() || 'desktop.png',
            type: 'image/png',
            path: screenshotPath,
            source: 'desktop-capture',
            previewUrl: previewDataUrl || toLocalFileUrl(screenshotPath),
          };
        });
      }

      if (!silent) {
        const detail = String(result?.observation?.detail || '').trim();
        if (includeScreenshot && !screenshotPath && detail) {
          setStatus(detail);
        } else {
          setStatus(includeScreenshot
            ? 'Aktualni obrazovka je pripravena jako sdileny kontext pro dalsi zpravu.'
            : 'Desktop context jsem nacetla pro dalsi zpravu.');
        }
      }
      return result;
    } catch {
      if (!silent) {
        setStatus(includeScreenshot ? 'Screenshot capture selhal.' : 'Desktop observation failed.');
      }
      return null;
    } finally {
      setEyesBusy(false);
    }
  }

  async function updateObserveMode(nextEnabled, { silent = false } = {}) {
    const api = window.lunaDesktop?.luna;
    if (!api?.setObserveMode) {
      if (!silent) {
        setStatus('Observe mode works only inside the Electron desktop shell.');
      }
      return null;
    }

    try {
      setEyesBusy(true);
      const result = await api.setObserveMode(nextEnabled);
      applyBackendChatState(result);
      let initialObservation = null;
      if (nextEnabled) {
        initialObservation = await requestDesktopObservation(true, { silent: true });
      }
      if (!silent) {
        const screenshotPath = String(initialObservation?.observation?.screenshot_path || '').trim();
        if (nextEnabled && screenshotPath) {
          setStatus('Observe mode je zapnuty a aktualni obrazovka je nactena.');
        } else {
          setStatus(String(result?.response || (nextEnabled ? 'Observe mode zapnuty.' : 'Observe mode vypnuty.')));
        }
      }
      return result;
    } catch {
      if (!silent) {
        setStatus('Observe mode change failed.');
      }
      return null;
    } finally {
      setEyesBusy(false);
    }
  }

  async function startAssistantMode() {
    setAssistantModeEnabled(true);
    setPage('chat');
    setStatus('Assistant mode se zapina: voice, vision a agent se spojuji do jednoho rezimu.');
    await window.lunaDesktop?.window?.showAssistantOverlay?.();

    if (!observeModeEnabled) {
      await updateObserveMode(true, { silent: true });
    }

    if (!voiceLoopRef.current) {
      voiceLoopRef.current = true;
      setVoiceLoopEnabled(true);
      if (!micSessionRef.current) {
        window.setTimeout(() => startMicrophoneCapture(), 0);
      }
    }

    if (!screenShareStateRef.current?.active) {
      await refreshScreenShareSources();
      setStatus('Assistant mode bezi. Vyber obrazovku nebo okno, ktere maji Luna a Xeno sledovat.');
    } else {
      setStatus('Assistant mode bezi. Luna posloucha, Xeno drzi plan a vision cte sdilenou obrazovku.');
    }
  }

  async function stopAssistantMode() {
    setAssistantModeEnabled(false);
    await window.lunaDesktop?.window?.hideAssistantOverlay?.();
    voiceLoopRef.current = false;
    setVoiceLoopEnabled(false);
    if (micSessionRef.current) {
      window.setTimeout(() => stopMicrophoneCapture(), 0);
    }
    stopSpeechPlayback();
    if (observeModeEnabled) {
      await updateObserveMode(false, { silent: true });
    }
    setStatus('Assistant mode vypnuty. Luna zustava v beznem chat rezimu.');
  }

  function toggleAssistantMode() {
    if (assistantModeEnabled) {
      stopAssistantMode();
    } else {
      startAssistantMode();
    }
  }

  useEffect(() => () => {
    clearRevealTimer();
    revealActiveRef.current = false;
  }, []);

  useEffect(() => {
    const api = window.lunaDesktop?.updates;

    async function loadUpdateFeed() {
      if (!api?.getFeed) {
        setUpdateFeed(buildFallbackUpdateFeed(updates, appMeta.version));
        return;
      }

      try {
        const nextFeed = api.prepare ? await api.prepare() : await api.getFeed();
        setUpdateFeed({
          ...buildFallbackUpdateFeed(updates, appMeta.version),
          ...nextFeed,
          entries: Array.isArray(nextFeed?.entries) && nextFeed.entries.length ? nextFeed.entries : updates,
          currentVersion: nextFeed?.currentVersion || appMeta.version || '0.1.0',
        });
      } catch {
        setUpdateFeed(buildFallbackUpdateFeed(updates, appMeta.version));
      }
    }

    loadUpdateFeed();
    const intervalId = window.setInterval(loadUpdateFeed, 300000);
    return () => window.clearInterval(intervalId);
  }, [appMeta.version]);

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
    const api = window.lunaDesktop?.actionEngine;
    if (!api?.getPending) return;

    let cancelled = false;

    async function loadActionEnginePending() {
      const result = await api.getPending().catch(() => null);
      if (!cancelled && result?.ok) {
        applyActionEnginePendingState(result);
      }
    }

    loadActionEnginePending();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const api = window.lunaDesktop?.luna;
    if (!api?.observeDesktop || page !== 'eyes' || !observeModeEnabled) return undefined;

    let cancelled = false;

    const refresh = async (includeScreenshot = false) => {
      const result = await api.observeDesktop({ includeScreenshot }).catch(() => null);
      if (cancelled || !result?.ok) return;
      applyBackendChatState(result);
    };

    refresh(true);
    const intervalId = window.setInterval(() => refresh(true), 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [page, observeModeEnabled]);

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

  useEffect(() => {
    const actionApi = window.lunaDesktop?.actionEngine;
    if (!actionApi?.onInternalAction) return undefined;

    return actionApi.onInternalAction((payload) => {
      const action = payload?.action;
      if (!action?.target) return;

      switch (action.target) {
        case 'open-share-debug-panel':
          setShareAutomation((current) => ({
            ...current,
            debugPanelOpen: true,
            confirmationRequest: null,
            lastActionStatus: 'executed',
            lastActionMessage: 'Interní debug panel je otevřený.',
          }));
          setStatus('Otevírám interní debug panel pro share workflow.');
          break;
        case 'close-share-debug-panel':
          closeShareDebugPanel();
          setStatus('Interní debug panel je zavřený.');
          break;
        case 'start-share-desktop':
          refreshScreenShareSources();
          break;
        case 'stop-share-desktop':
          stopScreenShare({ message: 'Desktop share byla zastavena interní akcí.' });
          break;
        case 'chat':
        case 'projects':
        case 'updates':
        case 'gallery':
        case 'friends':
        case 'settings':
          setPage(action.target);
          setStatus(`Přepínám interní panel na ${action.target}.`);
          break;
        default:
          break;
      }
    });
  }, []);

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

  async function handleSend(overrideText = '', options = {}) {
    const safeOverrideText = typeof overrideText === 'string' ? overrideText : '';
    const sendOptions = options && typeof options === 'object' ? options : {};
    const text = normalizeTransportText(safeOverrideText || composer).trim();
    if ((!text && !attachment?.name) || chatBusy) return;

    const api = window.lunaDesktop?.luna;
    const activeChatId = ensureActiveChat();
    const normalizedAttachmentName = normalizeTransportText(attachment?.name || '');
    const baseText = text || 'Attachment prepared for LunaAI.';
    const decoratedText = normalizedAttachmentName ? `${baseText}

[Attached file: ${normalizedAttachmentName}]` : baseText;
    let latestSharedFramePath = '';
    let latestSharedFrameSummary = '';

    if (isStartDesktopShareIntent(baseText)) {
      appendMessages(activeChatId, [
        { id: `user-${Date.now()}`, role: 'user', author: 'You', content: decoratedText },
        {
          id: `assistant-${Date.now() + 1}`,
          role: 'assistant',
          author: 'Luna',
          content: screenShare.active
            ? 'Luna: Desktop share už běží. Vpravo vidíš živý náhled a Luna/Xeno čtou nové framy. 👀'
            : 'Luna: Jasně, otevírám výběr zdroje pro Desktop share. Vyber monitor nebo okno a já ho začnu číst jako živý vizuální kontext. 👀',
        },
      ]);
      setComposer('');
      setAttachment(null);
      setPendingDesktopContext(null);
      setPendingGenerationType('');
      setPage('chat');
      if (!screenShare.active) {
        refreshScreenShareSources();
      } else {
        setStatus('Desktop share už běží.');
      }
      return;
    }

    const currentShareState = screenShareStateRef.current || screenShare;
    const shareIsActive = Boolean(currentShareState?.active || screenShareStreamRef.current);
    if (shareIsActive) {
      latestSharedFramePath = await ensureLatestSharedFrameForMessage();
      const fallbackFramePath = latestScreenSharePathRef.current
        || currentShareState?.framePath
        || screenShare.framePath
        || '';
      const shareFrameIsFresh = Number(currentShareState?.lastFrameAt || screenShare.lastFrameAt || 0) > 0
        && (Date.now() - Number(currentShareState?.lastFrameAt || screenShare.lastFrameAt || 0) < 5000);
      if (!latestSharedFramePath && (fallbackFramePath || shareFrameIsFresh)) {
        latestSharedFramePath = fallbackFramePath;
      }
      if (latestSharedFramePath) {
        latestSharedFrameSummary = await refreshScreenShareVisionSummary(latestSharedFramePath, { force: true });
        if (!latestSharedFrameSummary) {
          latestSharedFrameSummary = currentShareState?.visionSummary || screenShare.visionSummary || '';
        }
      }
    }

    const filePaths = [
      ...(attachment?.path ? [attachment.path] : []),
      ...(latestSharedFramePath ? [latestSharedFramePath] : []),
    ];
    const extraContext = [
      sendOptions.source === 'voice'
        ? 'Input source: voice. Voice mode: user is speaking conversationally. Reply naturally for speech output.'
        : '',
      String(pendingDesktopContext?.context || '').trim(),
      shareIsActive
        ? `Active desktop share: ${currentShareState?.label || screenShare.label || 'desktop stream'}. ${latestSharedFramePath ? 'The newest shared frame attached to this message is the current on-screen truth.' : 'The share preview is live, but no frame file was available for this exact message yet.'} It overrides any older screenshots or older screen descriptions in this chat. Answer from the newest shared frame when a frame is attached; if no frame is attached, say the share preview is active but the current frame was not delivered yet.`
        : '',
      latestSharedFrameSummary
        ? `Current live vision summary from the newest shared frame:\n${latestSharedFrameSummary}`
        : '',
    ].filter(Boolean).join('\n\n');
    const mediaType = inferGeneratedMediaType(baseText, pendingGenerationType);

    if (api?.sendMessage) {
      setChatBusy(true);
      setThinkingState(createThinkingState(baseText));
      try {
        const result = await api.sendMessage({
          chatId: activeChatId,
          text: decoratedText,
          filePaths,
          extraContext,
          forceActionExecution: sendOptions.source === 'voice' && shouldForceVoiceActionExecution(baseText),
        });
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
    setPendingDesktopContext(null);
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
    const lunaApi = window.lunaDesktop?.luna;
    const actionApi = window.lunaDesktop?.actionEngine;

    if (!pendingAction?.active && actionEnginePending?.active && actionApi) {
      setChatBusy(true);
      setThinkingState({ visible: true, lunaActive: true, xenoActive: true });
      try {
        const result = kind === 'confirm'
          ? await actionApi.confirmPending()
          : await actionApi.cancelPending();
        applyActionEnginePendingState(result);
        setShareAutomation((current) => ({
          ...current,
          confirmationRequest: null,
          lastActionStatus: result?.status || (kind === 'confirm' ? 'executed' : 'cancelled'),
          lastActionMessage: result?.message || (kind === 'confirm' ? 'Action Engine request executed.' : 'Action Engine request cancelled.'),
        }));
        setStatus(result?.message || (kind === 'confirm' ? 'Action Engine request executed.' : 'Action Engine request cancelled.'));
      } catch {
        setStatus(kind === 'confirm' ? 'Action Engine confirmation failed.' : 'Action Engine cancellation failed.');
      } finally {
        setChatBusy(false);
        if (!revealActiveRef.current) {
          setThinkingState((current) => (current.visible ? idleThinkingState : current));
        }
      }
      return;
    }

    if (!lunaApi) return;

    setChatBusy(true);
    setThinkingState({ visible: true, lunaActive: true, xenoActive: false });
    try {
      const result = kind === 'confirm'
        ? await lunaApi.confirmPendingAction()
        : await lunaApi.cancelPendingAction();
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
      if (action === 'hide-to-tray' && api.hideToTray) {
        const result = await api.hideToTray();
        setStatus(result?.message || 'LunaAI is still running in the tray.');
      }
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

  function handleNotificationSelect(item) {
    if (!item) return;

    if (item.kind === 'update') {
      setSeenUpdateVersion(String(item.version || updateFeed?.latestVersion || ''));
      setPage('updates');
      setNotificationsOpen(false);
      setStatus(`Nov\u00e1 verze ${item.version || updateFeed?.latestVersion || ''} je p\u0159ipraven\u00e1 v Updates.`);
      return;
    }

    setNotificationsOpen(false);
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

  async function startMicrophoneCapture() {
    const fileApi = window.lunaDesktop?.files;
    const lunaApi = window.lunaDesktop?.luna;
    if (!navigator.mediaDevices?.getUserMedia || !fileApi?.writeTempDataUrl || !lunaApi?.transcribeAudio) {
      setStatus('Microphone transcription works only inside the Electron shell with backend STT connected.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      const silentGain = audioContext.createGain();
      const chunks = [];

      silentGain.gain.value = 0;
      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0);
        chunks.push(new Float32Array(input));
        if (!voiceLoopRef.current || micSessionRef.current?.autoStopping) return;

        let sum = 0;
        for (let index = 0; index < input.length; index += 1) {
          sum += input[index] * input[index];
        }
        const rms = Math.sqrt(sum / Math.max(1, input.length));
        const session = micSessionRef.current;
        if (!session) return;
        const now = Date.now();
        if (rms > 0.018) {
          session.heardSpeech = true;
          session.lastVoiceAt = now;
        }
        if (session.heardSpeech && now - session.lastVoiceAt > 1100) {
          session.autoStopping = true;
          window.setTimeout(() => stopMicrophoneCapture(), 0);
        }
      };

      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(audioContext.destination);

      micSessionRef.current = {
        stream,
        audioContext,
        source,
        processor,
        silentGain,
        chunks,
        sampleRate: audioContext.sampleRate,
        heardSpeech: false,
        lastVoiceAt: Date.now(),
        autoStopping: false,
      };
      setMicRecording(true);
      setStatus('Listening... click the microphone again to transcribe.');
    } catch (error) {
      setMicRecording(false);
      micSessionRef.current = null;
      setStatus(`Microphone could not start: ${String(error?.message || error)}`);
    }
  }

  async function stopMicrophoneCapture() {
    const session = micSessionRef.current;
    micSessionRef.current = null;
    setMicRecording(false);
    if (!session) return;

    try {
      session.processor.disconnect();
      session.source.disconnect();
      session.silentGain.disconnect();
    } catch {
      // Best effort cleanup.
    }
    session.stream.getTracks().forEach((track) => track.stop());
    await session.audioContext.close().catch(() => {});

    if (!session.chunks.length) {
      setStatus('No microphone audio was captured.');
      return;
    }

    try {
      setStatus('Transcribing microphone audio...');
      const merged = mergeFloat32Chunks(session.chunks);
      const downsampled = downsampleFloat32Buffer(merged, session.sampleRate, 16000);
      const wavBlob = encodePcm16Wav(downsampled, 16000);
      const dataUrl = await blobToDataUrl(wavBlob);
      const fileResult = await window.lunaDesktop.files.writeTempDataUrl({
        dataUrl,
        extension: 'wav',
      });

      if (!fileResult?.ok || !fileResult?.path) {
        setStatus(fileResult?.message || 'Microphone audio could not be saved.');
        return;
      }

      const result = await window.lunaDesktop.luna.transcribeAudio({
        filePath: fileResult.path,
        language: 'cs-CZ',
      });
      const transcript = normalizeTransportText(result?.transcript || '').trim();
      if (!result?.ok || !transcript) {
        setStatus(result?.message || 'Speech transcription did not return text.');
        return;
      }

      if (voiceLoopRef.current) {
        setComposer('');
        setStatus('Voice loop heard you. Sending it to Luna/Xeno...');
        await handleSend(transcript, { source: 'voice' });
        return;
      }

      setComposer((current) => {
        const prefix = current.trim() ? `${current.trim()} ` : '';
        return `${prefix}${transcript}`;
      });
      setStatus('Speech transcription inserted into the message box.');
    } catch (error) {
      setStatus(`Speech transcription failed: ${String(error?.message || error)}`);
    }
  }

  function toggleMicrophoneCapture() {
    if (micRecording) {
      stopMicrophoneCapture();
    } else {
      startMicrophoneCapture();
    }
  }

  function handleVoiceSessionTalk() {
    if (speechPlaying) {
      stopSpeechPlayback();
      setStatus('Luna stopped speaking. Listening again...');
      if (!micSessionRef.current) {
        window.setTimeout(() => startMicrophoneCapture(), 0);
      }
      return;
    }

    toggleMicrophoneCapture();
  }

  function stopSpeechPlayback() {
    const currentAudio = speechPlaybackRef.current;
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      speechPlaybackRef.current = null;
    }
    setSpeechPlaying(false);
  }

  function closeVoiceSession() {
    setAssistantModeEnabled(false);
    window.lunaDesktop?.window?.hideAssistantOverlay?.();
    voiceLoopRef.current = false;
    setVoiceLoopEnabled(false);
    if (micSessionRef.current) {
      stopMicrophoneCapture();
    }
    stopSpeechPlayback();
    setStatus('Voice session closed.');
  }

  async function playGeneratedSpeech(audioPath) {
    const fileApi = window.lunaDesktop?.files;
    if (!fileApi?.readAsDataUrl) {
      setStatus('Audio playback works only inside the Electron desktop shell.');
      return;
    }

    const audioResult = await fileApi.readAsDataUrl(audioPath);
    if (!audioResult?.ok || !audioResult?.dataUrl) {
      setStatus(audioResult?.message || 'Generated speech audio could not be loaded.');
      return;
    }

    stopSpeechPlayback();
    const audio = new Audio(audioResult.dataUrl);
    speechPlaybackRef.current = audio;
    setSpeechPlaying(true);
    audio.onended = () => {
      if (speechPlaybackRef.current === audio) {
        speechPlaybackRef.current = null;
        setSpeechPlaying(false);
      }
      if (voiceLoopRef.current) {
        window.setTimeout(() => {
          if (voiceLoopRef.current && !micSessionRef.current) {
            startMicrophoneCapture();
          }
        }, 450);
      }
    };
    audio.onerror = () => {
      if (speechPlaybackRef.current === audio) {
        speechPlaybackRef.current = null;
        setSpeechPlaying(false);
      }
      setStatus('Generated speech audio could not be played.');
    };
    await audio.play();
  }

  function getTextForSpeech(overrideText = '') {
    const typedText = normalizeTransportText(overrideText || composer).trim();
    if (typedText) return typedText;

    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message?.role !== 'user' && String(message?.content || '').trim()) {
        return normalizeTransportText(message.content).trim();
      }
    }
    return '';
  }

  function cleanTextForSpeech(text) {
    return shapeTextForSpeech(text);
  }

  async function handleTextToSpeech(overrideText = '') {
    if (speechPlaying) {
      stopSpeechPlayback();
      setStatus('Speech playback stopped.');
      return;
    }

    const lunaApi = window.lunaDesktop?.luna;
    if (!lunaApi?.synthesizeSpeech) {
      setStatus('Text-to-speech works only inside the Electron shell with NVIDIA TTS connected.');
      return;
    }

    const text = cleanTextForSpeech(getTextForSpeech(overrideText));
    if (!text) {
      setStatus('Write text first, or keep a Luna/Xeno answer in the chat to read aloud.');
      return;
    }

    try {
      setStatus('Generating voice with NVIDIA Magpie...');
      const result = await lunaApi.synthesizeSpeech({
        text,
        language: detectSpeechLanguage(text),
      });
      if (!result?.ok || !result?.audioPath) {
        setStatus(result?.message || 'Text-to-speech did not return audio.');
        return;
      }
      await playGeneratedSpeech(result.audioPath);
      setStatus('Playing generated voice.');
    } catch (error) {
      setSpeechPlaying(false);
      setStatus(`Text-to-speech failed: ${String(error?.message || error)}`);
    }
  }

  function handleInputAction(action, payload) {
    if (action === 'file' && payload) {
      const isVisualAttachment = Boolean(
        payload.type?.startsWith('image/')
        || payload.type?.startsWith('video/'),
      );
      const nextAttachment = {
        name: payload.name,
        type: payload.type || '',
        path: payload.path || '',
        previewUrl: payload.type?.startsWith('image/') ? URL.createObjectURL(payload) : '',
      };
      setAttachment((current) => {
        if (current?.previewUrl?.startsWith('blob:')) URL.revokeObjectURL(current.previewUrl);
        return nextAttachment;
      });
      setStatus(
        isVisualAttachment
          ? `Prilozeno: ${payload.name}. Po odeslani to Luna a Xeno analyzuji pres vision model.`
          : `Attached file: ${payload.name}`,
      );
      return;
    }
    if (action === 'screenshot') {
      requestDesktopObservation(action === 'screenshot');
      return;
    }
    if (action === 'share-screen') {
      refreshScreenShareSources();
      return;
    }
    if (action === 'assistant-mode') {
      toggleAssistantMode();
      return;
    }
    if (action === 'hide-to-tray') {
      handleWindowAction('hide-to-tray');
      return;
    }
    if (action === 'image') {
      setPendingGenerationType('image');
      setComposer((current) => current || 'Generate a black-and-white futuristic image for LunaAI.');
      setStatus('Image generation prompt loaded into the composer.');
      return;
    }
    if (action === 'mic') {
      toggleMicrophoneCapture();
      return;
    }
    if (action === 'voice') {
      setVoiceLoopEnabled((current) => {
        const next = !current;
        voiceLoopRef.current = next;
        if (next && !micSessionRef.current) {
          window.setTimeout(() => startMicrophoneCapture(), 0);
        }
        if (!next && micSessionRef.current) {
          window.setTimeout(() => stopMicrophoneCapture(), 0);
        }
        if (!next) {
          stopSpeechPlayback();
        }
        setStatus(next
          ? 'Voice loop enabled: Mic will send your speech and Luna/Xeno will answer aloud.'
          : 'Voice loop disabled. Voice button now reads text aloud manually.');
        return next;
      });
      return;
    }
    if (action === 'speak') {
      handleTextToSpeech();
      return;
    }
    const messagesByAction = {
      menu: 'Quick action surface is ready for file and image workflows.',
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
      const combinedPendingAction = pendingAction?.active ? pendingAction : actionEnginePending;

      return (
        <div className={`chat-page ${isEmptyChat ? 'is-empty' : ''}`}>
          <ChatArea
            messages={messages}
            chatId={currentChatId}
            thinkingState={thinkingState}
            revealingMessage={revealingMessage?.chatId === currentChatId ? revealingMessage : null}
            pendingAction={combinedPendingAction}
            onConfirmPendingAction={() => handlePendingActionDecision('confirm')}
            onCancelPendingAction={() => handlePendingActionDecision('cancel')}
            screenShare={screenShare}
            shareAutomation={shareAutomation}
            onStopScreenShare={() => stopScreenShare({ message: 'Desktop sharing was stopped.' })}
            onCloseShareDebugPanel={closeShareDebugPanel}
          />
          <ChatInput
            value={composer}
            onChange={setComposer}
            onSend={handleSend}
            onAction={handleInputAction}
            attachment={attachment}
            onClearAttachment={() => {
              setAttachment((current) => {
                if (current?.previewUrl?.startsWith('blob:')) URL.revokeObjectURL(current.previewUrl);
                return null;
              });
              if (attachment?.source === 'desktop-capture') {
                setPendingDesktopContext(null);
              }
            }}
            screenShare={screenShare}
            onStopScreenShare={() => stopScreenShare({ message: 'Desktop sharing was stopped.' })}
            micRecording={micRecording}
            voiceLoopEnabled={voiceLoopEnabled}
            voiceSpeaking={speechPlaying}
            assistantModeEnabled={assistantModeEnabled}
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
    if (page === 'updates') {
      return (
        <UpdatesPage
          title={pageData.title}
          subtitle={pageData.subtitle}
          items={updates}
          currentVersion={appMeta.version}
          initialFeed={updateFeed}
          onFeedChange={setUpdateFeed}
          onStatusChange={setStatus}
        />
      );
    }
    if (page === 'settings' || page === 'applications') {
      return (
        <SettingsPage
          settings={runtimeSettings}
          onChange={handleRuntimeSettings}
          onSave={handleSaveRuntimeSettings}
          appMeta={appMeta}
          applications={applicationsState}
          selectedAppId={selectedApplicationId}
          onSelectApp={setSelectedApplicationId}
          onOpenApp={handleOpenApplication}
          onSavePath={handleSaveApplicationPath}
        />
      );
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
            items={notifications}
            onSelect={handleNotificationSelect}
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
      <ScreenShareSourcePicker
        picker={screenSharePicker}
        onClose={closeScreenSharePicker}
        onRefresh={refreshScreenShareSources}
        onSelectSource={handleSelectScreenShareSource}
      />
      <DesktopShareOverlay
        screenShare={screenShare}
        onStopScreenShare={() => stopScreenShare({ message: 'Desktop sharing was stopped.' })}
      />
      <VoiceSessionOverlay
        visible={voiceLoopEnabled || micRecording || speechPlaying}
        listening={micRecording}
        speaking={speechPlaying}
        thinking={chatBusy || thinkingState.visible}
        onToggleListen={handleVoiceSessionTalk}
        onClose={closeVoiceSession}
      />
    </>
  );
}
