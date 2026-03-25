import html
import os
import re
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)



BG = "#0b0b0f"
PANEL = "#101015"
PANEL_2 = "#15151c"
PANEL_3 = "#1b1b24"
TEXT = "#f3f3f5"
MUTED = "#8b8d98"
ACCENT = "#7c5cff"
ACCENT_SOFT = "#a89aff"
BORDER = "#23232b"
USER_BUBBLE = "#1b1b24"
AI_BUBBLE = "#14141b"
HOVER = "#1c1c25"

CONFIG_PATH = Path("d:/LunaAI/config/settings.py")


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

        self.setWindowTitle("LunaAI")
        self.resize(1440, 920)
        self.setMinimumSize(1180, 760)

        root = QWidget()
        self.setCentralWidget(root)

        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_sidebar())
        shell.addWidget(self._build_main_area(), 1)

        self._apply_styles()
        self._load_history()
        self._load_settings_values()
        self._update_empty_state()
        self.switch_page(0)
        QTimer.singleShot(0, self._scroll_chat_to_bottom)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(286)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        brand_icon = QLabel("L")
        brand_icon.setObjectName("brandIcon")
        brand_name = QLabel("LunaAI")
        brand_name.setObjectName("brandName")

        brand_row.addWidget(brand_icon)
        brand_row.addWidget(brand_name)
        brand_row.addStretch()

        self.new_chat_button = QPushButton("+ New chat")
        self.new_chat_button.setObjectName("primarySidebarButton")
        self.new_chat_button.clicked.connect(self.clear_history)

        self.assistant_button = QPushButton("Assistant")
        self.assistant_button.setObjectName("navButton")
        self.assistant_button.clicked.connect(lambda: self.switch_page(0))

        self.studio_button = QPushButton("Project Studio")
        self.studio_button.setObjectName("navButton")
        self.studio_button.clicked.connect(lambda: self.switch_page(1))

        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("navButton")
        self.settings_button.clicked.connect(lambda: self.switch_page(2))

        bottom_card = QFrame()
        bottom_card.setObjectName("sidebarCard")
        bottom_layout = QVBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(14, 12, 14, 12)
        bottom_layout.setSpacing(4)

        workspace_title = QLabel("Luna Workspace")
        workspace_title.setObjectName("workspaceTitle")
        self.workspace_status = QLabel("Ready")
        self.workspace_status.setObjectName("workspaceStatus")

        bottom_layout.addWidget(workspace_title)
        bottom_layout.addWidget(self.workspace_status)

        layout.addLayout(brand_row)
        layout.addWidget(self.new_chat_button)
        layout.addWidget(self.assistant_button)
        layout.addWidget(self.studio_button)
        layout.addStretch()
        layout.addWidget(self.settings_button)
        layout.addWidget(bottom_card)
        return sidebar

    def _build_main_area(self) -> QWidget:
        content = QFrame()
        content.setObjectName("content")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_chat_page())
        self.pages.addWidget(self._build_studio_page())
        self.pages.addWidget(self._build_settings_page())
        layout.addWidget(self.pages, 1)
        return content

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 18, 28, 18)
        layout.setSpacing(12)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        self.header_title = QLabel("Luna")
        self.header_title.setObjectName("titleLabel")
        self.header_subtitle = QLabel("Continue building where you left off.")
        self.header_subtitle.setObjectName("subtitleLabel")

        title_block.addWidget(self.header_title)
        title_block.addWidget(self.header_subtitle)

        self.status_chip = QLabel("Ready")
        self.status_chip.setObjectName("headerChip")

        layout.addLayout(title_block)
        layout.addStretch()
        layout.addWidget(self.status_chip)
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
        self.chat_area = ChatArea()
        self.chat_scroll.setWidget(self.chat_area)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("emptyState")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(0, 0, 0, 90)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_title = QLabel("Let's begin when you are ready.")
        empty_title.setObjectName("emptyStateTitle")
        empty_subtitle = QLabel("Ask Luna to think, build, explain, or shape a project.")
        empty_subtitle.setObjectName("emptyStateSubtitle")
        empty_layout.addWidget(empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        self.chat_stack = QStackedWidget()
        self.chat_stack.addWidget(self.empty_state)
        self.chat_stack.addWidget(self.chat_scroll)

        composer_shell = QFrame()
        composer_shell.setObjectName("composerShell")
        composer_layout = QHBoxLayout(composer_shell)
        composer_layout.setContentsMargins(28, 18, 28, 24)

        self.composer = QFrame()
        self.composer.setObjectName("composer")
        inner_layout = QHBoxLayout(self.composer)
        inner_layout.setContentsMargins(18, 12, 12, 12)
        inner_layout.setSpacing(12)

        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText("Message Luna...")
        self.message_input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)

        inner_layout.addWidget(self.message_input, 1)
        inner_layout.addWidget(self.send_button)
        composer_layout.addWidget(self.composer)

        layout.addWidget(self.chat_stack, 1)
        layout.addWidget(composer_shell)
        return page

    def _build_studio_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        intro = QLabel(
            "Project Studio is Luna's planning space. It uses hidden Xeno support to turn an idea into a blueprint, execution path, and first agent-ready steps."
        )
        intro.setObjectName("subtitleLabel")

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

        layout.addWidget(intro)
        layout.addWidget(self.studio_input, 1)
        layout.addLayout(actions)
        layout.addWidget(self.studio_output, 1)
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

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(28, 24, 28, 32)
        layout.setSpacing(20)

        intro = QLabel("Control how Luna connects, thinks, and integrates with your workspace.")
        intro.setObjectName("subtitleLabel")
        intro.setWordWrap(True)

        connection_card, connection_layout = self._make_settings_card(
            "Connection",
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

        apps_card, apps_layout = self._make_settings_card(
            "Creative Apps",
            "Optional desktop integrations Luna can reference later when we wire real actions into the agent layer.",
        )

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

        apps_layout.addWidget(self._make_settings_field("Unreal Engine 5", self.settings_unreal_path))
        apps_layout.addWidget(self._make_settings_field("Blender", self.settings_blender_path))
        apps_layout.addWidget(self._make_settings_field("FL Studio", self.settings_flstudio_path))
        apps_layout.addWidget(self._make_settings_field("Photoshop", self.settings_photoshop_path))
        apps_layout.addWidget(self._make_settings_field("VS Code", self.settings_vscode_path))
        apps_layout.addWidget(self._make_settings_field("DaVinci Resolve", self.settings_davinci_path))
        apps_layout.addWidget(self._make_settings_field("Unity", self.settings_unity_path))
        apps_layout.addWidget(self._make_settings_field("Premiere Pro", self.settings_premiere_path))
        apps_layout.addWidget(self._make_settings_field("After Effects", self.settings_after_effects_path))
        apps_layout.addWidget(self._make_settings_field("Figma", self.settings_figma_path))
        apps_layout.addWidget(self._make_settings_field("Substance 3D Painter", self.settings_substance_painter_path))

        accounts_card, accounts_layout = self._make_settings_card(
            "Accounts and Connections",
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
            "You can adjust connection, timeout, reasoning style, internet behavior, creative apps, and account links here."
        )
        self.settings_status.setObjectName("settingsStatus")
        self.settings_status.setWordWrap(True)

        layout.addWidget(intro)
        layout.addWidget(connection_card)
        layout.addWidget(apps_card)
        layout.addWidget(accounts_card)
        layout.addLayout(actions)
        layout.addWidget(self.settings_status)
        layout.addStretch()

        scroll.setWidget(content_widget)
        outer_layout.addWidget(scroll)
        return page

    def switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        if index == 0:
            self.header_title.setText("Luna")
            self.header_subtitle.setText("Continue building where you left off.")
        elif index == 1:
            self.header_title.setText("Project Studio")
            self.header_subtitle.setText("Shape an idea into a clear blueprint before sending it back to Luna.")
        else:
            self.header_title.setText("Settings")
            self.header_subtitle.setText("Control the endpoint and token used by Luna.")

    def _load_history(self) -> None:
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
        self.engine.user_settings.save()

        self.settings_status.setText("Settings, workspace integrations, and account links were saved.")
        self.status_chip.setText("Settings updated")
        self.workspace_status.setText("Settings updated")
    def _update_empty_state(self) -> None:
        has_messages = self.chat_area.chat_layout.count() > 1
        self.chat_stack.setCurrentIndex(1 if has_messages else 0)

    def _scroll_chat_to_bottom(self) -> None:
        def scroll() -> None:
            scroll_bar = self.chat_scroll.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

        QApplication.processEvents()
        scroll()
        QTimer.singleShot(0, scroll)
        QTimer.singleShot(80, scroll)

    def _add_thinking_placeholder(self) -> None:
        self.pending_thinking = TypingBubble(self._scroll_chat_to_bottom)
        self.chat_area.chat_layout.insertWidget(self.chat_area.chat_layout.count() - 1, self.pending_thinking)
        self._scroll_chat_to_bottom()

    def _remove_thinking_placeholder(self) -> None:
        if self.pending_thinking is not None:
            self.pending_thinking.stop()
            self.pending_thinking.deleteLater()
            self.pending_thinking = None

    def _start_response_reveal(self, text: str) -> None:
        self._stop_response_reveal()
        self.reveal_text = ""
        self.reveal_tokens = re.findall(r"\n|[^\s\n]+(?:[ \t]+)?", text)
        self.reveal_bubble = MessageBubble("Luna", "", False)
        self.chat_area.chat_layout.insertWidget(self.chat_area.chat_layout.count() - 1, self.reveal_bubble)

        if not self.reveal_tokens:
            self.reveal_bubble.set_text(text)
            self.reveal_bubble = None
            self.workspace_status.setText("Ready")
            self.status_chip.setText("Ready")
            self._set_busy(False, "Ready")
            self._scroll_chat_to_bottom()
            return

        self.reveal_timer = QTimer(self)
        self.reveal_timer.timeout.connect(self._advance_response_reveal)
        self.reveal_timer.start(34)
        self.workspace_status.setText("Responding")
        self.status_chip.setText("Responding")
        self._scroll_chat_to_bottom()

    def _advance_response_reveal(self) -> None:
        if self.reveal_bubble is None:
            self._stop_response_reveal()
            return

        if not self.reveal_tokens:
            self._stop_response_reveal(keep_bubble=True)
            self._set_busy(False, "Ready")
            self._scroll_chat_to_bottom()
            return

        next_chunk = self.reveal_tokens.pop(0)
        self.reveal_text += next_chunk
        self.reveal_bubble.set_text(self.reveal_text)
        self._scroll_chat_to_bottom()

        if next_chunk.endswith((".", "!", "?", ":")):
            assert self.reveal_timer is not None
            self.reveal_timer.setInterval(82)
        elif next_chunk == "\n":
            assert self.reveal_timer is not None
            self.reveal_timer.setInterval(68)
        else:
            assert self.reveal_timer is not None
            self.reveal_timer.setInterval(34)

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

        if self.worker_thread is None:
            self.workspace_status.setText("Ready")
            self.status_chip.setText("Ready")

    def _set_busy(self, busy: bool, status: str) -> None:
        self.workspace_status.setText(status)
        self.status_chip.setText(status)
        self.message_input.setDisabled(busy)
        self.send_button.setDisabled(busy)
        self.new_chat_button.setDisabled(busy)
        self.assistant_button.setDisabled(busy)
        self.studio_button.setDisabled(busy)
        self.settings_button.setDisabled(busy)
        self.generate_blueprint_button.setDisabled(busy)
        self.copy_blueprint_button.setDisabled(busy)
        self.send_blueprint_button.setDisabled(busy)
        self.settings_save_button.setDisabled(busy)
        self.settings_reload_button.setDisabled(busy)

    def send_message(self) -> None:
        text = self.message_input.text().strip()
        if not text or self.worker_thread is not None or self.reveal_timer is not None:
            return

        self.switch_page(0)
        self.chat_area.add_message("You", text, True)
        self.message_input.clear()
        self._add_thinking_placeholder()
        self._update_empty_state()
        self._set_busy(True, "Thinking")

        thread = QThread()
        worker = ResponseWorker(self.engine, text)
        worker.moveToThread(thread)

        self.worker_thread = thread
        self.worker = worker

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_response_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_finished)
        thread.start()

    def _on_response_ready(self, response: str) -> None:
        self._remove_thinking_placeholder()
        cleaned = response.removeprefix("Luna: ") if response.startswith("Luna: ") else response
        if cleaned:
            self._start_response_reveal(cleaned)
        self._update_empty_state()
        self._scroll_chat_to_bottom()

    def _on_worker_finished(self) -> None:
        self.worker_thread = None
        self.worker = None
        if self.reveal_timer is None:
            self._set_busy(False, "Ready")

    def clear_history(self) -> None:
        if self.worker_thread is not None:
            return

        answer = QMessageBox.question(
            self,
            "New Chat",
            "Start a fresh chat and clear the saved conversation history?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.engine.clear_history()
        self._remove_thinking_placeholder()
        self._stop_response_reveal()
        self.chat_area.clear_messages()
        self.studio_output.clear()
        self.message_input.clear()
        self._update_empty_state()
        self._set_busy(False, "Ready")

    def generate_blueprint(self) -> None:
        request = self.studio_input.toPlainText().strip()
        if not request:
            QMessageBox.information(self, "Project Studio", "Write a project idea first.")
            return
        result = self.engine.generate_project_blueprint(request)
        self.studio_output.setPlainText(result)
        self.workspace_status.setText("Blueprint ready")
        self.status_chip.setText("Blueprint ready")

    def copy_blueprint(self) -> None:
        text = self.studio_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Project Studio", "Generate a blueprint first.")
            return
        QApplication.clipboard().setText(text)
        self.workspace_status.setText("Copied")
        self.status_chip.setText("Copied")

    def send_blueprint_to_chat(self) -> None:
        text = self.studio_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Project Studio", "Generate a blueprint first.")
            return
        self.switch_page(0)
        self.message_input.setText(
            "Please refine this blueprint into a practical execution plan with milestones, risks, and a first implementation step:\n\n"
            + text
        )
        self.message_input.setFocus()

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

            #brandIcon {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {PANEL_3}, stop:1 {PANEL_2});
                border: 1px solid {BORDER};
                border-radius: 11px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
                qproperty-alignment: AlignCenter;
                font-weight: 700;
                color: {TEXT};
            }}

            #brandName {{
                font-size: 17px;
                font-weight: 700;
                color: {TEXT};
            }}

            #primarySidebarButton, #navButton, #secondaryButton {{
                background: {PANEL_2};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 12px 14px;
                text-align: left;
                font-weight: 600;
            }}

            #primarySidebarButton:hover, #navButton:hover, #secondaryButton:hover {{
                background: {HOVER};
                border: 1px solid {ACCENT};
            }}

            #sidebarCard, #settingsCard {{
                background: {PANEL_2};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}

            #workspaceTitle {{
                font-size: 13px;
                font-weight: 700;
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

            #settingsFieldHelper {{
                color: {MUTED};
                font-size: 12px;
            }}

            #settingsSectionTitle {{
                color: {TEXT};
                font-size: 16px;
                font-weight: 700;
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

            #header {{
                background: {BG};
                border-bottom: 1px solid {BORDER};
            }}

            #titleLabel {{
                font-size: 28px;
                font-weight: 700;
                color: {TEXT};
            }}

            #subtitleLabel {{
                font-size: 14px;
                color: {MUTED};
            }}

            #headerChip {{
                background: {PANEL_2};
                color: {MUTED};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 8px 12px;
                font-size: 12px;
            }}

            #chatScroll {{
                border: none;
                background: {BG};
            }}

            #emptyState {{
                background: {BG};
            }}

            #emptyStateTitle {{
                color: {TEXT};
                font-size: 34px;
                font-weight: 600;
            }}

            #emptyStateSubtitle {{
                color: {MUTED};
                font-size: 15px;
            }}

            #composerShell {{
                background: {BG};
            }}

            #composer {{
                background: {PANEL};
                border: 1px solid {BORDER};
                border-radius: 22px;
            }}

            #messageInput {{
                background: transparent;
                color: {TEXT};
                border: none;
                padding: 8px 6px;
                font-size: 15px;
                min-height: 28px;
            }}

            #sendButton {{
                background: {ACCENT};
                color: white;
                border: none;
                border-radius: 15px;
                padding: 12px 18px;
                font-weight: 700;
                min-width: 118px;
            }}

            #sendButton:hover {{
                background: {ACCENT_SOFT};
            }}

            #studioInput, #studioOutput {{
                background: {PANEL};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 14px 16px;
                font-size: 15px;
            }}

            #settingsInput, #settingsSelect {{
                background: {PANEL};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 0 16px;
                font-size: 14px;
                min-height: 46px;
            }}

            #studioInput:focus, #settingsInput:focus, #settingsSelect:focus {{
                border: 1px solid {ACCENT};
            }}

            #senderLabel {{
                background-color: transparent;
                color: {MUTED};
                font-size: 12px;
                font-weight: 700;
                border: none;
            }}

            #messageText {{
                background-color: transparent;
                color: {TEXT};
                font-size: 15px;
                line-height: 1.55;
                border: none;
            }}

            #messageText a {{
                color: #8ab4ff;
                text-decoration: none;
            }}

            #typingText {{
                background-color: transparent;
                color: {MUTED};
                font-size: 14px;
                font-weight: 600;
                border: none;
            }}

            #aiBubble {{
                background: {AI_BUBBLE};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}

            #userBubble {{
                background: {USER_BUBBLE};
                border: 1px solid {BORDER};
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
































