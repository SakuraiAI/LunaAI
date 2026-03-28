import html
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QObject, QParallelAnimationGroup, QPropertyAnimation, Qt, QThread, QTimer, QSize, Signal, Slot
from PySide6.QtGui import QCloseEvent, QColor, QCursor, QIcon, QKeyEvent, QPainter, QPainterPath, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QMenu,
    QFileDialog,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QStyle,
    QVBoxLayout,
    QWidget,
)



BG = "#171717"
PANEL = "#1f1f1f"
PANEL_2 = "#242424"
PANEL_3 = "#2b2b2b"
TEXT = "#f5f5f5"
MUTED = "#a1a1a1"
ACCENT = "#ffffff"
ACCENT_SOFT = "#e8e8e8"
BORDER = "#333333"
USER_BUBBLE = "#262626"
AI_BUBBLE = "#202020"
HOVER = "#2c2c2c"

CONFIG_PATH = Path("d:/LunaAI/config/settings.py")
LOGO_PATH = Path(r"C:\Users\sakur\Pictures\9EC6EC8B-5524-48FC-9A2E-9E140BC5CC38.png")
GALLERY_PATH = Path("d:/LunaAI/data/gallery")


def _make_shadow(blur: float = 28.0, y_offset: float = 8.0, alpha: int = 90) -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y_offset)
    shadow.setColor(QColor(0, 0, 0, alpha))
    return shadow



def _safe_powershell_value(command: str) -> str:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    output = (completed.stdout or "").strip()
    return output if completed.returncode == 0 else ""



def _build_profile_pixmap(image_path: str, size: int = 88, fallback_text: str = "L", radius: float | None = None) -> QPixmap:
    path = Path(image_path) if image_path else None
    effective_radius = radius if radius is not None else max(14.0, size * 0.28)
    if path and path.exists():
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            rounded = QPixmap(size, size)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            clip = QPainterPath()
            clip.addRoundedRect(0, 0, size, size, effective_radius, effective_radius)
            painter.setClipPath(clip)
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            return rounded

    fallback = QPixmap(size, size)
    fallback.fill(Qt.GlobalColor.transparent)
    painter = QPainter(fallback)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor(38, 38, 38))
    painter.setPen(QColor(56, 56, 56))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, effective_radius, effective_radius)
    painter.setPen(QColor(245, 245, 245))
    font = painter.font()
    font.setPointSize(max(16, int(size * 0.28)))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(fallback.rect(), Qt.AlignmentFlag.AlignCenter, fallback_text[:1].upper() or "L")
    painter.end()
    return fallback


def _read_system_overview() -> dict[str, str]:
    cpu_name = _safe_powershell_value('(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)')
    gpu_name = _safe_powershell_value('((Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ", ")')
    memory_gb = _safe_powershell_value('[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)')
    device_model = _safe_powershell_value('(Get-CimInstance Win32_ComputerSystem).Model')

    operating_system = f"{platform.system()} {platform.release()}".strip()
    return {
        "Email": "",
        "User": os.environ.get("USERNAME", "Unknown"),
        "Host": platform.node() or os.environ.get("COMPUTERNAME", "Unknown"),
        "Device": device_model or "Unknown device",
        "OS": operating_system or "Unknown OS",
        "Architecture": platform.machine() or "Unknown",
        "CPU": cpu_name or platform.processor() or f"{os.cpu_count() or '?'} logical cores",
        "GPU": gpu_name or "Not detected",
        "Memory": f"{memory_gb} GB" if memory_gb else "Not detected",
        "Python": platform.python_version(),
    }



class ResponseWorker(QObject):
    finished = Signal(str)

    def __init__(self, engine: Any, user_text: str) -> None:
        super().__init__()
        self.engine = engine
        self.user_text = user_text

    @Slot()
    def run(self) -> None:
        response = self.engine.chat(self.user_text)
        self.finished.emit(response)


class MessageBubble(QFrame):
    url_pattern = re.compile(r"(https?://[^\s<]+)")

    def __init__(self, sender: str, text: str, is_user: bool = False) -> None:
        super().__init__()
        self.setObjectName("messageRow")
        self._raw_text = text

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(0)

        if is_user:
            row.addStretch()

        bubble = QFrame()
        bubble.setObjectName("userBubble" if is_user else "aiBubble")
        bubble.setMaximumWidth(720 if is_user else 820)
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(20, 16, 20, 16)
        bubble_layout.setSpacing(7)

        self.sender_label = QLabel(sender)
        self.sender_label.setObjectName("senderLabel")
        self.sender_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.text_label = QLabel()
        self.text_label.setObjectName("messageText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        self.text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.text_label.setOpenExternalLinks(True)
        self.text_label.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.text_label.setText(self._format_text(text))

        bubble_layout.addWidget(self.sender_label)
        bubble_layout.addWidget(self.text_label)
        bubble.setGraphicsEffect(_make_shadow(24.0, 6.0, 70))
        row.addWidget(bubble)

        if not is_user:
            row.addStretch()

    def _format_text(self, text: str) -> str:
        paragraphs: list[str] = []
        for block in text.strip().split("\n\n"):
            escaped = html.escape(block).replace("\n", "<br>")
            linked = self.url_pattern.sub(r'<a href="\1">\1</a>', escaped)
            paragraphs.append(f'<div style="margin: 0 0 12px 0;">{linked}</div>')
        if not paragraphs:
            return ""
        return "".join(paragraphs)

    def set_text(self, text: str) -> None:
        self._raw_text = text
        self.text_label.setText(self._format_text(text))


class TypingBubble(QFrame):
    def __init__(self, on_tick: Any) -> None:
        super().__init__()
        self._on_tick = on_tick
        self._dot_count = 0

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(0)

        bubble = QFrame()
        bubble.setObjectName("aiBubble")
        bubble.setMaximumWidth(220)
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(20, 16, 20, 16)
        bubble_layout.setSpacing(7)

        sender_label = QLabel("Luna")
        sender_label.setObjectName("senderLabel")
        sender_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.typing_label = QLabel("Luna.")
        self.typing_label.setObjectName("typingText")
        self.typing_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        bubble_layout.addWidget(sender_label)
        bubble_layout.addWidget(self.typing_label)
        bubble.setGraphicsEffect(_make_shadow(20.0, 5.0, 55))
        row.addWidget(bubble)
        row.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(320)

    def _animate(self) -> None:
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count or "."
        self.typing_label.setText(f"Luna{dots}")
        self._on_tick()

    def stop(self) -> None:
        self.timer.stop()


class ExpandingMessageInput(QTextEdit):
    submit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("messageInput")
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(52)
        self.setMaximumHeight(164)
        self.document().documentLayout().documentSizeChanged.connect(self._update_height)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            event.accept()
            self.submit_requested.emit()
            return
        super().keyPressEvent(event)

    def _update_height(self) -> None:
        document_height = self.document().size().height()
        target = max(52, min(164, int(document_height) + 20))
        self.setFixedHeight(target)

    def setPlainTextAndMoveToEnd(self, text: str) -> None:
        self.setPlainText(text)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self._update_height()


def _is_image_path(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}


def _is_video_path(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def _extract_media_paths_from_text(text: str) -> list[Path]:
    suffixes = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")
    found: list[Path] = []
    seen: set[str] = set()

    for chunk in re.split(r"\s+", text):
        cleaned = chunk.strip().strip("\"'()[]{}<>,")
        if not cleaned:
            continue
        if not cleaned.lower().endswith(suffixes):
            continue
        if not (":\\" in cleaned or cleaned.startswith("/") or cleaned.startswith(".\\") or cleaned.startswith("./")):
            continue

        candidate = Path(cleaned)
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(candidate)
    return found



class AttachmentCard(QFrame):
    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = file_path
        self.setObjectName("attachmentCard")
        self.setFixedWidth(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.preview = QLabel()
        self.preview.setObjectName("attachmentPreview")
        self.preview.setFixedSize(94, 72)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = Path(file_path).name
        self.name_label = QLabel(name)
        self.name_label.setObjectName("attachmentName")
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_label)

        self._render_preview()

    def _render_preview(self) -> None:
        if _is_image_path(self.file_path) and Path(self.file_path).exists():
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(94, 72, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                rounded = QPixmap(94, 72)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                clip = QPainterPath()
                clip.addRoundedRect(0, 0, 94, 72, 14, 14)
                painter.setClipPath(clip)
                painter.drawPixmap(0, 0, scaled)
                painter.end()
                self.preview.setPixmap(rounded)
                return

        suffix = Path(self.file_path).suffix.lower().replace(".", "").upper() or "FILE"
        self.preview.setText(suffix[:6])


class ProfileDialog(QDialog):
    def __init__(self, profile_rows: list[tuple[str, str]], system_rows: list[tuple[str, str]], image_path: str = "", display_name: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profil")
        self.resize(760, 680)
        self.profile_image_path = image_path
        self.profile_display_name = display_name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Profil")
        title.setObjectName("settingsSectionTitle")
        subtitle = QLabel("Local identity, account links, and system overview for this Luna workspace.")
        subtitle.setObjectName("settingsFieldHelper")
        subtitle.setWordWrap(True)

        profile_card = QFrame()
        profile_card.setObjectName("settingsCard")
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(18, 18, 18, 18)
        profile_layout.setSpacing(14)
        profile_heading = QLabel("Profile")
        profile_heading.setObjectName("settingsSectionTitle")
        profile_layout.addWidget(profile_heading)

        image_row = QHBoxLayout()
        image_row.setSpacing(16)
        self.profile_image_label = QLabel()
        self.profile_image_label.setObjectName("profileImageLabel")
        self.profile_image_label.setFixedSize(88, 88)

        image_actions = QVBoxLayout()
        image_actions.setSpacing(8)

        self.profile_name_input = QLineEdit()
        self.profile_name_input.setObjectName("settingsInput")
        self.profile_name_input.setPlaceholderText("Your display name")
        self.profile_name_input.setText(self.profile_display_name)
        image_title = QLabel("Profile image")
        image_title.setObjectName("settingsFieldLabel")
        image_hint = QLabel("Choose a local image for your Luna profile.")
        image_hint.setObjectName("settingsFieldHelper")
        image_hint.setWordWrap(True)
        self.profile_image_button = QPushButton("Choose image")
        self.profile_image_button.setObjectName("secondaryButton")
        self.profile_image_button.clicked.connect(self._choose_profile_image)
        self.profile_image_remove_button = QPushButton("Remove image")
        self.profile_image_remove_button.setObjectName("secondaryButton")
        self.profile_image_remove_button.clicked.connect(self._remove_profile_image)
        image_actions.addWidget(image_title)
        image_actions.addWidget(image_hint)
        image_actions.addWidget(self.profile_name_input)
        image_actions.addWidget(self.profile_image_button, 0, Qt.AlignmentFlag.AlignLeft)
        image_actions.addWidget(self.profile_image_remove_button, 0, Qt.AlignmentFlag.AlignLeft)
        image_actions.addStretch(1)

        image_row.addWidget(self.profile_image_label, 0, Qt.AlignmentFlag.AlignTop)
        image_row.addLayout(image_actions, 1)
        profile_layout.addLayout(image_row)

        profile_grid = QGridLayout()
        profile_grid.setHorizontalSpacing(18)
        profile_grid.setVerticalSpacing(10)
        for row, (label_text, value_text) in enumerate(profile_rows):
            label = QLabel(label_text)
            label.setObjectName("settingsFieldLabel")
            value = QLabel(value_text or "Not set")
            value.setObjectName("settingsFieldHelper")
            value.setWordWrap(True)
            profile_grid.addWidget(label, row, 0)
            profile_grid.addWidget(value, row, 1)
        profile_layout.addLayout(profile_grid)

        system_card = QFrame()
        system_card.setObjectName("settingsCard")
        system_layout = QVBoxLayout(system_card)
        system_layout.setContentsMargins(18, 18, 18, 18)
        system_layout.setSpacing(12)
        system_heading = QLabel("System")
        system_heading.setObjectName("settingsSectionTitle")
        system_layout.addWidget(system_heading)
        system_grid = QGridLayout()
        system_grid.setHorizontalSpacing(18)
        system_grid.setVerticalSpacing(10)
        for row, (label_text, value_text) in enumerate(system_rows):
            label = QLabel(label_text)
            label.setObjectName("settingsFieldLabel")
            value = QLabel(value_text or "Unknown")
            value.setObjectName("settingsFieldHelper")
            value.setWordWrap(True)
            system_grid.addWidget(label, row, 0)
            system_grid.addWidget(value, row, 1)
        system_layout.addLayout(system_grid)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Save")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(profile_card)
        layout.addWidget(system_card)
        layout.addStretch(1)
        layout.addWidget(buttons)

        self._refresh_profile_image()

    def _refresh_profile_image(self) -> None:
        fallback = self.profile_name_input.text().strip()[:1] or "L"
        self.profile_image_label.setPixmap(_build_profile_pixmap(self.profile_image_path, 88, fallback))

    def _choose_profile_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose profile image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not file_path:
            return
        self.profile_image_path = file_path
        self._refresh_profile_image()

    def _remove_profile_image(self) -> None:
        self.profile_image_path = ""
        self._refresh_profile_image()

    def accept(self) -> None:
        self.profile_display_name = self.profile_name_input.text().strip()
        super().accept()



class ProjectCreateDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Project")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Create a new project")
        title.setObjectName("settingsSectionTitle")
        subtitle = QLabel("Define the project name and a few starting parameters for Luna and Xeno.")
        subtitle.setObjectName("settingsFieldHelper")
        subtitle.setWordWrap(True)

        self.project_name_input = QLineEdit()
        self.project_name_input.setObjectName("settingsInput")
        self.project_name_input.setPlaceholderText("Project name")

        self.project_goal_input = QTextEdit()
        self.project_goal_input.setObjectName("studioInput")
        self.project_goal_input.setPlaceholderText("What should this project do?")
        self.project_goal_input.setFixedHeight(120)

        self.project_type_input = QComboBox()
        self.project_type_input.setObjectName("settingsSelect")
        self.project_type_input.addItems(["App", "Game", "Website", "Brand", "Research", "Tool"])

        self.project_stack_input = QLineEdit()
        self.project_stack_input.setObjectName("settingsInput")
        self.project_stack_input.setPlaceholderText("Preferred stack or tools")

        self.first_version_input = QLineEdit()
        self.first_version_input.setObjectName("settingsInput")
        self.first_version_input.setPlaceholderText("First version or first milestone")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._make_field("Project name", self.project_name_input))
        layout.addWidget(self._make_field("Project type", self.project_type_input))
        layout.addWidget(self._make_field("Goal", self.project_goal_input))
        layout.addWidget(self._make_field("Preferred stack", self.project_stack_input))
        layout.addWidget(self._make_field("First version", self.first_version_input))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_field(self, label_text: str, widget: QWidget) -> QWidget:
        field = QWidget()
        field_layout = QVBoxLayout(field)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("settingsFieldLabel")
        field_layout.addWidget(label)
        field_layout.addWidget(widget)
        return field

    def build_request(self) -> tuple[str, str]:
        project_name = self.project_name_input.text().strip() or "New Project"
        project_type = self.project_type_input.currentText().strip()
        goal = self.project_goal_input.toPlainText().strip() or "Create a clear first version."
        stack = self.project_stack_input.text().strip() or "No preferred stack specified"
        first_version = self.first_version_input.text().strip() or "Define the first shippable milestone"

        request = (
            f"Project name: {project_name}\n"
            f"Project type: {project_type}\n"
            f"Goal: {goal}\n"
            f"Preferred stack: {stack}\n"
            f"First version: {first_version}"
        )
        return project_name, request


class ChatArea(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.chat_layout = QVBoxLayout(self)
        self.chat_layout.setContentsMargins(36, 22, 36, 22)
        self.chat_layout.setSpacing(0)
        self.chat_layout.addStretch()

    def add_message(self, sender: str, text: str, is_user: bool = False) -> None:
        bubble = MessageBubble(sender, text, is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

    def clear_messages(self) -> None:
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


class LunaMainWindow(QMainWindow):
    def __init__(self, engine: Any) -> None:
        super().__init__()
        self.engine = engine
        self.worker_thread: QThread | None = None
        self.worker: ResponseWorker | None = None
        self.pending_thinking: TypingBubble | None = None
        self.reveal_timer: QTimer | None = None
        self.reveal_bubble: MessageBubble | None = None
        self.reveal_tokens: list[str] = []
        self.reveal_text = ""
        self.pending_attachments: list[str] = []
        self.sidebar_expanded_width = 264
        self.sidebar_visible = True
        self.sidebar_animation: QParallelAnimationGroup | None = None
        self.chat_transition_animation: QParallelAnimationGroup | None = None

        self.setWindowTitle("LunaAI")
        self.resize(1440, 920)
        self.setMinimumSize(1180, 760)

        root = QWidget()
        self.setCentralWidget(root)

        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_sidebar_rail())
        shell.addWidget(self._build_sidebar())
        shell.addWidget(self._build_main_area(), 1)

        self._apply_styles()
        self._apply_icons()
        self._refresh_chat_list()
        self._load_history()
        self._load_settings_values()
        self._refresh_profile_button()
        self._refresh_project_list()
        current_project = self.engine.projects.get_current_project() if hasattr(self.engine, "projects") else None
        self._load_project_into_studio(self.engine.get_project(current_project.id) if current_project is not None else None)
        self._update_empty_state()
        self.switch_page(0)
        QTimer.singleShot(0, self._scroll_chat_to_bottom)

    def _make_logo_label(self, size: int, object_name: str) -> QLabel:
        label = QLabel()
        label.setObjectName(object_name)
        label.setFixedSize(size, size)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if LOGO_PATH.exists():
            pixmap = QPixmap(str(LOGO_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                rounded = QPixmap(size, size)
                rounded.fill(Qt.GlobalColor.transparent)

                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                path = QPainterPath()
                radius = max(10.0, size * 0.22)
                path.addRoundedRect(0, 0, size, size, radius, radius)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled)
                painter.end()

                label.setPixmap(rounded)
                return label

        label.setText("L")
        return label

    def _build_sidebar_rail(self) -> QWidget:
        self.sidebar_rail = QFrame()
        self.sidebar_rail.setObjectName("sidebarRail")
        self.sidebar_rail.setFixedWidth(58)

        layout = QVBoxLayout(self.sidebar_rail)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(0)

        self.sidebar_toggle_button = QPushButton()
        self.sidebar_toggle_button.setObjectName("iconSidebarButton")
        self.sidebar_toggle_button.setToolTip("Show or hide sidebar")
        self.sidebar_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_button.setFixedSize(38, 38)
        self.sidebar_toggle_button.clicked.connect(self.toggle_sidebar)

        top_buttons = QVBoxLayout()
        top_buttons.setContentsMargins(0, 0, 0, 0)
        top_buttons.setSpacing(10)

        top_buttons.addWidget(self.sidebar_toggle_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.updates_button = QPushButton()
        self.updates_button.setObjectName("iconSidebarButton")
        self.updates_button.setToolTip("Aktualizace")
        self.updates_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.updates_button.setFixedSize(38, 38)
        self.updates_button.clicked.connect(lambda: self.switch_page(3))
        top_buttons.addWidget(self.updates_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addLayout(top_buttons)
        layout.addStretch(1)
        return self.sidebar_rail

    def _build_sidebar(self) -> QWidget:
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(self.sidebar_expanded_width)
        self.sidebar.setMaximumWidth(self.sidebar_expanded_width)
        self.sidebar_opacity = QGraphicsOpacityEffect(self.sidebar)
        self.sidebar_opacity.setOpacity(1.0)
        self.sidebar.setGraphicsEffect(self.sidebar_opacity)

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(9)
        brand_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brand_icon = self._make_logo_label(38, "brandIcon")
        brand_name = QLabel("LunaAI")
        brand_name.setObjectName("brandName")

        brand_row.addWidget(brand_icon)
        brand_row.addWidget(brand_name)

        self.new_chat_button = QPushButton("+ New chat")
        self.new_chat_button.setObjectName("primarySidebarButton")
        self.new_chat_button.clicked.connect(self.create_chat)

        self.chat_search_input = QLineEdit()
        self.chat_search_input.setObjectName("sidebarSearchInput")
        self.chat_search_input.setPlaceholderText("Hledat chaty")
        self.chat_search_input.textChanged.connect(self._refresh_chat_list)

        self.studio_button = QPushButton("Projects")
        self.studio_button.setObjectName("navButton")
        self.studio_button.clicked.connect(lambda: self.switch_page(1))

        self.gallery_button = QPushButton("Gallery")
        self.gallery_button.setObjectName("navButton")
        self.gallery_button.clicked.connect(lambda: self.switch_page(2))

        self.settings_button = QPushButton()
        self.settings_button.setObjectName("iconSidebarButton")
        self.settings_button.setToolTip("Settings")
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setFixedSize(42, 42)
        self.settings_button.clicked.connect(lambda: self.switch_page(4))

        self.chats_label = QLabel("Chats")
        self.chats_label.setObjectName("settingsFieldHelper")
        self.chat_list = QListWidget()
        self.chat_list.setObjectName("chatList")
        self.chat_list.itemClicked.connect(self._on_chat_selected)
        self.chat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_list.customContextMenuRequested.connect(self._show_chat_actions_menu)

        layout.addLayout(brand_row)
        layout.addWidget(self.new_chat_button)
        layout.addWidget(self.chat_search_input)
        layout.addWidget(self.studio_button)
        layout.addWidget(self.gallery_button)
        layout.addSpacing(8)
        layout.addWidget(self.chats_label)
        layout.addWidget(self.chat_list, 1)
        layout.addStretch(1)
        layout.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignHCenter)
        return self.sidebar

    def _build_main_area(self) -> QWidget:
        content = QFrame()
        content.setObjectName("content")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(20, 18, 20, 10)
        top_bar_layout.setSpacing(0)
        top_bar_layout.addStretch(1)

        self.profile_button = QPushButton("Profil")
        self.profile_button.setObjectName("secondaryButton")
        self.profile_button.setProperty("compact", True)
        self.profile_button.clicked.connect(self.show_profile_dialog)
        top_bar_layout.addWidget(self.profile_button, 0, Qt.AlignmentFlag.AlignRight)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_chat_page())
        self.pages.addWidget(self._build_studio_page())
        self.pages.addWidget(self._build_gallery_page())
        self.pages.addWidget(self._build_updates_page())
        self.pages.addWidget(self._build_settings_page())
        layout.addWidget(top_bar)
        layout.addWidget(self.pages, 1)
        return content

    def _apply_icons(self) -> None:
        style = self.style()
        self.new_chat_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.studio_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.gallery_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.updates_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.updates_button.setIconSize(QSize(16, 16))
        self.settings_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.settings_button.setIconSize(QSize(16, 16))
        self._update_sidebar_toggle_icon()
        self.send_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.empty_send_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.copy_blueprint_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.send_blueprint_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.generate_blueprint_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_CommandLink))
        self.create_project_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.gallery_refresh_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.gallery_import_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.gallery_open_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.settings_reload_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.settings_save_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self._refresh_profile_button()

    def toggle_sidebar(self) -> None:
        self.set_sidebar_visible(not self.sidebar_visible)

    def set_sidebar_visible(self, visible: bool) -> None:
        sidebar = getattr(self, "sidebar", None)
        if sidebar is None:
            return
        if self.sidebar_visible == visible and self.sidebar_animation is None:
            return

        self.sidebar_visible = visible
        self._update_sidebar_toggle_icon()

        if self.sidebar_animation is not None:
            self.sidebar_animation.stop()

        start_width = sidebar.maximumWidth()
        end_width = self.sidebar_expanded_width if visible else 0
        start_opacity = self.sidebar_opacity.opacity()
        end_opacity = 1.0 if visible else 0.0

        width_min = QPropertyAnimation(sidebar, b"minimumWidth", self)
        width_min.setDuration(220)
        width_min.setStartValue(start_width)
        width_min.setEndValue(end_width)
        width_min.setEasingCurve(QEasingCurve.Type.InOutCubic)

        width_max = QPropertyAnimation(sidebar, b"maximumWidth", self)
        width_max.setDuration(220)
        width_max.setStartValue(start_width)
        width_max.setEndValue(end_width)
        width_max.setEasingCurve(QEasingCurve.Type.InOutCubic)

        opacity_anim = QPropertyAnimation(self.sidebar_opacity, b"opacity", self)
        opacity_anim.setDuration(180)
        opacity_anim.setStartValue(start_opacity)
        opacity_anim.setEndValue(end_opacity)
        opacity_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        animation = QParallelAnimationGroup(self)
        animation.addAnimation(width_min)
        animation.addAnimation(width_max)
        animation.addAnimation(opacity_anim)

        def _finish() -> None:
            self.sidebar_animation = None
            sidebar.setMinimumWidth(end_width)
            sidebar.setMaximumWidth(end_width)
            self.sidebar_opacity.setOpacity(end_opacity)

        animation.finished.connect(_finish)
        self.sidebar_animation = animation
        animation.start()

    def _update_sidebar_toggle_icon(self) -> None:
        button = getattr(self, "sidebar_toggle_button", None)
        if button is None:
            return
        icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_TitleBarUnshadeButton
            if self.sidebar_visible
            else QStyle.StandardPixmap.SP_TitleBarShadeButton
        )
        button.setIcon(icon)
        button.setIconSize(QSize(16, 16))

    def show_profile_dialog(self) -> None:
        workspace = self.engine.user_settings.load() if hasattr(self.engine, "user_settings") else None
        profile_rows = [
            ("Email", workspace.google_email if workspace is not None and workspace.google_email else "Not set"),
            ("GitHub", workspace.github_username if workspace is not None and workspace.github_username else "Not connected"),
            ("Workspace", str(Path.cwd())),
        ]

        system = _read_system_overview()
        system_rows = [
            ("User", system.get("User", "Unknown")),
            ("Host", system.get("Host", "Unknown")),
            ("Device", system.get("Device", "Unknown")),
            ("OS", system.get("OS", "Unknown")),
            ("Architecture", system.get("Architecture", "Unknown")),
            ("CPU", system.get("CPU", "Unknown")),
            ("GPU", system.get("GPU", "Unknown")),
            ("Memory", system.get("Memory", "Unknown")),
            ("Python", system.get("Python", "Unknown")),
        ]

        dialog = ProfileDialog(
            profile_rows,
            system_rows,
            workspace.profile_image_path if workspace is not None else "",
            workspace.profile_display_name if workspace is not None else "",
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted and workspace is not None:
            workspace.profile_image_path = dialog.profile_image_path
            workspace.profile_display_name = dialog.profile_display_name
            self.engine.user_settings.save(workspace)
            self._refresh_profile_button()



    def _refresh_profile_button(self) -> None:
        button = getattr(self, "profile_button", None)
        if button is None or not hasattr(self.engine, "user_settings"):
            return
        workspace = self.engine.user_settings.load()
        display_name = workspace.profile_display_name.strip() if getattr(workspace, "profile_display_name", "") else "Profil"
        button.setText(display_name)
        fallback = display_name[:1] or "L"
        icon_pixmap = _build_profile_pixmap(getattr(workspace, "profile_image_path", ""), 28, fallback, 10.0)
        button.setIcon(QIcon(icon_pixmap))
        button.setIconSize(QSize(28, 28))

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(10)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        self.header_title = QLabel("Luna")
        self.header_title.setObjectName("titleLabel")
        self.header_subtitle = QLabel("Your local AI workspace.")
        self.header_subtitle.setObjectName("subtitleLabel")

        title_block.addWidget(self.header_title)
        title_block.addWidget(self.header_subtitle)

        layout.addLayout(title_block)
        layout.addStretch()
        return header

    def _build_chat_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll_opacity = QGraphicsOpacityEffect(self.chat_scroll)
        self.chat_scroll_opacity.setOpacity(1.0)
        self.chat_scroll.setGraphicsEffect(self.chat_scroll_opacity)
        self.chat_area = ChatArea()
        self.chat_scroll.setWidget(self.chat_area)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("emptyState")
        self.empty_state_opacity = QGraphicsOpacityEffect(self.empty_state)
        self.empty_state_opacity.setOpacity(1.0)
        self.empty_state.setGraphicsEffect(self.empty_state_opacity)
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(32, 0, 32, 0)
        empty_layout.setSpacing(18)
        empty_layout.addStretch(1)

        empty_center = QWidget()
        empty_center_layout = QVBoxLayout(empty_center)
        empty_center_layout.setContentsMargins(0, 0, 0, 0)
        empty_center_layout.setSpacing(14)
        empty_center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_title = QLabel("LunaAI")
        empty_title.setObjectName("emptyStateTitle")
        empty_subtitle = QLabel("Napis Lune, co chces vytvorit, vyresit nebo pochopit.")
        empty_subtitle.setObjectName("emptyStateSubtitle")

        self.empty_attachment_row = QWidget()
        self.empty_attachment_row.setObjectName("attachmentRow")
        self.empty_attachment_layout = QHBoxLayout(self.empty_attachment_row)
        self.empty_attachment_layout.setContentsMargins(0, 0, 0, 0)
        self.empty_attachment_layout.setSpacing(8)
        self.empty_attachment_row.hide()

        self.empty_composer = QFrame()
        self.empty_composer.setObjectName("composer")
        self.empty_composer.setMinimumWidth(820)
        self.empty_composer.setMaximumWidth(1080)
        self.empty_composer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.empty_composer.setGraphicsEffect(_make_shadow(34.0, 10.0, 75))
        empty_composer_layout = QHBoxLayout(self.empty_composer)
        empty_composer_layout.setContentsMargins(18, 10, 10, 10)
        empty_composer_layout.setSpacing(10)

        self.empty_plus_button = QPushButton("+")
        self.empty_plus_button.setObjectName("composerPlusButton")
        self.empty_plus_button.clicked.connect(lambda: self._show_composer_menu(self.empty_plus_button))

        self.empty_message_input = ExpandingMessageInput()
        self.empty_message_input.setPlaceholderText("Napis Lune cokoli...")
        self.empty_message_input.submit_requested.connect(self.send_message)

        self.empty_send_button = QPushButton("Send")
        self.empty_send_button.setObjectName("sendButton")
        self.empty_send_button.clicked.connect(self.send_message)

        empty_composer_layout.addWidget(self.empty_plus_button)
        empty_composer_layout.addWidget(self.empty_message_input, 1)
        empty_composer_layout.addWidget(self.empty_send_button)

        empty_center_layout.addWidget(empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_center_layout.addWidget(empty_subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_center_layout.addWidget(self.empty_attachment_row)
        empty_center_layout.addWidget(self.empty_composer)

        empty_layout.addWidget(empty_center)
        empty_layout.addStretch(1)

        self.chat_stack = QStackedWidget()
        self.chat_stack.addWidget(self.empty_state)
        self.chat_stack.addWidget(self.chat_scroll)

        self.attachment_row = QWidget()
        self.attachment_row.setObjectName("attachmentRow")
        self.attachment_layout = QHBoxLayout(self.attachment_row)
        self.attachment_layout.setContentsMargins(28, 8, 28, 0)
        self.attachment_layout.setSpacing(8)
        self.attachment_row.hide()

        self.composer_shell = QFrame()
        self.composer_shell.setObjectName("composerShell")
        composer_layout = QHBoxLayout(self.composer_shell)
        composer_layout.setContentsMargins(24, 14, 24, 20)

        self.composer = QFrame()
        self.composer.setObjectName("composer")
        self.composer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.composer.setGraphicsEffect(_make_shadow(30.0, 8.0, 65))
        inner_layout = QHBoxLayout(self.composer)
        inner_layout.setContentsMargins(18, 10, 10, 10)
        inner_layout.setSpacing(10)

        self.plus_button = QPushButton("+")
        self.plus_button.setObjectName("composerPlusButton")
        self.plus_button.clicked.connect(lambda: self._show_composer_menu(self.plus_button))

        self.message_input = ExpandingMessageInput()
        self.message_input.setPlaceholderText("Napis Lune cokoli...")
        self.message_input.submit_requested.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)

        inner_layout.addWidget(self.plus_button)
        inner_layout.addWidget(self.message_input, 1)
        inner_layout.addWidget(self.send_button)
        composer_layout.addWidget(self.composer)

        layout.addWidget(self.chat_stack, 1)
        layout.addWidget(self.attachment_row)
        layout.addWidget(self.composer_shell)
        return page

    def _build_studio_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(14)

        intro = QLabel(
            "Projects turns an idea into a saved plan, memory track, and next step you can continue later."
        )
        intro.setObjectName("subtitleLabel")
        intro.setWordWrap(True)

        split = QHBoxLayout()
        split.setSpacing(14)

        projects_card, projects_layout = self._make_settings_card(
            "Project List",
            "Saved projects with their latest phase and next step.",
        )
        projects_card.setMinimumWidth(304)
        projects_card.setMaximumWidth(344)

        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        self.project_list.itemClicked.connect(self._on_project_selected)

        self.create_project_button = QPushButton("New project")
        self.create_project_button.setObjectName("secondaryButton")
        self.create_project_button.clicked.connect(self.open_project_dialog)

        projects_layout.addWidget(self.project_list, 1)
        projects_layout.addWidget(self.create_project_button)

        right_column = QVBoxLayout()
        right_column.setSpacing(14)

        planner_card, planner_layout = self._make_settings_card(
            "Project Studio",
            "Shape a clear blueprint, then send it back to Luna for execution help.",
        )

        project_header = QHBoxLayout()
        project_header.setSpacing(12)

        self.project_title_label = QLabel("No project selected")
        self.project_title_label.setObjectName("settingsSectionTitle")

        project_header.addWidget(self.project_title_label)
        project_header.addStretch()

        self.studio_input = QTextEdit()
        self.studio_input.setObjectName("studioInput")
        self.studio_input.setPlaceholderText("Describe the product, users, stack, and first version...")

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()

        self.copy_blueprint_button = QPushButton("Copy")
        self.copy_blueprint_button.setObjectName("secondaryButton")
        self.copy_blueprint_button.clicked.connect(self.copy_blueprint)

        self.send_blueprint_button = QPushButton("Send To Assistant")
        self.send_blueprint_button.setObjectName("secondaryButton")
        self.send_blueprint_button.clicked.connect(self.send_blueprint_to_chat)

        self.generate_blueprint_button = QPushButton("Generate Blueprint")
        self.generate_blueprint_button.setObjectName("sendButton")
        self.generate_blueprint_button.clicked.connect(self.generate_blueprint)

        actions.addWidget(self.copy_blueprint_button)
        actions.addWidget(self.send_blueprint_button)
        actions.addWidget(self.generate_blueprint_button)

        self.studio_output = QTextEdit()
        self.studio_output.setObjectName("studioOutput")
        self.studio_output.setReadOnly(True)

        planner_layout.addLayout(project_header)
        planner_layout.addWidget(self.studio_input, 1)
        planner_layout.addLayout(actions)
        planner_layout.addWidget(self.studio_output, 1)

        task_card, task_layout = self._make_settings_card(
            "Task Center",
            "What the planning layer thinks should happen next.",
        )

        self.task_phase_label = QLabel("Current phase: draft")
        self.task_phase_label.setObjectName("settingsFieldLabel")
        self.xeno_status_label = QLabel("Xeno and the agent stay in the background until this project needs deeper help.")
        self.xeno_status_label.setObjectName("settingsFieldHelper")
        self.xeno_status_label.setWordWrap(True)
        self.task_next_step_label = QLabel("Next step: Create or select a project to start planning.")
        self.task_next_step_label.setObjectName("settingsFieldHelper")
        self.task_next_step_label.setWordWrap(True)
        self.task_detail_label = QLabel("Select a task to see more detail.")
        self.task_detail_label.setObjectName("settingsFieldHelper")
        self.task_detail_label.setWordWrap(True)
        self.task_list = QListWidget()
        self.task_list.setObjectName("taskList")
        self.task_list.itemClicked.connect(self._on_task_selected)

        task_actions = QHBoxLayout()
        task_actions.setSpacing(8)
        self.task_mark_done_button = QPushButton("Mark done")
        self.task_mark_done_button.setObjectName("secondaryButton")
        self.task_mark_done_button.clicked.connect(self.mark_selected_task_done)
        self.task_run_button = QPushButton("Run task action")
        self.task_run_button.setObjectName("secondaryButton")
        self.task_run_button.clicked.connect(self.run_selected_task_action)
        self.task_send_button = QPushButton("Send task to Luna")
        self.task_send_button.setObjectName("secondaryButton")
        self.task_send_button.clicked.connect(self.send_selected_task_to_chat)
        task_actions.addWidget(self.task_mark_done_button)
        task_actions.addWidget(self.task_run_button)
        task_actions.addWidget(self.task_send_button)
        task_actions.addStretch()

        memory_card, memory_layout = self._make_settings_card(
            "Project Memory",
            "Notes, linked files, and decisions that stay with this project.",
        )

        self.project_memory_summary = QLabel("No project memory yet.")
        self.project_memory_summary.setObjectName("settingsFieldHelper")
        self.project_memory_summary.setWordWrap(True)
        self.project_memory_list = QListWidget()
        self.project_memory_list.setObjectName("taskList")
        self.project_note_input = QLineEdit()
        self.project_note_input.setObjectName("settingsInput")
        self.project_note_input.setPlaceholderText("Add a note, decision, or reminder to this project")
        self.project_note_save_button = QPushButton("Save note")
        self.project_note_save_button.setObjectName("secondaryButton")
        self.project_note_save_button.clicked.connect(self.save_project_note)

        memory_layout.addWidget(self.project_memory_summary)
        memory_layout.addWidget(self.project_memory_list)
        memory_layout.addWidget(self.project_note_input)
        memory_layout.addWidget(self.project_note_save_button)

        task_layout.addWidget(self.task_phase_label)
        task_layout.addWidget(self.xeno_status_label)
        task_layout.addWidget(self.task_next_step_label)
        task_layout.addWidget(self.task_detail_label)
        task_layout.addWidget(self.task_list)
        task_layout.addLayout(task_actions)

        right_column.addWidget(planner_card, 2)
        right_column.addWidget(task_card, 1)
        right_column.addWidget(memory_card, 1)

        split.addWidget(projects_card)
        split.addLayout(right_column, 1)

        layout.addWidget(intro)
        layout.addLayout(split, 1)
        return page

    def _make_settings_field(self, label_text: str, widget: QWidget, helper_text: str = "") -> QWidget:
        field = QWidget()
        field.setObjectName("settingsField")
        layout = QVBoxLayout(field)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setObjectName("settingsFieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)

        if helper_text:
            helper = QLabel(helper_text)
            helper.setObjectName("settingsFieldHelper")
            helper.setWordWrap(True)
            layout.addWidget(helper)

        return field

    def _make_browse_settings_field(
        self,
        label_text: str,
        widget: QLineEdit,
        browse_caption: str,
        helper_text: str = "",
        app_key: str = "",
    ) -> QWidget:
        field = QWidget()
        field.setObjectName("settingsField")
        layout = QVBoxLayout(field)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setObjectName("settingsFieldLabel")
        layout.addWidget(label)

        layout.addWidget(widget)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)

        browse_button = QPushButton("Browse")
        browse_button.setObjectName("secondaryButton")
        browse_button.setProperty("compact", True)
        browse_button.clicked.connect(lambda: self._browse_for_path(widget, browse_caption))
        actions.addWidget(browse_button)

        if app_key:
            open_button = QPushButton("Open")
            open_button.setObjectName("secondaryButton")
            open_button.setProperty("compact", True)
            open_button.clicked.connect(lambda: self._open_connected_app(app_key, widget))
            actions.addWidget(open_button)

        actions.addStretch(1)
        layout.addLayout(actions)

        if helper_text:
            helper = QLabel(helper_text)
            helper.setObjectName("settingsFieldHelper")
            helper.setWordWrap(True)
            layout.addWidget(helper)

        return field

    def _build_updates_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(18)

        hero = QLabel("Updates")
        hero.setObjectName("emptyStateTitle")
        subtitle = QLabel("Patch notes, unlocked capabilities, and system upgrades for Luna, Xeno, and the agent.")
        subtitle.setObjectName("emptyStateSubtitle")
        subtitle.setWordWrap(True)

        card, card_layout = self._make_settings_card(
            "Patch 0.4 - System Layers",
            "The first pass that makes Luna feel more like a real AI system than a simple chat app.",
        )
        notes = QListWidget()
        notes.setObjectName("taskList")
        for line in [
            "New - Gallery for AI images and videos",
            "New - Profile with image and display name",
            "Improved - Smooth sidebar hide and show transition",
            "Improved - Empty chat now fades into conversation",
            "Unlocked - Automatic capture of media files returned by Luna",
            "System note - Luna, Xeno, memory, and agents now feel more unified",
        ]:
            notes.addItem(QListWidgetItem(line))
        card_layout.addWidget(notes)

        layout.addWidget(hero)
        layout.addWidget(subtitle)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _build_gallery_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        intro = QLabel("Gallery keeps AI images and videos in one local place so they are easy to revisit later.")
        intro.setObjectName("subtitleLabel")
        intro.setWordWrap(True)

        split = QHBoxLayout()
        split.setSpacing(18)

        library_card, library_layout = self._make_settings_card(
            "Gallery",
            "AI images and videos saved locally inside Luna.",
        )
        library_card.setMinimumWidth(304)
        library_card.setMaximumWidth(344)

        self.gallery_list = QListWidget()
        self.gallery_list.setObjectName("projectList")
        self.gallery_list.itemClicked.connect(self._on_gallery_selected)

        gallery_actions = QHBoxLayout()
        gallery_actions.setSpacing(10)
        self.gallery_import_button = QPushButton("Add media")
        self.gallery_import_button.setObjectName("secondaryButton")
        self.gallery_import_button.clicked.connect(self.import_gallery_media)
        self.gallery_refresh_button = QPushButton("Refresh")
        self.gallery_refresh_button.setObjectName("secondaryButton")
        self.gallery_refresh_button.clicked.connect(self.refresh_gallery)
        gallery_actions.addWidget(self.gallery_import_button)
        gallery_actions.addWidget(self.gallery_refresh_button)

        library_layout.addWidget(self.gallery_list, 1)
        library_layout.addLayout(gallery_actions)

        preview_card, preview_layout = self._make_settings_card(
            "Preview",
            "Selected AI output with a quick visual preview and file details.",
        )
        self.gallery_preview_title = QLabel("No media selected")
        self.gallery_preview_title.setObjectName("settingsSectionTitle")
        self.gallery_preview_meta = QLabel("Import or select an image or video from the gallery.")
        self.gallery_preview_meta.setObjectName("settingsFieldHelper")
        self.gallery_preview_meta.setWordWrap(True)
        self.gallery_preview_media = QLabel()
        self.gallery_preview_media.setObjectName("galleryPreview")
        self.gallery_preview_media.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gallery_preview_media.setMinimumHeight(360)
        self.gallery_preview_media.setWordWrap(True)
        gallery_preview_actions = QHBoxLayout()
        gallery_preview_actions.setSpacing(10)

        self.gallery_open_button = QPushButton("Open file")
        self.gallery_open_button.setObjectName("secondaryButton")
        self.gallery_open_button.clicked.connect(self.open_selected_gallery_item)
        self.gallery_open_button.setEnabled(False)

        self.gallery_delete_button = QPushButton("Delete")
        self.gallery_delete_button.setObjectName("secondaryButton")
        self.gallery_delete_button.clicked.connect(self.delete_selected_gallery_item)
        self.gallery_delete_button.setEnabled(False)

        gallery_preview_actions.addWidget(self.gallery_open_button)
        gallery_preview_actions.addWidget(self.gallery_delete_button)
        gallery_preview_actions.addStretch(1)

        preview_layout.addWidget(self.gallery_preview_title)
        preview_layout.addWidget(self.gallery_preview_meta)
        preview_layout.addWidget(self.gallery_preview_media, 1)
        preview_layout.addLayout(gallery_preview_actions)

        split.addWidget(library_card)
        split.addWidget(preview_card, 1)

        layout.addWidget(intro)
        layout.addLayout(split, 1)
        self.refresh_gallery()
        return page

    def refresh_gallery(self) -> None:
        if not hasattr(self, "gallery_list"):
            return
        GALLERY_PATH.mkdir(parents=True, exist_ok=True)
        self.gallery_list.clear()
        files = [p for p in GALLERY_PATH.iterdir() if p.is_file() and (_is_image_path(str(p)) or _is_video_path(str(p)))]
        files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        style = self.style()
        image_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        video_icon = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        for file_path in files:
            icon = image_icon if _is_image_path(str(file_path)) else video_icon
            kind = "Image" if _is_image_path(str(file_path)) else "Video"
            item = QListWidgetItem(icon, f"{file_path.stem}\n{kind}")
            item.setData(Qt.ItemDataRole.UserRole, str(file_path))
            self.gallery_list.addItem(item)
        if self.gallery_list.count() == 0:
            self.gallery_preview_title.setText("No media yet")
            self.gallery_preview_meta.setText("Use Add media to place AI images and videos into Luna's local gallery.")
            self.gallery_preview_media.setPixmap(QPixmap())
            self.gallery_preview_media.setText("Gallery is empty")
            self.gallery_open_button.setEnabled(False)
            self.gallery_delete_button.setEnabled(False)

    def import_gallery_media(self) -> None:
        GALLERY_PATH.mkdir(parents=True, exist_ok=True)
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add images or videos to gallery",
            str(Path.home()),
            "Media (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.mp4 *.mov *.avi *.mkv *.webm *.m4v)",
        )
        if not files:
            return
        for file_path in files:
            source = Path(file_path)
            target = GALLERY_PATH / source.name
            if target.exists():
                stem = source.stem
                suffix = source.suffix
                index = 2
                while target.exists():
                    target = GALLERY_PATH / f"{stem}_{index}{suffix}"
                    index += 1
            try:
                shutil.copy2(source, target)
            except OSError:
                continue
        self.refresh_gallery()

    def _on_gallery_selected(self, item: QListWidgetItem) -> None:
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(file_path, str):
            return
        path = Path(file_path)
        if not path.exists():
            return

        self.gallery_preview_title.setText(path.stem)
        kind = "Image" if _is_image_path(file_path) else "Video"
        size_mb = path.stat().st_size / (1024 * 1024)
        self.gallery_preview_meta.setText(f"{kind} - {path.suffix.lower()} - {size_mb:.2f} MB")
        self.gallery_open_button.setEnabled(True)
        self.gallery_delete_button.setEnabled(True)

        if _is_image_path(file_path):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(720, 420, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.gallery_preview_media.setPixmap(scaled)
                self.gallery_preview_media.setText("")
                return

        self.gallery_preview_media.setPixmap(QPixmap())
        self.gallery_preview_media.setText(
            f"{kind} preview\n\n{path.name}\n\nInline video playback is not enabled yet, but the file is saved in Luna's local gallery."
        )

    def delete_selected_gallery_item(self) -> None:
        item = self.gallery_list.currentItem()
        if item is None:
            return
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(file_path, str):
            return
        path = Path(file_path)
        if not path.exists():
            self.refresh_gallery()
            return
        answer = QMessageBox.question(
            self,
            "Delete media",
            f"Delete {path.name} from Luna's gallery?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            path.unlink()
        except OSError:
            QMessageBox.warning(self, "Delete media", "This file could not be deleted.")
            return
        self.refresh_gallery()

    def _store_media_in_gallery(self, source_path: Path) -> Path | None:
        if not source_path.exists() or not source_path.is_file():
            return None
        if not (_is_image_path(str(source_path)) or _is_video_path(str(source_path))):
            return None

        GALLERY_PATH.mkdir(parents=True, exist_ok=True)
        try:
            if source_path.parent.resolve() == GALLERY_PATH.resolve():
                return source_path
        except OSError:
            pass

        target = GALLERY_PATH / source_path.name
        if target.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            index = 2
            while target.exists():
                target = GALLERY_PATH / f"{stem}_{index}{suffix}"
                index += 1
        try:
            shutil.copy2(source_path, target)
        except OSError:
            return None
        return target

    def _capture_generated_media(self, response: str) -> None:
        stored_any = False
        for media_path in _extract_media_paths_from_text(response):
            if self._store_media_in_gallery(media_path) is not None:
                stored_any = True
        if stored_any:
            self.refresh_gallery()

    def open_selected_gallery_item(self) -> None:
        item = self.gallery_list.currentItem()
        if item is None:
            return
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(file_path, str):
            return
        if Path(file_path).exists():
            os.startfile(file_path)

    def _make_settings_card(self, title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        heading = QLabel(title)
        heading.setObjectName("settingsSectionTitle")
        layout.addWidget(heading)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("settingsFieldHelper")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        return card, layout

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(30, 18, 30, 28)
        root_layout.setSpacing(20)

        nav_card, nav_layout = self._make_settings_card(
            "Settings folders",
            "Everything is grouped here so the settings page stays clean.",
        )
        nav_card.setMinimumWidth(210)
        nav_card.setMaximumWidth(232)

        self.settings_nav_runtime = QPushButton("Runtime")
        self.settings_nav_runtime.setObjectName("settingsFolderButton")
        self.settings_nav_apps = QPushButton("Apps")
        self.settings_nav_apps.setObjectName("settingsFolderButton")
        self.settings_nav_accounts = QPushButton("Accounts")
        self.settings_nav_accounts.setObjectName("settingsFolderButton")

        nav_layout.addWidget(self.settings_nav_runtime)
        nav_layout.addWidget(self.settings_nav_apps)
        nav_layout.addWidget(self.settings_nav_accounts)
        nav_layout.addStretch()

        self.settings_stack = QStackedWidget()

        runtime_page = QWidget()
        runtime_layout = QVBoxLayout(runtime_page)
        runtime_layout.setContentsMargins(0, 0, 0, 0)
        runtime_layout.setSpacing(16)

        intro = QLabel("Control how Luna connects, thinks, and works with the local backend.")
        intro.setObjectName("subtitleLabel")
        intro.setWordWrap(True)

        connection_card, connection_layout = self._make_settings_card(
            "Runtime",
            "Core runtime settings for Luna. Model selection stays internal, but connection and behavior can be adjusted here.",
        )

        self.settings_url = QLineEdit()
        self.settings_url.setObjectName("settingsInput")
        self.settings_url.setPlaceholderText("LM Studio API URL")

        self.settings_token = QLineEdit()
        self.settings_token.setObjectName("settingsInput")
        self.settings_token.setPlaceholderText("LM Studio API token")
        self.settings_token.setEchoMode(QLineEdit.EchoMode.Password)

        self.settings_timeout = QLineEdit()
        self.settings_timeout.setObjectName("settingsInput")
        self.settings_timeout.setPlaceholderText("LM Studio timeout in seconds")

        self.settings_reasoning_box = QComboBox()
        self.settings_reasoning_box.setObjectName("settingsSelect")
        self.settings_reasoning_box.addItems(["black_box", "white_box"])

        self.settings_internet_enabled = QCheckBox("Allow Luna to use internet support when needed")
        self.settings_internet_enabled.setObjectName("settingsCheck")

        self.settings_internet_mode = QComboBox()
        self.settings_internet_mode.setObjectName("settingsSelect")
        self.settings_internet_mode.addItems(["auto", "manual"])

        connection_layout.addWidget(self._make_settings_field("API URL", self.settings_url, "The endpoint Luna uses to reach LM Studio or another compatible backend."))
        connection_layout.addWidget(self._make_settings_field("API Token", self.settings_token, "Stored locally for this workspace."))
        connection_layout.addWidget(self._make_settings_field("Request timeout", self.settings_timeout, "Increase this if your model loads slowly or replies take longer."))
        connection_layout.addWidget(self._make_settings_field("Default reasoning style", self.settings_reasoning_box))
        connection_layout.addWidget(self.settings_internet_enabled)
        connection_layout.addWidget(self._make_settings_field("Internet mode", self.settings_internet_mode))

        runtime_layout.addWidget(intro)
        runtime_layout.addWidget(connection_card)
        runtime_layout.addStretch()

        apps_page = QWidget()
        apps_layout_page = QVBoxLayout(apps_page)
        apps_layout_page.setContentsMargins(0, 0, 0, 0)
        apps_layout_page.setSpacing(16)

        apps_intro = QLabel("Connect local creative and development tools Luna can work with later through the agent layer.")
        apps_intro.setObjectName("subtitleLabel")
        apps_intro.setWordWrap(True)

        self.settings_unreal_path = QLineEdit()
        self.settings_unreal_path.setObjectName("settingsInput")
        self.settings_unreal_path.setPlaceholderText("Unreal Engine 5 path")

        self.settings_blender_path = QLineEdit()
        self.settings_blender_path.setObjectName("settingsInput")
        self.settings_blender_path.setPlaceholderText("Blender path")

        self.settings_flstudio_path = QLineEdit()
        self.settings_flstudio_path.setObjectName("settingsInput")
        self.settings_flstudio_path.setPlaceholderText("FL Studio path")

        self.settings_photoshop_path = QLineEdit()
        self.settings_photoshop_path.setObjectName("settingsInput")
        self.settings_photoshop_path.setPlaceholderText("Photoshop path")

        self.settings_vscode_path = QLineEdit()
        self.settings_vscode_path.setObjectName("settingsInput")
        self.settings_vscode_path.setPlaceholderText("VS Code path")

        self.settings_davinci_path = QLineEdit()
        self.settings_davinci_path.setObjectName("settingsInput")
        self.settings_davinci_path.setPlaceholderText("DaVinci Resolve path")

        self.settings_unity_path = QLineEdit()
        self.settings_unity_path.setObjectName("settingsInput")
        self.settings_unity_path.setPlaceholderText("Unity path")

        self.settings_premiere_path = QLineEdit()
        self.settings_premiere_path.setObjectName("settingsInput")
        self.settings_premiere_path.setPlaceholderText("Premiere Pro path")

        self.settings_after_effects_path = QLineEdit()
        self.settings_after_effects_path.setObjectName("settingsInput")
        self.settings_after_effects_path.setPlaceholderText("After Effects path")

        self.settings_figma_path = QLineEdit()
        self.settings_figma_path.setObjectName("settingsInput")
        self.settings_figma_path.setPlaceholderText("Figma path or desktop app path")

        self.settings_substance_painter_path = QLineEdit()
        self.settings_substance_painter_path.setObjectName("settingsInput")
        self.settings_substance_painter_path.setPlaceholderText("Substance 3D Painter path")

        dev_card, dev_layout = self._make_settings_card(
            "Development",
            "Tools Luna can treat as build and coding hands later.",
        )
        dev_layout.addWidget(
            self._make_browse_settings_field("Unreal Engine 5", self.settings_unreal_path, "Select Unreal Engine executable", "Path to the main Unreal executable or launcher.", "unreal")
        )
        dev_layout.addWidget(
            self._make_browse_settings_field("Unity", self.settings_unity_path, "Select Unity executable", "Optional if you also build Unity projects.", "unity")
        )
        dev_layout.addWidget(
            self._make_browse_settings_field("VS Code", self.settings_vscode_path, "Select VS Code executable", "Used when the agent opens project workspaces or code.", "vscode")
        )

        creative_card, creative_layout = self._make_settings_card(
            "Creative Apps",
            "Image, video, and 3D tools Luna can reference across creative workflows.",
        )
        creative_layout.addWidget(self._make_browse_settings_field("Blender", self.settings_blender_path, "Select Blender executable", app_key="blender"))
        creative_layout.addWidget(self._make_browse_settings_field("Photoshop", self.settings_photoshop_path, "Select Photoshop executable", app_key="photoshop"))
        creative_layout.addWidget(self._make_browse_settings_field("DaVinci Resolve", self.settings_davinci_path, "Select DaVinci Resolve executable", app_key="davinci"))
        creative_layout.addWidget(self._make_browse_settings_field("Premiere Pro", self.settings_premiere_path, "Select Premiere Pro executable", app_key="premiere"))
        creative_layout.addWidget(self._make_browse_settings_field("After Effects", self.settings_after_effects_path, "Select After Effects executable", app_key="after_effects"))
        creative_layout.addWidget(self._make_browse_settings_field("Substance 3D Painter", self.settings_substance_painter_path, "Select Substance 3D Painter executable", app_key="substance"))

        design_card, design_layout = self._make_settings_card(
            "Design and Audio",
            "Useful when Luna supports interface, concept, and music workflows.",
        )
        design_layout.addWidget(self._make_browse_settings_field("Figma", self.settings_figma_path, "Select Figma app or shortcut", app_key="figma"))
        design_layout.addWidget(self._make_browse_settings_field("FL Studio", self.settings_flstudio_path, "Select FL Studio executable", app_key="fl_studio"))

        apps_sections = QWidget()
        apps_sections_layout = QVBoxLayout(apps_sections)
        apps_sections_layout.setContentsMargins(0, 0, 0, 0)
        apps_sections_layout.setSpacing(16)
        apps_sections_layout.addWidget(dev_card)
        apps_sections_layout.addWidget(creative_card)
        apps_sections_layout.addWidget(design_card)
        apps_sections_layout.addStretch()

        apps_scroll = QScrollArea()
        apps_scroll.setObjectName("settingsScroll")
        apps_scroll.setWidgetResizable(True)
        apps_scroll.setFrameShape(QFrame.Shape.NoFrame)
        apps_scroll.setWidget(apps_sections)

        apps_layout_page.addWidget(apps_intro)
        apps_layout_page.addWidget(apps_scroll, 1)

        accounts_page = QWidget()
        accounts_layout_page = QVBoxLayout(accounts_page)
        accounts_layout_page.setContentsMargins(0, 0, 0, 0)
        accounts_layout_page.setSpacing(16)

        accounts_intro = QLabel("Local account links and identity settings for future integrations.")
        accounts_intro.setObjectName("subtitleLabel")
        accounts_intro.setWordWrap(True)

        accounts_card, accounts_layout = self._make_settings_card(
            "Accounts",
            "These stay local for now. Real OAuth-style sign-in can come later when we build the integrations fully.",
        )

        self.settings_github_username = QLineEdit()
        self.settings_github_username.setObjectName("settingsInput")
        self.settings_github_username.setPlaceholderText("GitHub username")

        self.settings_github_token = QLineEdit()
        self.settings_github_token.setObjectName("settingsInput")
        self.settings_github_token.setPlaceholderText("GitHub token")
        self.settings_github_token.setEchoMode(QLineEdit.EchoMode.Password)

        self.settings_google_email = QLineEdit()
        self.settings_google_email.setObjectName("settingsInput")
        self.settings_google_email.setPlaceholderText("Google account email")

        accounts_layout.addWidget(self._make_settings_field("GitHub username", self.settings_github_username))
        accounts_layout.addWidget(self._make_settings_field("GitHub token", self.settings_github_token))
        accounts_layout.addWidget(self._make_settings_field("Google account", self.settings_google_email))

        accounts_layout_page.addWidget(accounts_intro)
        accounts_layout_page.addWidget(accounts_card)
        accounts_layout_page.addStretch()

        self.settings_stack.addWidget(runtime_page)
        self.settings_stack.addWidget(apps_page)
        self.settings_stack.addWidget(accounts_page)

        self.settings_nav_runtime.clicked.connect(lambda: self._show_settings_section(0))
        self.settings_nav_apps.clicked.connect(lambda: self._show_settings_section(1))
        self.settings_nav_accounts.clicked.connect(lambda: self._show_settings_section(2))

        content_column = QVBoxLayout()
        content_column.setSpacing(14)
        content_column.addWidget(self.settings_stack, 1)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addStretch()

        self.settings_reload_button = QPushButton("Reload values")
        self.settings_reload_button.setObjectName("secondaryButton")
        self.settings_reload_button.clicked.connect(self._load_settings_values)

        self.settings_save_button = QPushButton("Save settings")
        self.settings_save_button.setObjectName("sendButton")
        self.settings_save_button.clicked.connect(self._save_settings)

        actions.addWidget(self.settings_reload_button)
        actions.addWidget(self.settings_save_button)

        self.settings_status = QLabel(
            "Settings are grouped into folders so runtime, apps, and accounts stay easy to manage."
        )
        self.settings_status.setObjectName("settingsStatus")
        self.settings_status.setWordWrap(True)

        content_column.addLayout(actions)
        content_column.addWidget(self.settings_status)

        root_layout.addWidget(nav_card)
        root_layout.addLayout(content_column, 1)

        outer_layout.addWidget(root)
        self._show_settings_section(0)
        return page

    def _show_settings_section(self, index: int) -> None:
        self.settings_stack.setCurrentIndex(index)
        buttons = [
            self.settings_nav_runtime,
            self.settings_nav_apps,
            self.settings_nav_accounts,
        ]
        for button_index, button in enumerate(buttons):
            button.setProperty("active", button_index == index)
            self.style().unpolish(button)
            self.style().polish(button)
            button.update()

    def switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def _refresh_chat_list(self) -> None:
        self.chat_list.clear()
        current_chat_id = self.engine.get_current_chat_id()
        query = self.chat_search_input.text().strip().lower() if hasattr(self, "chat_search_input") else ""
        style = self.style()
        chat_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        for chat in self.engine.list_chats():
            title = chat.get("title", "New chat")
            if query and query not in title.lower():
                continue
            item = QListWidgetItem(chat_icon, title)
            item.setData(Qt.ItemDataRole.UserRole, chat.get("id", ""))
            self.chat_list.addItem(item)
            if chat.get("id") == current_chat_id:
                self.chat_list.setCurrentItem(item)

    def _load_history(self) -> None:
        self.chat_area.clear_messages()
        history = self.engine.memory.load_history()
        for item in history:
            role = item.get("role", "assistant")
            content = item.get("content", "").strip()
            if not content:
                continue
            if role == "user":
                self.chat_area.add_message("You", content, True)
            else:
                cleaned = content.removeprefix("Luna: ") if content.startswith("Luna: ") else content
                self.chat_area.add_message("Luna", cleaned, False)
        self._update_empty_state()
        self._scroll_chat_to_bottom()

    def _on_chat_selected(self, item: QListWidgetItem) -> None:
        if self.worker_thread is not None or self.reveal_timer is not None:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(session_id, str) or not session_id:
            return
        self.engine.switch_chat(session_id)
        self.switch_page(0)
        self._load_history()
        self._refresh_chat_list()
    def create_chat(self) -> None:
        if self.worker_thread is not None or self.reveal_timer is not None:
            return
        self._remove_thinking_placeholder()
        self._stop_response_reveal()
        self._clear_attachments()
        self.engine.create_new_chat("New chat")
        self.switch_page(0)
        self.studio_output.clear()
        self.message_input.clear()
        self.empty_message_input.clear()
        self._load_history()
        self._refresh_chat_list()
        self._set_busy(False, "LunaAI")
        self.message_input.setFocus()

    def rename_selected_chat(self) -> None:
        if self.worker_thread is not None or self.reveal_timer is not None:
            return
        item = self.chat_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Rename chat", "Select a chat first.")
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        current_title = item.text().strip() or "New chat"
        if not isinstance(session_id, str) or not session_id:
            return

        title, ok = QInputDialog.getText(self, "Rename chat", "Chat name:", QLineEdit.EchoMode.Normal, current_title)
        if not ok:
            return
        clean_title = " ".join(title.strip().split())
        if not clean_title:
            QMessageBox.information(self, "Rename chat", "Chat name cannot be empty.")
            return

        self.engine.rename_chat(session_id, clean_title)
        self._refresh_chat_list()

    def delete_selected_chat(self) -> None:
        if self.worker_thread is not None or self.reveal_timer is not None:
            return
        item = self.chat_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Delete chat", "Select a chat first.")
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        title = item.text().strip() or "this chat"
        if not isinstance(session_id, str) or not session_id:
            return

        answer = QMessageBox.question(
            self,
            "Delete chat",
            f'Delete "{title}"? This chat history will be removed.',
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._remove_thinking_placeholder()
        self._stop_response_reveal()
        self.engine.delete_chat(session_id)
        self.switch_page(0)
        self._load_history()
        self._refresh_chat_list()
        self._set_busy(False, "LunaAI")

    def _refresh_project_list(self) -> None:
        if not hasattr(self, "project_list"):
            return
        self.project_list.clear()
        current_project = self.engine.get_current_project()
        current_project_id = str(current_project.get("id", "")) if current_project else ""

        style = self.style()
        project_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        for project in self.engine.list_projects():
            name = project.get("name", "New Project")
            phase = project.get("current_phase", "draft").replace("_", " ")
            task_count = project.get("task_count", "0")
            memory_count = project.get("memory_count", "0")
            label = f"{name}\n{phase.title()} - {task_count} tasks - {memory_count} notes"
            item = QListWidgetItem(project_icon, label)
            item.setData(Qt.ItemDataRole.UserRole, project.get("id", ""))
            self.project_list.addItem(item)
            if project.get("id") == current_project_id:
                self.project_list.setCurrentItem(item)

    def _update_task_center(self, tasks: list[dict[str, str]], current_phase: str, next_step: str, xeno_note: str = "") -> None:
        self.task_phase_label.setText(f"Current phase: {current_phase.replace('_', ' ')}")
        self.task_next_step_label.setText(f"Next step: {next_step}")
        self.xeno_status_label.setText(xeno_note or "Luna is active. Xeno and the task agent are quietly standing by inside the project flow.")
        self.task_detail_label.setText("Select a task to see more detail.")
        self.task_list.clear()
        for task in tasks:
            title = task.get("title", "Task")
            status = task.get("status", "pending").replace("_", " ")
            description = task.get("description", "")
            item = QListWidgetItem(f"{status.title()} - {title}")
            item.setToolTip(description)
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.task_list.addItem(item)

    def _update_project_memory(self, project: dict[str, object] | None) -> None:
        self.project_memory_list.clear()
        if project is None:
            self.project_memory_summary.setText("No project memory yet.")
            return

        memory_entries = project.get("memory_entries", [])
        attachment_names = project.get("attachment_names", [])
        if not isinstance(memory_entries, list):
            memory_entries = []
        if not isinstance(attachment_names, list):
            attachment_names = []

        self.project_memory_summary.setText(
            f"{len(memory_entries)} notes and {len(attachment_names)} linked files are attached to this project."
        )
        for entry in memory_entries:
            self.project_memory_list.addItem(QListWidgetItem(str(entry)))
        if attachment_names:
            self.project_memory_list.addItem(QListWidgetItem("Linked files: " + ", ".join(str(name) for name in attachment_names)))

    def _load_project_into_studio(self, project: dict[str, object] | None) -> None:
        if project is None:
            self.project_title_label.setText("No project selected")
            self.studio_input.clear()
            self.studio_output.clear()
            self._update_task_center([], "draft", "Create or select a project to start planning.")
            self._update_project_memory(None)
            return

        self.project_title_label.setText(str(project.get("name", "No project selected")))
        self.studio_input.setPlainText(str(project.get("brief", "")))
        self.studio_output.setPlainText(str(project.get("blueprint_text", "")))
        tasks = project.get("tasks", [])
        if not isinstance(tasks, list):
            tasks = []
        self._update_task_center(
            tasks,
            str(project.get("current_phase", "draft")),
            str(project.get("next_step", "Create a project blueprint.")),
            f"Xeno note: phase {str(project.get('current_phase', 'draft')).replace('_', ' ')} ready. Agent steps are available for Luna as hidden operational support.",
        )
        self._update_project_memory(project)

    def _on_project_selected(self, item: QListWidgetItem) -> None:
        project_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(project_id, str) or not project_id:
            return
        project = self.engine.set_current_project(project_id)
        self._load_project_into_studio(project)

    def _on_task_selected(self, item: QListWidgetItem) -> None:
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            self.task_detail_label.setText("Select a task to see more detail.")
            return
        self.task_detail_label.setText(str(task.get("description", "No details available.")))

    def _clear_attachment_layout(self, layout: QHBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh_attachment_rows(self) -> None:
        rows = [
            (self.attachment_row, self.attachment_layout),
            (self.empty_attachment_row, self.empty_attachment_layout),
        ]
        for row, row_layout in rows:
            self._clear_attachment_layout(row_layout)
            if not self.pending_attachments:
                row.hide()
                continue
            for file_path in self.pending_attachments:
                card = AttachmentCard(file_path)
                row_layout.addWidget(card)
            row_layout.addStretch()
            row.show()

    def _clear_attachments(self) -> None:
        self.pending_attachments.clear()
        self._refresh_attachment_rows()

    def mark_selected_task_done(self) -> None:
        project = self.engine.get_current_project()
        if project is None:
            QMessageBox.information(self, "Task Center", "Select a project first.")
            return
        item = self.task_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Task Center", "Select a task first.")
            return
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            return
        updated = self.engine.update_project_task_status(str(project.get("id", "")), str(task.get("title", "")), "completed")
        self._load_project_into_studio(updated)
        self._refresh_project_list()

    def send_selected_task_to_chat(self) -> None:
        item = self.task_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Task Center", "Select a task first.")
            return
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            return
        self.switch_page(0)
        self.message_input.setPlainTextAndMoveToEnd(
            f"Pomoz mi splnit tento ukol krok za krokem:\n\n{task.get('title', 'Task')}\n{task.get('description', '')}"
        )
        self.message_input.setFocus()

    def run_selected_task_action(self) -> None:
        project = self.engine.get_current_project()
        if project is None:
            QMessageBox.information(self, "Task Center", "Select a project first.")
            return
        item = self.task_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Task Center", "Select a task first.")
            return
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            return
        result = self.engine.run_agent_task_action(str(project.get("id", "")), str(task.get("title", "")))
        if not result.get("ok"):
            QMessageBox.information(self, "Task Center", str(result.get("message", "Action could not be completed.")))
            return
        refreshed_project = result.get("project")
        if isinstance(refreshed_project, dict):
            self._load_project_into_studio(refreshed_project)
            self._refresh_project_list()
        self.xeno_status_label.setText(str(result.get("message", "Task agent completed an action.")))

    def save_project_note(self) -> None:
        project = self.engine.get_current_project()
        if project is None:
            QMessageBox.information(self, "Project Memory", "Create or select a project first.")
            return
        note = self.project_note_input.text().strip()
        if not note:
            QMessageBox.information(self, "Project Memory", "Write a note first.")
            return
        updated = self.engine.add_project_memory(str(project.get("id", "")), note)
        self.project_note_input.clear()
        self._load_project_into_studio(updated)
        self._refresh_project_list()

    def _load_settings_values(self) -> None:
        settings = self.engine.settings
        workspace = self.engine.user_settings.data
        self.settings_url.setText(settings.lm_studio_base_url)
        self.settings_token.setText(settings.lm_studio_api_token)
        self.settings_timeout.setText(str(settings.lm_studio_timeout_seconds))
        self.settings_reasoning_box.setCurrentText(settings.default_reasoning_box)
        self.settings_internet_enabled.setChecked(bool(settings.internet_enabled))
        self.settings_internet_mode.setCurrentText(settings.internet_mode)
        self.settings_unreal_path.setText(workspace.unreal_engine_path)
        self.settings_blender_path.setText(workspace.blender_path)
        self.settings_flstudio_path.setText(workspace.fl_studio_path)
        self.settings_photoshop_path.setText(workspace.photoshop_path)
        self.settings_vscode_path.setText(workspace.vscode_path)
        self.settings_davinci_path.setText(workspace.davinci_resolve_path)
        self.settings_unity_path.setText(workspace.unity_path)
        self.settings_premiere_path.setText(workspace.premiere_pro_path)
        self.settings_after_effects_path.setText(workspace.after_effects_path)
        self.settings_figma_path.setText(workspace.figma_path)
        self.settings_substance_painter_path.setText(workspace.substance_painter_path)
        self.settings_github_username.setText(workspace.github_username)
        self.settings_github_token.setText(workspace.github_token)
        self.settings_google_email.setText(workspace.google_email)


    def _save_settings(self) -> None:
        base_url = self.settings_url.text().strip()
        token = self.settings_token.text().strip()
        timeout_text = self.settings_timeout.text().strip()
        reasoning_box = self.settings_reasoning_box.currentText().strip()
        internet_enabled = self.settings_internet_enabled.isChecked()
        internet_mode = self.settings_internet_mode.currentText().strip()

        if not base_url:
            QMessageBox.information(self, "Settings", "API URL is required.")
            return

        if not timeout_text.isdigit():
            QMessageBox.information(self, "Settings", "Timeout must be a whole number.")
            return

        timeout_seconds = int(timeout_text)
        if timeout_seconds < 5:
            QMessageBox.information(self, "Settings", "Timeout should be at least 5 seconds.")
            return

        content = CONFIG_PATH.read_text(encoding="utf-8")
        content = re.sub(r'LM_STUDIO_BASE_URL = ".*?"', f'LM_STUDIO_BASE_URL = "{base_url}"', content)
        content = re.sub(r'LM_STUDIO_API_TOKEN = ".*?"', f'LM_STUDIO_API_TOKEN = "{token}"', content)
        content = re.sub(r'LM_STUDIO_TIMEOUT_SECONDS = \d+', f'LM_STUDIO_TIMEOUT_SECONDS = {timeout_seconds}', content)
        content = re.sub(r'DEFAULT_REASONING_BOX = ".*?"', f'DEFAULT_REASONING_BOX = "{reasoning_box}"', content)
        content = re.sub(r'INTERNET_ENABLED = \(True\|False\)', f'INTERNET_ENABLED = {internet_enabled}', content)
        content = re.sub(r'INTERNET_ENABLED = (True|False)', f'INTERNET_ENABLED = {internet_enabled}', content)
        content = re.sub(r'INTERNET_MODE = ".*?"', f'INTERNET_MODE = "{internet_mode}"', content)
        CONFIG_PATH.write_text(content, encoding="utf-8")

        self.engine.settings.lm_studio_base_url = base_url
        self.engine.settings.lm_studio_api_token = token
        self.engine.settings.lm_studio_timeout_seconds = timeout_seconds
        self.engine.settings.default_reasoning_box = reasoning_box
        self.engine.settings.internet_enabled = internet_enabled
        self.engine.settings.internet_mode = internet_mode
        self.engine.model.url = base_url
        self.engine.model.api_token = token
        self.engine.model.timeout_seconds = timeout_seconds
        self.engine.internet.set_enabled(internet_enabled)
        self.engine.internet.set_mode(internet_mode)

        workspace = self.engine.user_settings.data
        workspace.unreal_engine_path = self.settings_unreal_path.text().strip()
        workspace.blender_path = self.settings_blender_path.text().strip()
        workspace.fl_studio_path = self.settings_flstudio_path.text().strip()
        workspace.photoshop_path = self.settings_photoshop_path.text().strip()
        workspace.vscode_path = self.settings_vscode_path.text().strip()
        workspace.davinci_resolve_path = self.settings_davinci_path.text().strip()
        workspace.unity_path = self.settings_unity_path.text().strip()
        workspace.premiere_pro_path = self.settings_premiere_path.text().strip()
        workspace.after_effects_path = self.settings_after_effects_path.text().strip()
        workspace.figma_path = self.settings_figma_path.text().strip()
        workspace.substance_painter_path = self.settings_substance_painter_path.text().strip()
        workspace.github_username = self.settings_github_username.text().strip()
        workspace.github_token = self.settings_github_token.text().strip()
        workspace.google_email = self.settings_google_email.text().strip()
        self.engine.user_settings.save(workspace)

        self.settings_status.setText("Settings saved locally and applied to the current Luna session.")

    def _open_connected_app(self, app_key: str, widget: QLineEdit) -> None:
        current_path = widget.text().strip()
        workspace = self.engine.user_settings.data
        field_map = {
            "unreal": "unreal_engine_path",
            "blender": "blender_path",
            "fl_studio": "fl_studio_path",
            "photoshop": "photoshop_path",
            "vscode": "vscode_path",
            "davinci": "davinci_resolve_path",
            "unity": "unity_path",
            "premiere": "premiere_pro_path",
            "after_effects": "after_effects_path",
            "figma": "figma_path",
            "substance": "substance_painter_path",
        }
        field_name = field_map.get(app_key, "")
        if field_name and current_path:
            setattr(workspace, field_name, current_path)
            self.engine.user_settings.save(workspace)

        current_project = self.engine.get_current_project()
        project_name = str(current_project.get("name", "")) if current_project else ""
        result = self.engine.open_connected_app(app_key, project_name)
        if result.get("ok"):
            QMessageBox.information(self, "Apps", result.get("message", "App opened."))
        else:
            QMessageBox.warning(self, "Apps", result.get("message", "App could not be opened."))

    def _browse_for_path(self, target: QLineEdit, caption: str) -> None:
        current_value = target.text().strip()
        start_dir = ""
        if current_value:
            current_path = Path(current_value)
            if current_path.exists():
                start_dir = str(current_path.parent if current_path.is_file() else current_path)
        file_path, _ = QFileDialog.getOpenFileName(self, caption, start_dir)
        if file_path:
            target.setText(file_path)
            target.setFocus()

    def _active_input(self) -> ExpandingMessageInput:
        if self.chat_stack.currentIndex() == 0:
            return self.empty_message_input
        return self.message_input

    def open_project_dialog(self) -> None:
        if self.worker_thread is not None or self.reveal_timer is not None:
            return
        dialog = ProjectCreateDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        project_name, request = dialog.build_request()
        project = self.engine.create_project(project_name, request)
        self.engine.create_new_chat(project_name)
        self.chat_search_input.clear()
        self.studio_output.clear()
        self.message_input.clear()
        self.empty_message_input.clear()
        self._refresh_chat_list()
        self._load_history()
        self._refresh_project_list()
        self._load_project_into_studio(project)
        self.switch_page(1)

    def generate_blueprint(self) -> None:
        request = self.studio_input.toPlainText().strip()
        if not request:
            QMessageBox.information(self, "Project Studio", "Write a project idea first.")
            return
        package = self.engine.generate_project_package(request, self.project_title_label.text())
        self.studio_output.setPlainText(str(package.get("blueprint_text", "")))
        self._update_task_center(
            package.get("tasks", []) if isinstance(package.get("tasks", []), list) else [],
            str(package.get("current_phase", "planning")),
            str(package.get("next_step", "Confirm the next implementation move.")),
            str(package.get("xeno_note", "Xeno prepared a new execution track.")),
        )
        self._refresh_project_list()
        project = self.engine.get_project(str(package.get("project_id", "")))
        self._load_project_into_studio(project)

    def copy_blueprint(self) -> None:
        text = self.studio_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Project Studio", "Generate a blueprint first.")
            return
        QApplication.clipboard().setText(text)

    def send_blueprint_to_chat(self) -> None:
        text = self.studio_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Project Studio", "Generate a blueprint first.")
            return
        self.switch_page(0)
        self.message_input.setPlainTextAndMoveToEnd(
            "Please refine this blueprint into a practical execution plan with milestones, risks, and a first implementation step:\n\n"
            + text
        )
        self.message_input.setFocus()

    def _transition_empty_to_chat(self) -> None:
        if self.chat_stack.currentIndex() != 0:
            self._update_empty_state()
            return

        self.composer_shell.setVisible(True)
        if self.chat_transition_animation is not None:
            self.chat_transition_animation.stop()

        fade_out = QPropertyAnimation(self.empty_state_opacity, b"opacity", self)
        fade_out.setDuration(150)
        fade_out.setStartValue(self.empty_state_opacity.opacity())
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def _switch() -> None:
            self.chat_stack.setCurrentIndex(1)
            self.chat_scroll_opacity.setOpacity(0.0)
            fade_in = QPropertyAnimation(self.chat_scroll_opacity, b"opacity", self)
            fade_in.setDuration(190)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.InOutCubic)

            def _finish() -> None:
                self.chat_transition_animation = None
                self.empty_state_opacity.setOpacity(1.0)
                self.chat_scroll_opacity.setOpacity(1.0)
                self._scroll_chat_to_bottom()

            fade_in.finished.connect(_finish)
            self.chat_transition_animation = QParallelAnimationGroup(self)
            self.chat_transition_animation.addAnimation(fade_in)
            self.chat_transition_animation.start()

        fade_out.finished.connect(_switch)
        self.chat_transition_animation = QParallelAnimationGroup(self)
        self.chat_transition_animation.addAnimation(fade_out)
        self.chat_transition_animation.start()

    def _update_empty_state(self) -> None:
        has_history = bool(self.engine.memory.load_history())
        self.chat_stack.setCurrentIndex(1 if has_history else 0)
        self.empty_state_opacity.setOpacity(1.0)
        self.chat_scroll_opacity.setOpacity(1.0)
        self.composer_shell.setVisible(has_history)
        if has_history and self.pending_attachments:
            self.attachment_row.show()
        else:
            self.attachment_row.hide()

    def _scroll_chat_to_bottom(self) -> None:
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _show_chat_actions_menu(self, position) -> None:
        item = self.chat_list.itemAt(position)
        if item is None:
            return

        self.chat_list.setCurrentItem(item)
        menu = QMenu(self)
        menu.setObjectName("composerMenu")
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        global_pos = self.chat_list.viewport().mapToGlobal(position)
        chosen = menu.exec(global_pos)
        if chosen == rename_action:
            self.rename_selected_chat()
        elif chosen == delete_action:
            self.delete_selected_chat()

    def _show_composer_menu(self, button: QPushButton) -> None:
        menu = QMenu(self)
        menu.setObjectName("composerMenu")

        files_action = menu.addAction("Pridat fotografie a soubory")
        image_action = menu.addAction("Vytvor obrazek")
        research_action = menu.addAction("Hluboky vyzkum")
        web_action = menu.addAction("Vyhledavani na webu")
        more_action = menu.addAction("Vice")

        chosen = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        target = self._active_input()

        if chosen == files_action:
            files, _ = QFileDialog.getOpenFileNames(self, "Pridat soubory")
            if files:
                for file_path in files:
                    if file_path not in self.pending_attachments:
                        self.pending_attachments.append(file_path)
                self._refresh_attachment_rows()
                target.setFocus()
        elif chosen == image_action:
            target.setPlainTextAndMoveToEnd("Vytvor obrazek pro: ")
            target.setFocus()
        elif chosen == research_action:
            target.setPlainTextAndMoveToEnd("Udelej hluboky vyzkum na tema: ")
            target.setFocus()
        elif chosen == web_action:
            target.setPlainTextAndMoveToEnd("/search ")
            target.setFocus()
        elif chosen == more_action:
            QMessageBox.information(self, "Vice", "Dalsi nastroje pridame do tohoto menu pozdeji.")

    def _remove_thinking_placeholder(self) -> None:
        if self.pending_thinking is not None:
            self.pending_thinking.stop()
            self.pending_thinking.deleteLater()
            self.pending_thinking = None

    def _stop_response_reveal(self, keep_bubble: bool = False) -> None:
        if self.reveal_timer is not None:
            self.reveal_timer.stop()
            self.reveal_timer.deleteLater()
            self.reveal_timer = None
        self.reveal_tokens = []
        self.reveal_text = ""
        if keep_bubble:
            self.reveal_bubble = None
        elif self.reveal_bubble is not None:
            self.reveal_bubble.deleteLater()
            self.reveal_bubble = None
    def _set_busy(self, busy: bool, status: str) -> None:
        self.message_input.setDisabled(busy)
        self.empty_message_input.setDisabled(busy)
        self.send_button.setDisabled(busy)
        self.empty_send_button.setDisabled(busy)
        self.new_chat_button.setDisabled(busy)
        self.chat_search_input.setDisabled(busy)
        self.chat_list.setDisabled(busy)
        self.studio_button.setDisabled(busy)
        self.gallery_button.setDisabled(busy)
        self.updates_button.setDisabled(busy)
        self.settings_button.setDisabled(busy)
        self.generate_blueprint_button.setDisabled(busy)
        self.copy_blueprint_button.setDisabled(busy)
        self.send_blueprint_button.setDisabled(busy)
        self.create_project_button.setDisabled(busy)
        self.task_mark_done_button.setDisabled(busy)
        self.task_run_button.setDisabled(busy)
        self.task_send_button.setDisabled(busy)
        self.project_note_input.setDisabled(busy)
        self.project_note_save_button.setDisabled(busy)
        self.project_list.setDisabled(busy)
        self.task_list.setDisabled(busy)
        self.settings_save_button.setDisabled(busy)
        self.settings_reload_button.setDisabled(busy)

    def _start_response_reveal(self, response: str) -> None:
        cleaned = response.removeprefix("Luna: ").strip() or response.strip()
        self._stop_response_reveal()
        self.reveal_bubble = MessageBubble("Luna", "", False)
        self.chat_area.chat_layout.insertWidget(self.chat_area.chat_layout.count() - 1, self.reveal_bubble)
        self.reveal_tokens = cleaned.split()
        self.reveal_text = ""

        if not self.reveal_tokens:
            self.reveal_bubble.set_text(cleaned)
            self.reveal_bubble = None
            self._set_busy(False, "LunaAI")
            self._scroll_chat_to_bottom()
            return

        self.reveal_timer = QTimer(self)
        self.reveal_timer.timeout.connect(self._reveal_next_chunk)
        self.reveal_timer.start(26)

    def _reveal_next_chunk(self) -> None:
        if self.reveal_bubble is None:
            self._stop_response_reveal(True)
            self._set_busy(False, "LunaAI")
            return
        chunk = self.reveal_tokens[:3]
        self.reveal_tokens = self.reveal_tokens[3:]
        if chunk:
            self.reveal_text = (self.reveal_text + " " + " ".join(chunk)).strip()
            self.reveal_bubble.set_text(self.reveal_text)
            self._scroll_chat_to_bottom()
        if not self.reveal_tokens:
            if self.reveal_timer is not None:
                self.reveal_timer.stop()
                self.reveal_timer.deleteLater()
                self.reveal_timer = None
            self.reveal_bubble = None
            self._set_busy(False, "LunaAI")

    def _handle_worker_finished(self, response: str) -> None:
        self._remove_thinking_placeholder()
        if self.worker_thread is not None:
            self.worker_thread = None
        self.worker = None
        self._capture_generated_media(response)
        self._start_response_reveal(response)
        self._refresh_chat_list()
        self._update_empty_state()
        QTimer.singleShot(0, self._scroll_chat_to_bottom)

    def send_message(self) -> None:
        primary_text = self.message_input.toPlainText().strip()
        empty_text = self.empty_message_input.toPlainText().strip()
        text = primary_text or empty_text
        if not text or self.worker_thread is not None or self.reveal_timer is not None:
            return

        final_text = text
        current_project = self.engine.get_current_project()
        if self.pending_attachments:
            attachment_paths = list(self.pending_attachments)
            attachment_names = [Path(file_path).name for file_path in attachment_paths]
            attachment_context = self.engine.read_attachment_context(attachment_paths)
            final_text += "\n\nAttached files: " + ", ".join(attachment_names)
            if attachment_context:
                final_text += "\n\n" + attachment_context
            if current_project is not None:
                self.engine.attach_files_to_project(str(current_project.get("id", "")), attachment_paths)

        self.chat_area.add_message("You", text, True)
        self.message_input.clear()
        self.empty_message_input.clear()
        self._clear_attachments()
        if self.chat_stack.currentIndex() == 0:
            self._transition_empty_to_chat()
        else:
            self._update_empty_state()
        self._scroll_chat_to_bottom()

        self.pending_thinking = TypingBubble(self._scroll_chat_to_bottom)
        self.chat_area.chat_layout.insertWidget(self.chat_area.chat_layout.count() - 1, self.pending_thinking)
        self._set_busy(True, "Luna")
        self.switch_page(0)
        self._scroll_chat_to_bottom()

        self.worker_thread = QThread(self)
        self.worker = ResponseWorker(self.engine, final_text)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._handle_worker_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        QTimer.singleShot(2000, lambda: os._exit(0))
        self._stop_response_reveal()
        if self.worker_thread is not None:
            self._set_busy(False, "Closing")
            self.worker_thread.requestInterruption()
            self.worker_thread.quit()
            if not self.worker_thread.wait(1000):
                self.worker_thread.terminate()
                self.worker_thread.wait(250)
            self.worker_thread = None
            self.worker = None
        QApplication.quit()
        super().closeEvent(event)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background: {BG};
                color: {TEXT};
                font-family: Segoe UI, Inter, Arial;
                font-size: 14px;
            }}

            QWidget {{
                background: transparent;
                color: {TEXT};
                font-family: Segoe UI, Inter, Arial;
                font-size: 14px;
            }}

            QLabel {{
                background: transparent;
                background-color: transparent;
                border: none;
            }}

            #sidebar {{
                background: {PANEL};
                border-right: 1px solid {BORDER};
            }}

            #sidebarRail {{
                background: #151515;
                border-right: 1px solid #252525;
            }}

            #railFeatureButton {{
                background: #1d1d1d;
                color: {TEXT};
                border: 1px solid #2b2b2b;
                border-radius: 16px;
                padding: 10px 8px 12px 8px;
                min-width: 40px;
                max-width: 40px;
                min-height: 78px;
                max-height: 78px;
                font-size: 10px;
                font-weight: 560;
                text-align: center;
            }}

            #railFeatureButton:hover {{
                background: #242424;
                border: 1px solid #363636;
            }}

            #brandIcon {{
                background: transparent;
                border: none;
            }}

            #emptyStateLogo {{
                background: transparent;
                border: none;
                margin-bottom: 10px;
            }}

            #brandName {{
                font-size: 16px;
                font-weight: 650;
                color: {TEXT};
            }}

            #primarySidebarButton, #navButton, #secondaryButton {{
                background: #222222;
                color: {TEXT};
                border: 1px solid #313131;
                border-radius: 13px;
                padding: 11px 13px;
                text-align: left;
                font-weight: 560;
                icon-size: 15px;
            }}

            #primarySidebarButton {{
                font-weight: 640;
                border: 1px solid #3b3b3b;
                background: #252525;
            }}

            #sidebarSearchInput {{
                background: #202020;
                color: {TEXT};
                border: 1px solid #2d2d2d;
                border-radius: 13px;
                padding: 0 14px;
                min-height: 42px;
                font-size: 13px;
            }}

            #sidebarSearchInput:focus {{
                border: 1px solid #5a5a5a;
            }}

            #primarySidebarButton:hover, #navButton:hover, #secondaryButton:hover, #settingsFolderButton:hover, #iconSidebarButton:hover {{
                background: #292929;
                border: 1px solid #404040;
            }}

            #settingsFolderButton {{
                background: {PANEL_2};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 12px 14px;
                text-align: left;
                font-weight: 600;
            }}

            #secondaryButton[compact="true"] {{
                padding: 0 16px;
                min-height: 42px;
                min-width: 94px;
            }}

            #settingsFolderButton[active="true"] {{
                background: #303030;
                border: 1px solid #636363;
                color: {TEXT};
            }}

            #chatList, #projectList, #taskList {{
                background: transparent;
                border: none;
                outline: none;
                padding: 0;
            }}

            #chatList::item, #projectList::item, #taskList::item {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 13px;
                padding: 10px 12px;
                margin: 2px 0;
                color: {TEXT};
            }}

            #chatList::item:hover, #projectList::item:hover, #taskList::item:hover {{
                background: #262626;
                border: 1px solid #323232;
            }}

            #chatList::item:selected, #projectList::item:selected, #taskList::item:selected {{
                background: #2a2a2a;
                border: 1px solid #484848;
                color: {TEXT};
            }}

            #projectList::item, #taskList::item {{
                padding: 12px 13px;
                margin: 3px 0;
            }}

            #sidebarCard, #settingsCard {{
                background: #202020;
                border: 1px solid #2d2d2d;
                border-radius: 18px;
            }}

            #workspaceTitle {{
                font-size: 12px;
                font-weight: 650;
                color: {TEXT};
            }}

            #workspaceStatus, #settingsStatus {{
                font-size: 12px;
                color: {MUTED};
            }}

            #settingsFieldLabel {{
                color: {TEXT};
                font-size: 13px;
                font-weight: 600;
            }}

            #profileImageLabel {{
                background: transparent;
                border: none;
            }}

            #galleryPreview {{
                background: #1d1d1d;
                border: 1px solid #2f2f2f;
                border-radius: 20px;
                color: #d9d9d9;
                font-size: 14px;
                line-height: 1.5;
                padding: 18px;
            }}

            #attachmentCard {{
                background: #212121;
                border: 1px solid #303030;
                border-radius: 16px;
            }}

            #attachmentPreview {{
                background: #2a2a2a;
                border: 1px solid #353535;
                border-radius: 14px;
                color: {TEXT};
                font-size: 11px;
                font-weight: 700;
            }}

            #attachmentName {{
                color: #d0d0d0;
                font-size: 11px;
                line-height: 1.35;
                background: transparent;
            }}

            #settingsFieldHelper {{
                color: {MUTED};
                font-size: 12px;
                line-height: 1.45;
            }}

            #settingsSectionTitle {{
                color: {TEXT};
                font-size: 15px;
                font-weight: 650;
            }}

            #settingsCheck {{
                color: {TEXT};
                spacing: 10px;
                padding: 2px 0 2px 2px;
            }}

            #settingsCheck::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1px solid {BORDER};
                background: {PANEL};
            }}

            #settingsCheck::indicator:checked {{
                background: {ACCENT};
                border: 1px solid {ACCENT};
            }}

            #content {{
                background: {BG};
            }}

            #topBar {{
                background: transparent;
            }}

            #header {{
                background: {BG};
                border-bottom: 1px solid {BORDER};
            }}

            #titleLabel {{
                font-size: 24px;
                font-weight: 650;
                color: {TEXT};
            }}

            #subtitleLabel {{
                font-size: 13px;
                color: #8d8d8d;
            }}

            #headerChip {{
                background: #202020;
                color: #d8d8d8;
                border: 1px solid #2f2f2f;
                border-radius: 11px;
                padding: 7px 11px;
                font-size: 11px;
                font-weight: 560;
            }}

            #chatScroll, #settingsScroll {{
                border: none;
                background: {BG};
            }}

            #emptyState {{
                background: {BG};
            }}

            #emptyStateTitle {{
                color: {TEXT};
                font-size: 28px;
                font-weight: 580;
            }}

            #emptyStateSubtitle {{
                color: #969696;
                font-size: 14px;
            }}

            #composerShell {{
                background: {BG};
            }}

            #composer {{
                background: #262626;
                border: 1px solid #343434;
                border-radius: 26px;
                min-height: 72px;
            }}

            #projectList, #taskList {{
                font-size: 13px;
            }}

            #composerPlusButton {{
                background: transparent;
                color: #d4d4d4;
                border: none;
                font-size: 22px;
                font-weight: 400;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                padding: 0;
            }}

            #composerPlusButton:hover {{
                color: #ffffff;
                background: rgba(255, 255, 255, 0.06);
                border-radius: 14px;
            }}

            #messageInput {{
                background: transparent;
                color: {TEXT};
                border: none;
                padding: 7px 10px;
                font-size: 14px;
                min-height: 32px;
            }}

            #messageInput QTextDocument {{
                background: transparent;
            }}

            #sendButton {{
                background: {ACCENT};
                color: #111111;
                border: none;
                border-radius: 16px;
                padding: 11px 16px;
                font-weight: 650;
                min-width: 102px;
                icon-size: 14px;
            }}

            #sendButton:hover {{
                background: {ACCENT_SOFT};
            }}

            #studioInput, #studioOutput {{
                background: #202020;
                color: {TEXT};
                border: 1px solid #2d2d2d;
                border-radius: 16px;
                padding: 14px 16px;
                font-size: 14px;
            }}

            #settingsInput, #settingsSelect {{
                background: #202020;
                color: {TEXT};
                border: 1px solid #2d2d2d;
                border-radius: 14px;
                padding: 0 16px;
                font-size: 13px;
                min-height: 44px;
            }}

            #studioInput:focus, #settingsInput:focus, #settingsSelect:focus {{
                border: 1px solid #f0f0f0;
            }}

            #senderLabel {{
                background-color: transparent;
                color: #8f8f8f;
                font-size: 11px;
                font-weight: 650;
                border: none;
            }}

            #messageText {{
                background-color: transparent;
                color: {TEXT};
                font-size: 14px;
                line-height: 1.62;
                border: none;
            }}

            #messageText a {{
                color: #e8e8e8;
                text-decoration: underline;
            }}

            #typingText {{
                background-color: transparent;
                color: {MUTED};
                font-size: 14px;
                font-weight: 600;
                border: none;
            }}

            #aiBubble {{
                background: #1f1f1f;
                border: 1px solid #2d2d2d;
                border-radius: 20px;
            }}

            #userBubble {{
                background: #252525;
                border: 1px solid #323232;
                border-radius: 20px;
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 6px;
            }}

            QScrollBar::handle:vertical {{
                background: {PANEL_2};
                border-radius: 5px;
                min-height: 40px;
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QMenu#composerMenu {{
                background: #242424;
                color: {TEXT};
                border: 1px solid #313131;
                border-radius: 14px;
                padding: 8px;
            }}

            QMenu#composerMenu::item {{
                background: transparent;
                padding: 10px 16px;
                border-radius: 10px;
            }}

            QMenu#composerMenu::item:selected {{
                background: #2d2d2d;
            }}
            """
        )


class LunaDesktopApp:
    def __init__(self, engine: Any = None) -> None:
        if engine is None:
            from app.core.engine import LunaEngine
            engine = LunaEngine()
        self.engine = engine
        self.app = None
        self.window: LunaMainWindow | None = None

    def run(self) -> None:
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            app = QApplication(sys.argv)
        self.app = app
        self.window = LunaMainWindow(self.engine)
        self.window.show()
        app.exec()




































