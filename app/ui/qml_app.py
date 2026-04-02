from __future__ import annotations

import platform
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from PySide6.QtCore import Property, QObject, Qt, QAbstractListModel, QModelIndex, QPersistentModelIndex, QByteArray, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from config.settings import APP_NAME


class DictListModel(QAbstractListModel):
    def __init__(self, role_names: list[str]) -> None:
        super().__init__()
        self._role_map = {Qt.ItemDataRole.UserRole + 1 + index: name for index, name in enumerate(role_names)}
        self._items: list[dict[str, object]] = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        key = self._role_map.get(role)
        if key is None:
            return None
        return item.get(key)

    def roleNames(self) -> dict[int, QByteArray]:
        return {role: QByteArray(name.encode('utf-8')) for role, name in self._role_map.items()}

    def replace_items(self, items: Sequence[Mapping[str, object]]) -> None:
        self.beginResetModel()
        self._items = [dict(item) for item in items]
        self.endResetModel()


class LunaQmlBridge(QObject):
    statusTextChanged = Signal()
    currentChatTitleChanged = Signal()
    currentProjectTitleChanged = Signal()
    currentProjectPhaseChanged = Signal()
    currentProjectNextStepChanged = Signal()
    controlSummaryChanged = Signal()
    projectMemoryTextChanged = Signal()
    taskDetailTextChanged = Signal()
    profileNameChanged = Signal()
    profileImagePathChanged = Signal()
    deviceInfoChanged = Signal()
    appVersionChanged = Signal()
    galleryPreviewTitleChanged = Signal()
    galleryPreviewMetaChanged = Signal()
    galleryPreviewPathChanged = Signal()

    def __init__(self, engine: Any) -> None:
        super().__init__()
        self.engine = engine
        self._status_text = 'LunaAI system ready.'
        self._current_chat_title = 'LunaAI'
        self._current_project_title = 'No project selected'
        self._current_project_phase = 'draft'
        self._current_project_next_step = 'Create or select a project.'
        self._control_summary = self.engine.get_system_control_summary()
        self._project_memory_text = 'No project memory yet.'
        self._task_detail_text = 'Select a task to see more detail.'
        self._profile_name = self.engine.user_settings.data.profile_display_name.strip() or 'Operator'
        self._profile_image_path = self._to_file_url(self.engine.user_settings.data.profile_image_path)
        self._device_info = self._build_device_info()
        self._app_version = 'LunaAI Desktop Preview 0.9'
        self._gallery_preview_title = 'Gallery'
        self._gallery_preview_meta = 'Generated images and videos appear here.'
        self._gallery_preview_path = ''
        self._messages_model = DictListModel(['role', 'author', 'content'])
        self._chats_model = DictListModel(['sessionId', 'title', 'pinned'])
        self._projects_model = DictListModel(['projectId', 'name', 'currentPhase', 'taskCount', 'memoryCount'])
        self._tasks_model = DictListModel(['title', 'status', 'description', 'tool', 'risk', 'handoffNote', 'dependencies'])
        self._profiles_model = DictListModel(['key', 'label', 'description'])
        self._gallery_model = DictListModel(['name', 'path', 'kind', 'meta'])
        self._apps_model = DictListModel(['key', 'label', 'path', 'connected'])
        self._updates_model = DictListModel(['title', 'detail', 'status'])
        self._friends_model = DictListModel(['name', 'status', 'detail'])
        self._current_project_id = ''
        self._chat_search_query = ''
        self._pinned_chats: set[str] = set()
        self._archived_chats: set[str] = set()
        self._refresh_profiles()
        self.refresh_all()

    @Property(QObject, constant=True)
    def messagesModel(self) -> QObject:
        return self._messages_model

    @Property(QObject, constant=True)
    def chatsModel(self) -> QObject:
        return self._chats_model

    @Property(QObject, constant=True)
    def projectsModel(self) -> QObject:
        return self._projects_model

    @Property(QObject, constant=True)
    def tasksModel(self) -> QObject:
        return self._tasks_model

    @Property(QObject, constant=True)
    def profilesModel(self) -> QObject:
        return self._profiles_model

    @Property(QObject, constant=True)
    def galleryModel(self) -> QObject:
        return self._gallery_model

    @Property(QObject, constant=True)
    def appsModel(self) -> QObject:
        return self._apps_model

    @Property(QObject, constant=True)
    def updatesModel(self) -> QObject:
        return self._updates_model

    @Property(QObject, constant=True)
    def friendsModel(self) -> QObject:
        return self._friends_model

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(str, notify=currentChatTitleChanged)
    def currentChatTitle(self) -> str:
        return self._current_chat_title

    @Property(str, notify=currentProjectTitleChanged)
    def currentProjectTitle(self) -> str:
        return self._current_project_title

    @Property(str, notify=currentProjectPhaseChanged)
    def currentProjectPhase(self) -> str:
        return self._current_project_phase

    @Property(str, notify=currentProjectNextStepChanged)
    def currentProjectNextStep(self) -> str:
        return self._current_project_next_step

    @Property(str, notify=controlSummaryChanged)
    def controlSummary(self) -> str:
        return self._control_summary

    @Property(str, notify=projectMemoryTextChanged)
    def projectMemoryText(self) -> str:
        return self._project_memory_text

    @Property(str, notify=taskDetailTextChanged)
    def taskDetailText(self) -> str:
        return self._task_detail_text

    @Property(str, notify=profileNameChanged)
    def profileName(self) -> str:
        return self._profile_name

    @Property(str, notify=profileImagePathChanged)
    def profileImagePath(self) -> str:
        return self._profile_image_path

    @Property(str, notify=deviceInfoChanged)
    def deviceInfo(self) -> str:
        return self._device_info

    @Property(str, notify=appVersionChanged)
    def appVersion(self) -> str:
        return self._app_version

    @Property(str, notify=galleryPreviewTitleChanged)
    def galleryPreviewTitle(self) -> str:
        return self._gallery_preview_title

    @Property(str, notify=galleryPreviewMetaChanged)
    def galleryPreviewMeta(self) -> str:
        return self._gallery_preview_meta

    @Property(str, notify=galleryPreviewPathChanged)
    def galleryPreviewPath(self) -> str:
        return self._gallery_preview_path

    def _set_status(self, value: str) -> None:
        value = (value or '').strip() or 'LunaAI system ready.'
        if value != self._status_text:
            self._status_text = value
            self.statusTextChanged.emit()

    def _set_current_chat_title(self, value: str) -> None:
        value = value or 'LunaAI'
        if value != self._current_chat_title:
            self._current_chat_title = value
            self.currentChatTitleChanged.emit()

    def _set_current_project_title(self, value: str) -> None:
        value = value or 'No project selected'
        if value != self._current_project_title:
            self._current_project_title = value
            self.currentProjectTitleChanged.emit()

    def _set_current_project_phase(self, value: str) -> None:
        value = value or 'draft'
        if value != self._current_project_phase:
            self._current_project_phase = value
            self.currentProjectPhaseChanged.emit()

    def _set_current_project_next_step(self, value: str) -> None:
        value = value or 'Create or select a project.'
        if value != self._current_project_next_step:
            self._current_project_next_step = value
            self.currentProjectNextStepChanged.emit()

    def _set_control_summary(self, value: str) -> None:
        if value != self._control_summary:
            self._control_summary = value
            self.controlSummaryChanged.emit()

    def _set_project_memory_text(self, value: str) -> None:
        if value != self._project_memory_text:
            self._project_memory_text = value
            self.projectMemoryTextChanged.emit()

    def _set_task_detail_text(self, value: str) -> None:
        if value != self._task_detail_text:
            self._task_detail_text = value
            self.taskDetailTextChanged.emit()

    def _set_profile_name(self, value: str) -> None:
        value = value or 'Operator'
        if value != self._profile_name:
            self._profile_name = value
            self.profileNameChanged.emit()

    def _set_profile_image_path(self, value: str) -> None:
        if value != self._profile_image_path:
            self._profile_image_path = value
            self.profileImagePathChanged.emit()

    def _set_device_info(self, value: str) -> None:
        if value != self._device_info:
            self._device_info = value
            self.deviceInfoChanged.emit()

    def _set_gallery_preview(self, title: str, meta: str, path: str) -> None:
        if title != self._gallery_preview_title:
            self._gallery_preview_title = title
            self.galleryPreviewTitleChanged.emit()
        if meta != self._gallery_preview_meta:
            self._gallery_preview_meta = meta
            self.galleryPreviewMetaChanged.emit()
        if path != self._gallery_preview_path:
            self._gallery_preview_path = path
            self.galleryPreviewPathChanged.emit()

    def _to_file_url(self, raw_path: str) -> str:
        cleaned = str(raw_path or '').strip()
        if not cleaned:
            return ''
        path = Path(cleaned)
        if path.exists():
            return path.resolve().as_uri()
        return ''

    def _build_device_info(self) -> str:
        parts = [platform.node() or 'Unknown device', platform.system() or 'Windows', platform.machine() or 'x64']
        return ' | '.join(part for part in parts if part)

    def _refresh_messages(self) -> None:
        history = self.engine.memory.load_history()
        items: list[dict[str, object]] = []
        for item in history:
            role = str(item.get('role', 'assistant'))
            content = str(item.get('content', '')).strip()
            if not content:
                continue
            items.append({'role': role, 'author': 'You' if role == 'user' else 'Luna', 'content': content})
        self._messages_model.replace_items(items)

    def _refresh_chats(self) -> None:
        chats = self.engine.list_chats()
        query = self._chat_search_query.strip().lower()
        filtered: list[dict[str, object]] = []
        for item in chats:
            session_id = str(item.get('id', ''))
            title = str(item.get('title', 'LunaAI'))
            if session_id in self._archived_chats:
                continue
            if query and query not in title.lower():
                continue
            filtered.append({'sessionId': session_id, 'title': title, 'pinned': session_id in self._pinned_chats})
        filtered.sort(key=lambda row: (not bool(row.get('pinned')), str(row.get('title', '')).lower()))
        self._chats_model.replace_items(filtered)
        self._set_current_chat_title(self.engine.get_current_chat_title())

    def _refresh_profiles(self) -> None:
        profiles = self.engine.list_system_control_profiles()
        self._profiles_model.replace_items([
            {'key': str(item.get('key', '')), 'label': str(item.get('label', item.get('key', ''))), 'description': str(item.get('description', ''))}
            for item in profiles
        ])

    def _refresh_projects(self) -> None:
        projects = self.engine.list_projects()
        self._projects_model.replace_items([
            {
                'projectId': item.get('id', ''),
                'name': item.get('name', 'Project'),
                'currentPhase': item.get('current_phase', 'draft'),
                'taskCount': item.get('task_count', '0'),
                'memoryCount': item.get('memory_count', '0'),
            }
            for item in projects
        ])

        project = self.engine.get_current_project()
        if not project:
            self._current_project_id = ''
            self._set_current_project_title('No project selected')
            self._set_current_project_phase('draft')
            self._set_current_project_next_step('Create or select a project.')
            self._tasks_model.replace_items([])
            self._set_project_memory_text('No project memory yet.')
            self._set_task_detail_text('Select a task to see more detail.')
            return

        self._current_project_id = str(project.get('id', ''))
        self._set_current_project_title(str(project.get('name', 'No project selected')))
        self._set_current_project_phase(str(project.get('current_phase', 'draft')))
        self._set_current_project_next_step(str(project.get('next_step', 'Create a project blueprint.')))
        tasks = project.get('tasks', []) if isinstance(project.get('tasks', []), list) else []
        self._tasks_model.replace_items([
            {
                'title': str(task.get('title', 'Task')),
                'status': str(task.get('status', 'pending')),
                'description': str(task.get('description', '')),
                'tool': str(task.get('tool', '')),
                'risk': str(task.get('risk', '')),
                'handoffNote': str(task.get('handoff_note', '')),
                'dependencies': str(task.get('dependencies', '')),
            }
            for task in tasks
        ])
        self._set_project_memory_from_project(project)

    def _set_project_memory_from_project(self, project: dict[str, object] | None) -> None:
        if not project:
            self._set_project_memory_text('No project memory yet.')
            return
        raw_memory_entries = project.get('memory_entries', [])
        raw_attachment_names = project.get('attachment_names', [])
        memory_entries: list[object] = cast(list[object], raw_memory_entries) if isinstance(raw_memory_entries, list) else []
        attachment_names: list[object] = cast(list[object], raw_attachment_names) if isinstance(raw_attachment_names, list) else []
        chunks = [str(item) for item in memory_entries[:6]]
        if attachment_names:
            chunks.append('Linked files: ' + ', '.join(str(name) for name in attachment_names[:6]))
        self._set_project_memory_text('\n\n'.join(chunks) if chunks else 'No project memory yet.')

    def _refresh_profile(self) -> None:
        data = self.engine.user_settings.data
        self._set_profile_name(data.profile_display_name.strip() or 'Operator')
        self._set_profile_image_path(self._to_file_url(data.profile_image_path))
        self._set_device_info(self._build_device_info())

    def _refresh_gallery(self) -> None:
        root = Path('data/gallery')
        root.mkdir(parents=True, exist_ok=True)
        files: list[dict[str, object]] = []
        for path in sorted(root.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}:
                continue
            kind = 'Video' if suffix in {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'} else 'Image'
            files.append({
                'name': path.stem,
                'path': path.resolve().as_uri(),
                'kind': kind,
                'meta': f'{kind} - {path.suffix.lower()}',
            })
        self._gallery_model.replace_items(files)
        if files:
            first = files[0]
            self._set_gallery_preview(str(first['name']), str(first['meta']), str(first['path']))
        else:
            self._set_gallery_preview('Gallery', 'Generated images and videos appear here.', '')

    def _refresh_apps(self) -> None:
        workspace = self.engine.user_settings.data
        app_fields = [
            ('vscode', 'VS Code', workspace.vscode_path),
            ('blender', 'Blender', workspace.blender_path),
            ('unreal', 'Unreal Engine', workspace.unreal_engine_path),
            ('unity', 'Unity', workspace.unity_path),
            ('photoshop', 'Photoshop', workspace.photoshop_path),
            ('davinci', 'DaVinci Resolve', workspace.davinci_resolve_path),
            ('premiere', 'Premiere Pro', workspace.premiere_pro_path),
            ('after_effects', 'After Effects', workspace.after_effects_path),
            ('figma', 'Figma', workspace.figma_path),
            ('fl_studio', 'FL Studio', workspace.fl_studio_path),
            ('substance', 'Substance 3D Painter', workspace.substance_painter_path),
        ]
        self._apps_model.replace_items([
            {'key': key, 'label': label, 'path': path, 'connected': bool(str(path).strip())}
            for key, label, path in app_fields
        ])

    def _refresh_updates(self) -> None:
        recent = self.engine.list_recent_actions(6)
        self._updates_model.replace_items([
            {
                'title': str(item.get('title', 'System update')),
                'detail': str(item.get('detail', '')),
                'status': str(item.get('status', 'completed')).upper(),
            }
            for item in recent
        ])

    def _refresh_friends(self) -> None:
        self._friends_model.replace_items([
            {'name': 'Luna Core', 'status': 'Online', 'detail': 'Main operator interface and personal AI layer.'},
            {'name': 'XenoAI', 'status': 'Linked', 'detail': 'Strategic planning and hidden reasoning layer.'},
            {'name': 'Task Agent', 'status': 'Ready', 'detail': 'Execution layer for files, apps, and project actions.'},
        ])

    def refresh_all(self) -> None:
        self._refresh_messages()
        self._refresh_chats()
        self._refresh_projects()
        self._refresh_profiles()
        self._refresh_gallery()
        self._refresh_apps()
        self._refresh_updates()
        self._refresh_friends()
        self._refresh_profile()
        self._set_control_summary(self.engine.get_system_control_summary())

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        response = self.engine.chat(cleaned)
        self.refresh_all()
        self._set_status(response if response else 'Message sent.')

    @Slot()
    def createNewChat(self) -> None:
        self.engine.create_new_chat()
        self.refresh_all()
        self._set_status('New chat created.')

    @Slot(str)
    def switchChat(self, session_id: str) -> None:
        if not session_id.strip():
            return
        self.engine.switch_chat(session_id)
        self.refresh_all()
        self._set_status('Conversation ready.')

    @Slot(str)
    def setChatSearchQuery(self, query: str) -> None:
        self._chat_search_query = query or ''
        self._refresh_chats()

    @Slot(str, str)
    def renameChat(self, session_id: str, title: str) -> None:
        cleaned_id = session_id.strip()
        cleaned_title = title.strip()
        if not cleaned_id or not cleaned_title:
            return
        self.engine.rename_chat(cleaned_id, cleaned_title)
        self.refresh_all()
        self._set_status('Chat title updated.')

    @Slot(str)
    def deleteChat(self, session_id: str) -> None:
        cleaned_id = session_id.strip()
        if not cleaned_id:
            return
        self.engine.delete_chat(cleaned_id)
        self._pinned_chats.discard(cleaned_id)
        self._archived_chats.discard(cleaned_id)
        self.refresh_all()
        self._set_status('Chat removed from the workspace.')

    @Slot(str)
    def pinChat(self, session_id: str) -> None:
        cleaned_id = session_id.strip()
        if not cleaned_id:
            return
        if cleaned_id in self._pinned_chats:
            self._pinned_chats.remove(cleaned_id)
            self._set_status('Chat returned to the normal list.')
        else:
            self._pinned_chats.add(cleaned_id)
            self._set_status('Chat pinned to the top of the workspace.')
        self._refresh_chats()

    @Slot(str)
    def archiveChat(self, session_id: str) -> None:
        cleaned_id = session_id.strip()
        if not cleaned_id:
            return
        self._archived_chats.add(cleaned_id)
        self._pinned_chats.discard(cleaned_id)
        self._refresh_chats()
        self._set_status('Chat archived from the main sidebar.')

    @Slot()
    def observeDesktop(self) -> None:
        self._set_status(self.engine.observe_desktop(False))

    @Slot()
    def captureScreen(self) -> None:
        self._set_status(self.engine.observe_desktop(True))
        self._refresh_gallery()

    @Slot()
    def refreshCapabilities(self) -> None:
        self._set_status(self.engine.describe_local_capabilities())

    @Slot(str, str)
    def createProject(self, name: str, brief: str) -> None:
        title = name.strip() or 'New Project'
        project = self.engine.create_project(title, brief.strip())
        project_id = str(project.get('id', ''))
        if project_id:
            self.engine.set_current_project(project_id)
        self.refresh_all()
        self._set_status(f'Project {title} is ready.')

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        if not project_id.strip():
            return
        self.engine.set_current_project(project_id)
        self.refresh_all()
        self._set_status('Project workspace ready.')

    @Slot(str)
    def generateBlueprint(self, brief: str) -> None:
        cleaned = brief.strip()
        if not cleaned:
            self._set_status('Write a project brief first.')
            return
        project = self.engine.get_current_project()
        project_name = str(project.get('name', '')) if project else ''
        result = self.engine.generate_project_package(cleaned, project_name=project_name)
        project_id = str(result.get('project_id', ''))
        if project_id:
            self.engine.set_current_project(project_id)
        self.refresh_all()
        self._set_status(str(result.get('summary', 'Blueprint created.')))

    @Slot(int)
    def selectTask(self, index: int) -> None:
        project = self.engine.get_current_project()
        if not project:
            self._set_task_detail_text('Select a task to see more detail.')
            return
        tasks = project.get('tasks', []) if isinstance(project.get('tasks', []), list) else []
        if index < 0 or index >= len(tasks):
            self._set_task_detail_text('Select a task to see more detail.')
            return
        task = tasks[index]
        lines = [str(task.get('description', 'No details available.'))]
        handoff = str(task.get('handoff_note', '')).strip()
        dependencies = str(task.get('dependencies', '')).strip()
        tool = str(task.get('tool', '')).strip()
        risk = str(task.get('risk', '')).strip()
        if handoff:
            lines.append(f'Agent handoff: {handoff}')
        if dependencies:
            lines.append(f'Depends on: {dependencies}')
        meta = ' | '.join(part for part in [f'Tool: {tool}' if tool else '', f'Risk: {risk}' if risk else ''] if part)
        if meta:
            lines.append(meta)
        self._set_task_detail_text('\n\n'.join(lines))

    @Slot()
    def runNextStep(self) -> None:
        if not self._current_project_id:
            self._set_status('No active project selected.')
            return
        result = self.engine.run_next_agent_task(self._current_project_id)
        self.refresh_all()
        self._set_status(str(result.get('message', 'No next step was executed.')))

    @Slot()
    def runNextChain(self) -> None:
        if not self._current_project_id:
            self._set_status('No active project selected.')
            return
        result = self.engine.run_next_agent_chain(self._current_project_id)
        self.refresh_all()
        self._set_status(str(result.get('message', 'No chain was executed.')))

    @Slot(str)
    def setControlProfile(self, profile_key: str) -> None:
        if not profile_key.strip():
            return
        summary = self.engine.set_system_control_profile(profile_key.strip())
        self._set_control_summary(summary)
        self._set_status(summary)

    @Slot()
    def refreshControlSummary(self) -> None:
        self._set_control_summary(self.engine.get_system_control_summary())
        self._set_status(self._control_summary)

    @Slot(result=str)
    def currentProjectBrief(self) -> str:
        project = self.engine.get_current_project()
        if not project:
            return ''
        return str(project.get('brief', ''))

    @Slot(result=bool)
    def hasMessages(self) -> bool:
        return self._messages_model.rowCount() > 0

    @Slot(str)
    def launchConnectedApp(self, app_key: str) -> None:
        result = self.engine.open_connected_app(app_key.strip(), '')
        self._set_status(str(result.get('message', 'App launch finished.')))

    @Slot(str)
    def noteAction(self, text: str) -> None:
        self._set_status(text.strip() or 'Action prepared.')

    @Slot(int)
    def selectGalleryItem(self, index: int) -> None:
        items = list(self._gallery_model._items)
        if index < 0 or index >= len(items):
            self._set_gallery_preview('Gallery', 'Generated images and videos appear here.', '')
            return
        item = items[index]
        self._set_gallery_preview(str(item.get('name', 'Gallery')), str(item.get('meta', '')), str(item.get('path', '')))


class LunaQmlApp:
    def __init__(self, engine: Any = None) -> None:
        if engine is None:
            from app.core.engine import LunaEngine
            engine = LunaEngine()
        self.engine = engine
        self.app: QGuiApplication | None = None
        self.qml_engine: QQmlApplicationEngine | None = None
        self.bridge: LunaQmlBridge | None = None

    def run(self) -> None:
        app = QGuiApplication.instance()
        if not isinstance(app, QGuiApplication):
            app = QGuiApplication([])
        self.app = app
        self.bridge = LunaQmlBridge(self.engine)
        qml_engine = QQmlApplicationEngine()
        self.qml_engine = qml_engine
        qml_engine.rootContext().setContextProperty('lunaBridge', self.bridge)
        qml_path = Path(__file__).resolve().parent / 'qml' / 'LunaMain.qml'
        qml_engine.load(str(qml_path))
        if not qml_engine.rootObjects():
            raise RuntimeError('QML UI could not be loaded.')
        app.exec()
