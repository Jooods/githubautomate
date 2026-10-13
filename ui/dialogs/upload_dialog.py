import os
import webbrowser
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QRadioButton, QCheckBox, 
    QProgressBar, QMessageBox, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from core.github_client import GitHubClient
from core.git_manager import GitManager
from core.workers import UploadProjectWorker
from core.db import add_or_update_local_project

class UploadDialog(QDialog):
    project_uploaded = Signal(dict) # repo_data
    generate_ai_requested = Signal(str) # project_path

    def __init__(self, client: GitHubClient, token: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.token = token
        self.worker: Optional[UploadProjectWorker] = None
        self.uploaded_repo = None
        self.selected_path = ""

        self.setWindowTitle("Upload Local Project to GitHub")
        self.setMinimumSize(560, 480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Upload Existing Project as New Repository")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #f0f6fc;")
        layout.addWidget(title)

        subtitle = QLabel("Select a local directory on your machine. This tool will initialize Git, create the remote repository on GitHub, and push your code.")
        subtitle.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(subtitle)

        # 1. Local Directory Picker
        dir_frame = QFrame()
        dir_frame.setStyleSheet("""
            background-color: #161b22; border: 1px solid #30363d;
            border-radius: 8px; padding: 10px;
        """)
        dir_layout = QVBoxLayout(dir_frame)
        dir_layout.setSpacing(8)

        dir_lbl = QLabel("Project Folder:")
        dir_lbl.setStyleSheet("font-weight: 600; color: #c9d1d9;")
        dir_layout.addWidget(dir_lbl)

        dir_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select folder on your computer...")
        self.path_input.textChanged.connect(self._on_path_changed)
        dir_row.addWidget(self.path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_directory)
        dir_row.addWidget(browse_btn)
        dir_layout.addLayout(dir_row)

        self.scan_info_lbl = QLabel("No folder selected.")
        self.scan_info_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        dir_layout.addWidget(self.scan_info_lbl)

        layout.addWidget(dir_frame)

        # 2. Remote Repository Details
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            background-color: #161b22; border: 1px solid #30363d;
            border-radius: 8px; padding: 12px;
        """)
        details_layout = QVBoxLayout(details_frame)
        details_layout.setSpacing(10)

        # Repo Name
        name_row = QHBoxLayout()
        name_lbl = QLabel("Repository Name:")
        name_lbl.setStyleSheet("min-width: 120px; color: #c9d1d9;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. my-awesome-app")
        name_row.addWidget(name_lbl)
        name_row.addWidget(self.name_input)
        details_layout.addLayout(name_row)

        # Description
        desc_row = QHBoxLayout()
        desc_lbl = QLabel("Description:")
        desc_lbl.setStyleSheet("min-width: 120px; color: #c9d1d9;")
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Short project description (optional)")
        desc_row.addWidget(desc_lbl)
        desc_row.addWidget(self.desc_input)
        details_layout.addLayout(desc_row)

        # Visibility
        vis_row = QHBoxLayout()
        vis_lbl = QLabel("Visibility:")
        vis_lbl.setStyleSheet("min-width: 120px; color: #c9d1d9;")
        self.priv_radio = QRadioButton("🔒 Private (Recommended)")
        self.pub_radio = QRadioButton("🌐 Public")
        self.priv_radio.setChecked(True)
        vis_row.addWidget(vis_lbl)
        vis_row.addWidget(self.priv_radio)
        vis_row.addWidget(self.pub_radio)
        vis_row.addStretch()
        details_layout.addLayout(vis_row)

        # Branch
        branch_row = QHBoxLayout()
        branch_lbl = QLabel("Initial Branch:")
        branch_lbl.setStyleSheet("min-width: 120px; color: #c9d1d9;")
        self.branch_input = QLineEdit("main")
        branch_row.addWidget(branch_lbl)
        branch_row.addWidget(self.branch_input)
        details_layout.addLayout(branch_row)

        # Commit Message
        commit_row = QHBoxLayout()
        commit_lbl = QLabel("Initial Commit:")
        commit_lbl.setStyleSheet("min-width: 120px; color: #c9d1d9;")
        self.commit_input = QLineEdit("Initial commit via GitHub Repository Manager")
        commit_row.addWidget(commit_lbl)
        commit_row.addWidget(self.commit_input)
        details_layout.addLayout(commit_row)

        layout.addWidget(details_frame)

        # Progress bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Success Action frame
        self.success_frame = QFrame()
        success_layout = QHBoxLayout(self.success_frame)
        success_layout.setContentsMargins(0, 0, 0, 0)
        self.view_online_btn = QPushButton("🌐 View on GitHub")
        self.view_online_btn.clicked.connect(self._open_online)
        success_layout.addWidget(self.view_online_btn)

        self.ai_btn = QPushButton("🤖 Generate AI Context for Project")
        self.ai_btn.setProperty("class", "accent")
        self.ai_btn.clicked.connect(self._on_ai_requested)
        success_layout.addWidget(self.ai_btn)

        self.success_frame.setVisible(False)
        layout.addWidget(self.success_frame)

        # Buttons
        self.btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.btn_row.addWidget(self.cancel_btn)

        self.upload_btn = QPushButton("Upload to GitHub")
        self.upload_btn.setProperty("class", "primary")
        self.upload_btn.clicked.connect(self._start_upload)
        self.btn_row.addWidget(self.upload_btn)

        layout.addLayout(self.btn_row)

    def _browse_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder:
            self.path_input.setText(folder)

    def _on_path_changed(self, path: str):
        self.selected_path = path.strip()
        if not self.selected_path or not os.path.exists(self.selected_path):
            self.scan_info_lbl.setText("Folder not found.")
            return

        folder_name = os.path.basename(os.path.normpath(self.selected_path))
        if not self.name_input.text():
            self.name_input.setText(folder_name)

        is_git = GitManager.is_git_repo(self.selected_path)
        item_count = len(os.listdir(self.selected_path))
        status_text = f"Folder: {item_count} items."
        if is_git:
            status_text += " Existing Git repository detected."
        else:
            status_text += " New Git repository will be initialized."

        self.scan_info_lbl.setText(status_text)

    def _start_upload(self):
        folder = self.path_input.text().strip()
        repo_name = self.name_input.text().strip()

        if not folder or not os.path.exists(folder):
            QMessageBox.warning(self, "Invalid Path", "Please select a valid local project directory.")
            return

        if not repo_name:
            QMessageBox.warning(self, "Missing Name", "Please enter a repository name.")
            return

        desc = self.desc_input.text().strip()
        is_private = self.priv_radio.isChecked()
        branch = self.branch_input.text().strip() or "main"
        commit_msg = self.commit_input.text().strip() or "Initial commit"

        self.upload_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        self.status_label.setText("Starting upload...")

        self.worker = UploadProjectWorker(
            local_path=folder,
            repo_name=repo_name,
            description=desc,
            is_private=is_private,
            client=self.client,
            token=self.token,
            commit_message=commit_msg,
            branch=branch,
            parent=self
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.succeeded.connect(self._on_success)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def _on_success(self, repo_data: dict):
        self.uploaded_repo = repo_data
        self.progress_bar.setValue(100)
        self.status_label.setText(f"✓ Repository uploaded to GitHub: {repo_data.get('html_url')}")
        self.status_label.setStyleSheet("color: #3fb950; font-weight: 500;")

        # Track in local projects
        add_or_update_local_project(
            name=repo_data.get("name"),
            path=self.selected_path,
            remote_url=repo_data.get("clone_url"),
            repo_full_name=repo_data.get("full_name"),
            current_branch=repo_data.get("default_branch", "main")
        )

        self.upload_btn.setVisible(False)
        self.cancel_btn.setText("Close")
        self.cancel_btn.setEnabled(True)
        self.success_frame.setVisible(True)

        self.project_uploaded.emit(repo_data)

    def _on_failed(self, err_msg: str):
        self.upload_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Upload failed.")
        self.status_label.setStyleSheet("color: #f85149;")
        QMessageBox.critical(self, "Upload Error", f"Failed to upload project:\n{err_msg}")

    def _open_online(self):
        if self.uploaded_repo:
            webbrowser.open(self.uploaded_repo.get("html_url"))

    def _on_ai_requested(self):
        if self.selected_path:
            self.generate_ai_requested.emit(self.selected_path)
            self.accept()
