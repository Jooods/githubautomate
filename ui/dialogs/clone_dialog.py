import os
import subprocess
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QRadioButton, QCheckBox, 
    QProgressBar, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from core.workers import CloneRepoWorker
from core.db import get_setting, add_or_update_local_project

class CloneDialog(QDialog):
    clone_finished = Signal(str, dict) # local_path, repo_data
    generate_ai_requested = Signal(str) # local_path

    def __init__(self, repo_data: Dict[str, Any], token: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.repo_data = repo_data
        self.token = token
        self.cloned_path: Optional[str] = None
        self.worker: Optional[CloneRepoWorker] = None

        self.setWindowTitle(f"Clone Repository: {repo_data.get('name')}")
        self.setMinimumSize(540, 420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        repo_name = self.repo_data.get("name", "repository")
        title = QLabel(f"Clone {self.repo_data.get('full_name')}")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #58a6ff;")
        layout.addWidget(title)

        # Protocol selection
        proto_frame = QFrame()
        proto_layout = QHBoxLayout(proto_frame)
        proto_layout.setContentsMargins(0, 0, 0, 0)
        self.https_radio = QRadioButton("HTTPS")
        self.ssh_radio = QRadioButton("SSH")
        self.https_radio.setChecked(True)
        proto_layout.addWidget(QLabel("Protocol:"))
        proto_layout.addWidget(self.https_radio)
        proto_layout.addWidget(self.ssh_radio)
        proto_layout.addStretch()
        layout.addWidget(proto_frame)

        # Destination Folder
        dest_label = QLabel("Destination Directory:")
        dest_label.setStyleSheet("font-weight: 500; color: #c9d1d9;")
        layout.addWidget(dest_label)

        dest_row = QHBoxLayout()
        default_base = get_setting("default_clone_path", os.path.join(os.path.expanduser("~"), "Projects"))
        default_dest = os.path.join(default_base, repo_name)
        
        self.dest_input = QLineEdit(default_dest)
        dest_row.addWidget(self.dest_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_directory)
        dest_row.addWidget(browse_btn)
        layout.addLayout(dest_row)

        # Options
        opts_layout = QHBoxLayout()
        self.shallow_chk = QCheckBox("Shallow Clone (depth = 1, faster download)")
        opts_layout.addWidget(self.shallow_chk)
        layout.addLayout(opts_layout)

        # Branch override (optional)
        branch_row = QHBoxLayout()
        branch_lbl = QLabel("Branch (optional):")
        branch_lbl.setStyleSheet("color: #8b949e; min-width: 110px;")
        self.branch_input = QLineEdit()
        self.branch_input.setPlaceholderText(f"Default ({self.repo_data.get('default_branch', 'main')})")
        branch_row.addWidget(branch_lbl)
        branch_row.addWidget(self.branch_input)
        layout.addLayout(branch_row)

        # Progress bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Post-clone actions frame
        self.post_clone_frame = QFrame()
        post_layout = QHBoxLayout(self.post_clone_frame)
        post_layout.setContentsMargins(0, 0, 0, 0)
        post_layout.setSpacing(8)

        self.open_folder_btn = QPushButton("📁 Open in Explorer")
        self.open_folder_btn.clicked.connect(self._open_folder)
        post_layout.addWidget(self.open_folder_btn)

        self.open_code_btn = QPushButton("💻 Open in VS Code")
        self.open_code_btn.clicked.connect(self._open_in_code)
        post_layout.addWidget(self.open_code_btn)

        self.ai_btn = QPushButton("🤖 Generate AI Context")
        self.ai_btn.setProperty("class", "accent")
        self.ai_btn.clicked.connect(self._on_ai_requested)
        post_layout.addWidget(self.ai_btn)

        self.post_clone_frame.setVisible(False)
        layout.addWidget(self.post_clone_frame)

        # Action Buttons
        self.btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.btn_row.addWidget(self.cancel_btn)

        self.clone_btn = QPushButton("Clone Repository")
        self.clone_btn.setProperty("class", "primary")
        self.clone_btn.clicked.connect(self._start_clone)
        self.btn_row.addWidget(self.clone_btn)

        layout.addLayout(self.btn_row)

    def _browse_directory(self):
        parent_dir = QFileDialog.getExistingDirectory(self, "Select Parent Directory")
        if parent_dir:
            repo_name = self.repo_data.get("name", "repository")
            self.dest_input.setText(os.path.join(parent_dir, repo_name))

    def _start_clone(self):
        target_dir = self.dest_input.text().strip()
        if not target_dir:
            QMessageBox.warning(self, "Error", "Please select a target destination directory.")
            return

        if os.path.exists(target_dir) and os.listdir(target_dir):
            reply = QMessageBox.question(
                self, "Directory Exists",
                f"The directory '{target_dir}' already exists and is not empty.\nDo you want to proceed anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Choose clone URL
        if self.ssh_radio.isChecked():
            url = self.repo_data.get("ssh_url") or self.repo_data.get("clone_url")
        else:
            url = self.repo_data.get("clone_url")

        depth = 1 if self.shallow_chk.isChecked() else None
        branch = self.branch_input.text().strip() or None

        self.clone_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.status_label.setText("Starting clone operation...")

        # Worker
        self.worker = CloneRepoWorker(
            clone_url=url,
            target_dir=target_dir,
            token=self.token,
            branch=branch,
            depth=depth,
            parent=self
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.succeeded.connect(self._on_clone_success)
        self.worker.failed.connect(self._on_clone_failed)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def _on_clone_success(self, local_path: str):
        self.cloned_path = local_path
        self.progress_bar.setValue(100)
        self.status_label.setText(f"✓ Repository cloned to: {local_path}")
        self.status_label.setStyleSheet("color: #3fb950; font-weight: 500;")

        # Save local project in SQLite
        add_or_update_local_project(
            name=self.repo_data.get("name"),
            path=local_path,
            remote_url=self.repo_data.get("clone_url"),
            repo_full_name=self.repo_data.get("full_name"),
            current_branch=self.repo_data.get("default_branch", "main")
        )

        self.clone_btn.setVisible(False)
        self.cancel_btn.setText("Close")
        self.cancel_btn.setEnabled(True)
        self.post_clone_frame.setVisible(True)

        self.clone_finished.emit(local_path, self.repo_data)

    def _on_clone_failed(self, err_msg: str):
        self.clone_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Clone failed. See console logs for details.")
        self.status_label.setStyleSheet("color: #f85149;")
        QMessageBox.critical(self, "Clone Error", f"Failed to clone repository:\n{err_msg}")

    def _open_folder(self):
        if self.cloned_path and os.path.exists(self.cloned_path):
            os.startfile(self.cloned_path)

    def _open_in_code(self):
        if self.cloned_path and os.path.exists(self.cloned_path):
            try:
                subprocess.Popen(["code", self.cloned_path], shell=True)
            except Exception as e:
                QMessageBox.warning(self, "VS Code Not Found", f"Could not launch 'code': {e}")

    def _on_ai_requested(self):
        if self.cloned_path:
            self.generate_ai_requested.emit(self.cloned_path)
            self.accept()
