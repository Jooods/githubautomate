import webbrowser
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QScrollArea, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor

LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Rust": "#dea584",
    "Go": "#00ADD8",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C#": "#178600",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Shell": "#89e051",
    "Unknown": "#8b949e"
}

class RepoDetailsWidget(QWidget):
    clone_requested = Signal(dict)
    release_requested = Signal(dict)
    ai_context_requested = Signal(dict)
    download_requested = Signal(dict)
    star_toggled = Signal(dict, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.repo_data: Optional[Dict[str, Any]] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Empty State placeholder
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_icon = QLabel("📦")
        empty_icon.setStyleSheet("font-size: 40px; margin-bottom: 8px;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_label = QLabel("Select a repository to inspect details & manage actions")
        empty_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(empty_label)
        main_layout.addWidget(self.empty_widget)

        # Details Content Container
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        # Title & Badges
        header_box = QVBoxLayout()
        header_box.setSpacing(6)

        title_row = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setFont(QFont("-apple-system", 15, QFont.Bold))
        self.title_label.setStyleSheet("color: #58a6ff;")
        self.title_label.setWordWrap(True)
        title_row.addWidget(self.title_label, stretch=1)

        self.web_btn = QPushButton("Open ↗")
        self.web_btn.setToolTip("Open on GitHub in Web Browser")
        self.web_btn.setFixedWidth(75)
        self.web_btn.clicked.connect(self._open_in_browser)
        title_row.addWidget(self.web_btn)
        header_box.addLayout(title_row)

        # Badges row
        self.badges_layout = QHBoxLayout()
        self.badges_layout.setSpacing(8)

        self.visibility_badge = QLabel("Public")
        self.visibility_badge.setStyleSheet("""
            background-color: #172b4d; color: #58a6ff;
            border: 1px solid #1f6feb; border-radius: 10px;
            padding: 2px 10px; font-weight: 600; font-size: 11px;
        """)
        self.badges_layout.addWidget(self.visibility_badge)

        self.lang_badge = QLabel("Python")
        self.lang_badge.setStyleSheet("""
            background-color: #21262d; color: #c9d1d9;
            border: 1px solid #30363d; border-radius: 10px;
            padding: 2px 10px; font-weight: 600; font-size: 11px;
        """)
        self.badges_layout.addWidget(self.lang_badge)

        self.branch_badge = QLabel("main")
        self.branch_badge.setStyleSheet("""
            background-color: #21262d; color: #8b949e;
            border: 1px solid #30363d; border-radius: 10px;
            padding: 2px 10px; font-size: 11px;
        """)
        self.badges_layout.addWidget(self.branch_badge)

        self.badges_layout.addStretch()
        header_box.addLayout(self.badges_layout)
        content_layout.addLayout(header_box)

        # Description
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #8b949e; font-size: 13px; line-height: 1.4;")
        content_layout.addWidget(self.desc_label)

        # Stats Grid (Stars, Forks, Issues, Size)
        stats_frame = QFrame()
        stats_frame.setObjectName("stats_card")
        stats_frame.setStyleSheet("""
            QFrame#stats_card {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        stats_grid = QGridLayout(stats_frame)
        stats_grid.setContentsMargins(12, 10, 12, 10)
        stats_grid.setSpacing(12)

        self.stars_stat = QLabel("⭐ 0")
        self.stars_stat.setStyleSheet("font-size: 13px; font-weight: 600; color: #e6edf3;")
        self.forks_stat = QLabel("🍴 0")
        self.forks_stat.setStyleSheet("font-size: 13px; font-weight: 600; color: #e6edf3;")
        self.issues_stat = QLabel("🐛 0 Issues")
        self.issues_stat.setStyleSheet("font-size: 13px; font-weight: 600; color: #e6edf3;")
        self.size_stat = QLabel("📦 0 KB")
        self.size_stat.setStyleSheet("font-size: 13px; font-weight: 600; color: #e6edf3;")

        stats_grid.addWidget(self.stars_stat, 0, 0)
        stats_grid.addWidget(self.forks_stat, 0, 1)
        stats_grid.addWidget(self.issues_stat, 1, 0)
        stats_grid.addWidget(self.size_stat, 1, 1)

        content_layout.addWidget(stats_frame)

        # Clone URLs box
        clone_frame = QFrame()
        clone_frame.setStyleSheet("""
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 8px;
        """)
        clone_layout = QVBoxLayout(clone_frame)
        clone_layout.setContentsMargins(10, 8, 10, 8)
        clone_layout.setSpacing(8)

        clone_title = QLabel("Clone URLs")
        clone_title.setStyleSheet("font-weight: 600; font-size: 12px; color: #8b949e;")
        clone_layout.addWidget(clone_title)

        # HTTPS Row
        https_row = QHBoxLayout()
        https_label = QLabel("HTTPS:")
        https_label.setStyleSheet("color: #8b949e; font-size: 11px; min-width: 45px;")
        self.https_text = QLabel()
        self.https_text.setStyleSheet("color: #e6edf3; font-family: Consolas; font-size: 11px;")
        self.https_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        copy_https_btn = QPushButton("Copy")
        copy_https_btn.setFixedSize(50, 24)
        copy_https_btn.clicked.connect(lambda: self._copy_to_clip(self.https_text.text()))
        https_row.addWidget(https_label)
        https_row.addWidget(self.https_text, stretch=1)
        https_row.addWidget(copy_https_btn)
        clone_layout.addLayout(https_row)

        # SSH Row
        ssh_row = QHBoxLayout()
        ssh_label = QLabel("SSH:")
        ssh_label.setStyleSheet("color: #8b949e; font-size: 11px; min-width: 45px;")
        self.ssh_text = QLabel()
        self.ssh_text.setStyleSheet("color: #e6edf3; font-family: Consolas; font-size: 11px;")
        self.ssh_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        copy_ssh_btn = QPushButton("Copy")
        copy_ssh_btn.setFixedSize(50, 24)
        copy_ssh_btn.clicked.connect(lambda: self._copy_to_clip(self.ssh_text.text()))
        ssh_row.addWidget(ssh_label)
        ssh_row.addWidget(self.ssh_text, stretch=1)
        ssh_row.addWidget(copy_ssh_btn)
        clone_layout.addLayout(ssh_row)

        content_layout.addWidget(clone_frame)

        # Action Buttons Section
        actions_label = QLabel("Quick Actions")
        actions_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #f0f6fc; margin-top: 4px;")
        content_layout.addWidget(actions_label)

        # Action 1: Clone
        self.clone_btn = QPushButton("📥  Clone Repository to Local")
        self.clone_btn.setProperty("class", "primary")
        self.clone_btn.setFixedHeight(34)
        self.clone_btn.clicked.connect(lambda: self.clone_requested.emit(self.repo_data))
        content_layout.addWidget(self.clone_btn)

        # Action 2: Manage Releases & SemVer Tags
        self.releases_btn = QPushButton("🚀  Manage Releases & SemVer Tags")
        self.releases_btn.setProperty("class", "accent")
        self.releases_btn.setFixedHeight(34)
        self.releases_btn.clicked.connect(lambda: self.release_requested.emit(self.repo_data))
        content_layout.addWidget(self.releases_btn)

        # Action 3: AI-powered Project Context Generator
        self.ai_btn = QPushButton("🤖  AI Context Generator (AI_CONTEXT.md)")
        self.ai_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b2361;
                color: #e2c5ff;
                border: 1px solid #8957e5;
                font-weight: 600;
                height: 34px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #55338d;
                color: #ffffff;
            }
        """)
        self.ai_btn.clicked.connect(lambda: self.ai_context_requested.emit(self.repo_data))
        content_layout.addWidget(self.ai_btn)

        # Secondary Actions Row (Download Archive, Star)
        sec_row = QHBoxLayout()
        sec_row.setSpacing(8)

        self.download_btn = QPushButton("⬇️  Download .ZIP")
        self.download_btn.setFixedHeight(30)
        self.download_btn.clicked.connect(lambda: self.download_requested.emit(self.repo_data))
        sec_row.addWidget(self.download_btn)

        self.star_btn = QPushButton("⭐ Star")
        self.star_btn.setFixedHeight(30)
        self.star_btn.clicked.connect(self._toggle_star)
        sec_row.addWidget(self.star_btn)

        content_layout.addLayout(sec_row)

        content_layout.addStretch()
        main_layout.addWidget(self.content_widget)

        self.content_widget.setVisible(False)

    def display_repo(self, repo: Optional[Dict[str, Any]]):
        self.repo_data = repo
        if not repo:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
            return

        self.empty_widget.setVisible(False)
        self.content_widget.setVisible(True)

        full_name = repo.get("full_name", "")
        self.title_label.setText(full_name)
        
        desc = repo.get("description", "")
        self.desc_label.setText(desc if desc else "No description provided.")

        is_private = repo.get("is_private", False)
        if is_private:
            self.visibility_badge.setText("Private")
            self.visibility_badge.setStyleSheet("""
                background-color: #2d1d24; color: #f85149;
                border: 1px solid #da3633; border-radius: 10px;
                padding: 2px 10px; font-weight: 600; font-size: 11px;
            """)
        else:
            self.visibility_badge.setText("Public")
            self.visibility_badge.setStyleSheet("""
                background-color: #172b4d; color: #58a6ff;
                border: 1px solid #1f6feb; border-radius: 10px;
                padding: 2px 10px; font-weight: 600; font-size: 11px;
            """)

        lang = repo.get("language") or "Unknown"
        lang_color = LANGUAGE_COLORS.get(lang, "#8b949e")
        self.lang_badge.setText(f"● {lang}")
        self.lang_badge.setStyleSheet(f"""
            background-color: #21262d; color: {lang_color};
            border: 1px solid #30363d; border-radius: 10px;
            padding: 2px 10px; font-weight: 600; font-size: 11px;
        """)

        branch = repo.get("default_branch") or "main"
        self.branch_badge.setText(f" {branch}")

        stars = repo.get("stars", 0)
        forks = repo.get("forks", 0)
        issues = repo.get("open_issues", 0)
        size_kb = repo.get("size", 0)

        self.stars_stat.setText(f"⭐ {stars:,} Stars")
        self.forks_stat.setText(f"🍴 {forks:,} Forks")
        self.issues_stat.setText(f"🐛 {issues} Open Issues")
        
        if size_kb >= 1024:
            self.size_stat.setText(f"📦 {size_kb / 1024:.1f} MB")
        else:
            self.size_stat.setText(f"📦 {size_kb} KB")

        clone_url = repo.get("clone_url", "")
        ssh_url = repo.get("ssh_url", "")
        self.https_text.setText(clone_url)
        self.ssh_text.setText(ssh_url)

    def _open_in_browser(self):
        if self.repo_data:
            url = self.repo_data.get("html_url")
            if url:
                webbrowser.open(url)

    def _copy_to_clip(self, text: str):
        QApplication.clipboard().setText(text)

    def _toggle_star(self):
        if self.repo_data:
            is_starred = self.star_btn.text().startswith("★")
            self.star_toggled.emit(self.repo_data, not is_starred)
            if not is_starred:
                self.star_btn.setText("★ Starred")
            else:
                self.star_btn.setText("⭐ Star")
