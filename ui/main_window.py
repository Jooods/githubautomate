import os
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSplitter, QMessageBox, QFrame, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from core.db import get_active_profile, get_cached_repos, save_cached_repos, get_setting
from core.github_client import GitHubClient
from core.workers import FetchReposWorker, DownloadArchiveWorker
from ui.repo_view import RepoViewWidget
from ui.repo_details import RepoDetailsWidget
from ui.log_console import LogConsoleWidget
from ui.dialogs.auth_dialog import AuthDialog
from ui.dialogs.clone_dialog import CloneDialog
from ui.dialogs.upload_dialog import UploadDialog
from ui.dialogs.release_dialog import ReleaseManagerDialog
from ui.dialogs.ai_context_dialog import AIContextDialog
from ui.dialogs.settings_dialog import SettingsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Repository Manager — Developer Suite")
        self.setMinimumSize(1180, 760)

        self.current_profile: Optional[Dict[str, Any]] = None
        self.github_client: Optional[GitHubClient] = None
        self.fetch_worker: Optional[FetchReposWorker] = None
        self.selected_repo: Optional[Dict[str, Any]] = None

        self._init_ui()
        self._load_active_profile_and_data()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Bar
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(12)

        # Brand
        brand_box = QHBoxLayout()
        brand_box.setSpacing(8)
        logo_lbl = QLabel("🐙")
        logo_lbl.setStyleSheet("font-size: 22px;")
        brand_box.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        app_title = QLabel("GitHub Repository Manager")
        app_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f0f6fc;")
        app_sub = QLabel("Desktop Git & AI Context Toolkit")
        app_sub.setStyleSheet("font-size: 11px; color: #8b949e;")
        title_box.addWidget(app_title)
        title_box.addWidget(app_sub)
        brand_box.addLayout(title_box)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Action Buttons in Header
        self.upload_top_btn = QPushButton("⬆️ Upload Project")
        self.upload_top_btn.setProperty("class", "primary")
        self.upload_top_btn.clicked.connect(self._open_upload_dialog)
        header_layout.addWidget(self.upload_top_btn)

        self.ai_top_btn = QPushButton("🤖 AI Context Generator")
        self.ai_top_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b2361; color: #e2c5ff;
                border: 1px solid #8957e5; font-weight: 600;
            }
            QPushButton:hover { background-color: #55338d; color: #ffffff; }
        """)
        self.ai_top_btn.clicked.connect(lambda: self._open_ai_context_dialog())
        header_layout.addWidget(self.ai_top_btn)

        # Profile Switcher / Indicator
        self.profile_btn = QPushButton("👤 Sign In")
        self.profile_btn.setProperty("class", "accent")
        self.profile_btn.clicked.connect(self._open_auth_dialog)
        header_layout.addWidget(self.profile_btn)

        settings_btn = QPushButton("⚙️")
        settings_btn.setToolTip("Settings")
        settings_btn.setFixedWidth(36)
        settings_btn.clicked.connect(self._open_settings_dialog)
        header_layout.addWidget(settings_btn)

        main_layout.addWidget(header)

        # 2. Main Vertical Splitter: (Workspace / Details) and (Log Console)
        v_splitter = QSplitter(Qt.Vertical)

        # Horizontal Splitter: Repos Table (Left) and Inspector Panel (Right)
        h_splitter = QSplitter(Qt.Horizontal)

        # Repos Table
        self.repo_view = RepoViewWidget()
        self.repo_view.repo_selected.connect(self._on_repo_selected)
        self.repo_view.upload_requested.connect(self._open_upload_dialog)
        self.repo_view.refresh_requested.connect(self._refresh_repositories)
        h_splitter.addWidget(self.repo_view)

        # Inspector Panel
        self.repo_details = RepoDetailsWidget()
        self.repo_details.clone_requested.connect(self._open_clone_dialog)
        self.repo_details.release_requested.connect(self._open_release_dialog)
        self.repo_details.ai_context_requested.connect(self._open_ai_context_for_repo)
        self.repo_details.download_requested.connect(self._quick_download_archive)
        self.repo_details.star_toggled.connect(self._on_star_toggled)
        self.repo_details.setMinimumWidth(320)
        h_splitter.addWidget(self.repo_details)

        h_splitter.setSizes([750, 430])
        v_splitter.addWidget(h_splitter)

        # 3. Log Console at bottom
        self.log_console = LogConsoleWidget()
        self.log_console.setFixedHeight(160)
        v_splitter.addWidget(self.log_console)

        v_splitter.setSizes([600, 160])
        main_layout.addWidget(v_splitter)

    # --- Profile & Repos Logic ---
    def _load_active_profile_and_data(self):
        self.current_profile = get_active_profile()

        if not self.current_profile:
            self.profile_btn.setText("🔑 Connect GitHub Account")
            self.profile_btn.setProperty("class", "accent")
            self.log_console.append_log("No active GitHub profile configured. Click 'Connect GitHub Account' to start.", "WARNING")
            self._prompt_for_auth_if_first_time()
            return

        username = self.current_profile.get("username") or self.current_profile.get("name")
        self.profile_btn.setText(f"@{username}")
        self.profile_btn.setStyleSheet("font-weight: 600; color: #58a6ff;")

        # Init client
        token = self.current_profile.get("token")
        self.github_client = GitHubClient(token)

        # Load cached repos first for instant display
        cached = get_cached_repos(self.current_profile["id"])
        if cached:
            self.log_console.append_log(f"Loaded {len(cached)} repositories from local cache.", "INFO")
            self.repo_view.set_repositories(cached)

        # Trigger background fresh sync
        self._refresh_repositories()

    def _prompt_for_auth_if_first_time(self):
        # Auto-open auth dialog on first launch
        self._open_auth_dialog()

    def _refresh_repositories(self):
        if not self.github_client or not self.current_profile:
            self._open_auth_dialog()
            return

        self.repo_view.refresh_btn.setEnabled(False)
        self.repo_view.refresh_btn.setText("🔄 Syncing...")

        self.fetch_worker = FetchReposWorker(
            client=self.github_client,
            profile_id=self.current_profile["id"],
            repo_type="all",
            sort="updated",
            parent=self
        )
        self.fetch_worker.log.connect(self.log_console.append_log)
        self.fetch_worker.succeeded.connect(self._on_repos_fetched)
        self.fetch_worker.failed.connect(self._on_repos_fetch_failed)
        self.fetch_worker.start()

    def _on_repos_fetched(self, repos: List[Dict[str, Any]]):
        self.repo_view.refresh_btn.setEnabled(True)
        self.repo_view.refresh_btn.setText("🔄 Refresh")
        self.repo_view.set_repositories(repos)

    def _on_repos_fetch_failed(self, err_msg: str):
        self.repo_view.refresh_btn.setEnabled(True)
        self.repo_view.refresh_btn.setText("🔄 Refresh")
        self.log_console.append_log(err_msg, "ERROR")

    def _on_repo_selected(self, repo: Dict[str, Any]):
        self.selected_repo = repo
        self.repo_details.display_repo(repo)

    # --- Actions & Dialogs ---
    def _open_auth_dialog(self):
        dialog = AuthDialog(self)
        dialog.profile_changed.connect(self._on_profile_switched)
        dialog.exec()

    def _on_profile_switched(self, new_profile: dict):
        self.current_profile = new_profile
        username = new_profile.get("username") or new_profile.get("name")
        self.profile_btn.setText(f"@{username}")
        self.github_client = GitHubClient(new_profile.get("token"))
        self._refresh_repositories()

    def _open_clone_dialog(self, repo_data: Dict[str, Any]):
        token = self.current_profile.get("token") if self.current_profile else None
        dialog = CloneDialog(repo_data=repo_data, token=token, parent=self)
        dialog.worker.log.connect(self.log_console.append_log) if dialog.worker else None
        dialog.clone_finished.connect(lambda path, r: self.log_console.append_log(f"Cloned {r.get('full_name')} to {path}", "SUCCESS"))
        dialog.generate_ai_requested.connect(self._open_ai_context_dialog)
        dialog.exec()

    def _open_upload_dialog(self):
        if not self.github_client or not self.current_profile:
            QMessageBox.information(self, "Sign In Required", "Please connect your GitHub account before uploading projects.")
            self._open_auth_dialog()
            return

        token = self.current_profile.get("token")
        dialog = UploadDialog(client=self.github_client, token=token, parent=self)
        dialog.project_uploaded.connect(self._on_project_uploaded)
        dialog.generate_ai_requested.connect(self._open_ai_context_dialog)
        dialog.exec()

    def _on_project_uploaded(self, repo_data: dict):
        self.log_console.append_log(f"Uploaded new repository {repo_data.get('full_name')}", "SUCCESS")
        self._refresh_repositories()

    def _open_release_dialog(self, repo_data: Dict[str, Any]):
        if not self.github_client:
            self._open_auth_dialog()
            return

        dialog = ReleaseManagerDialog(repo_data=repo_data, client=self.github_client, parent=self)
        dialog.release_created.connect(lambda rel: self.log_console.append_log(f"Created release {rel.get('tag_name')} for {repo_data.get('full_name')}", "SUCCESS"))
        dialog.exec()

    def _open_ai_context_for_repo(self, repo_data: Dict[str, Any]):
        # Check if cloned locally
        repo_name = repo_data.get("name")
        default_base = get_setting("default_clone_path", os.path.join(os.path.expanduser("~"), "Projects"))
        potential_path = os.path.join(default_base, repo_name)
        initial_path = potential_path if os.path.exists(potential_path) else None

        self._open_ai_context_dialog(initial_path)

    def _open_ai_context_dialog(self, initial_path: Optional[str] = None):
        dialog = AIContextDialog(initial_path=initial_path, parent=self)
        dialog.exec()

    def _open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def _quick_download_archive(self, repo_data: Dict[str, Any]):
        if not self.github_client:
            self._open_auth_dialog()
            return

        full_name = repo_data.get("full_name")
        branch = repo_data.get("default_branch", "main")
        suggested = f"{repo_data.get('name')}-{branch}.zip"

        dest_file, _ = QFileDialog.getSaveFileName(self, "Download Repository Archive", suggested)
        if not dest_file:
            return

        self.log_console.append_log(f"Starting download of {full_name} ({branch})...", "INFO")
        
        dl_worker = DownloadArchiveWorker(
            client=self.github_client,
            full_name=full_name,
            ref=branch,
            dest_path=dest_file,
            archive_format="zipball",
            parent=self
        )
        dl_worker.log.connect(self.log_console.append_log)
        dl_worker.succeeded.connect(lambda path: QMessageBox.information(self, "Download Complete", f"Repository archive saved to:\n{path}"))
        dl_worker.failed.connect(lambda err: QMessageBox.critical(self, "Download Failed", err))
        dl_worker.start()

    def _on_star_toggled(self, repo_data: Dict[str, Any], star: bool):
        if not self.github_client:
            return
        try:
            full_name = repo_data.get("full_name")
            self.github_client.star_repository(full_name, star=star)
            action = "Starred" if star else "Unstarred"
            self.log_console.append_log(f"{action} repository {full_name}", "SUCCESS")
        except Exception as e:
            self.log_console.append_log(f"Star toggle failed: {e}", "ERROR")
