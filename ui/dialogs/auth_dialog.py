from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, 
    QFrame, QWidget
)
from PySide6.QtCore import Qt, Signal
from core.github_client import GitHubClient
from core.db import get_profiles, save_profile, set_active_profile, delete_profile, update_profile_info

class AuthDialog(QDialog):
    profile_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub Authentication & Profiles")
        self.setMinimumSize(560, 480)
        self._init_ui()
        self._load_profiles()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("GitHub Account Profiles")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #f0f6fc;")
        layout.addWidget(title)

        subtitle = QLabel("Authenticate using a Personal Access Token (Classic or Fine-grained with 'repo' scope).")
        subtitle.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(subtitle)

        # Profiles List
        self.profile_list = QListWidget()
        self.profile_list.setStyleSheet("""
            QListWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 4px;
                border-bottom: 1px solid #21262d;
            }
            QListWidget::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.profile_list)

        # List Actions (Switch Active, Delete)
        list_btn_row = QHBoxLayout()
        self.use_btn = QPushButton("✓ Set as Active Profile")
        self.use_btn.setProperty("class", "primary")
        self.use_btn.clicked.connect(self._set_active)
        list_btn_row.addWidget(self.use_btn)

        self.del_btn = QPushButton("🗑️ Remove Profile")
        self.del_btn.setProperty("class", "danger")
        self.del_btn.clicked.connect(self._delete_profile)
        list_btn_row.addWidget(self.del_btn)

        layout.addLayout(list_btn_row)

        # Add New Profile Box
        add_frame = QFrame()
        add_frame.setStyleSheet("""
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px;
        """)
        add_layout = QVBoxLayout(add_frame)
        add_layout.setSpacing(10)

        add_title = QLabel("Add New GitHub Profile")
        add_title.setStyleSheet("font-weight: 600; color: #f0f6fc; font-size: 13px;")
        add_layout.addWidget(add_title)

        name_row = QHBoxLayout()
        name_lbl = QLabel("Profile Name:")
        name_lbl.setStyleSheet("min-width: 90px; color: #c9d1d9;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Work, Personal, Dev Account")
        name_row.addWidget(name_lbl)
        name_row.addWidget(self.name_input)
        add_layout.addLayout(name_row)

        token_row = QHBoxLayout()
        token_lbl = QLabel("GitHub Token:")
        token_lbl.setStyleSheet("min-width: 90px; color: #c9d1d9;")
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("ghp_... or github_pat_...")
        token_row.addWidget(token_lbl)
        token_row.addWidget(self.token_input)
        add_layout.addLayout(token_row)

        # Test & Save button
        self.add_btn = QPushButton("🔑 Connect & Save Profile")
        self.add_btn.setProperty("class", "accent")
        self.add_btn.clicked.connect(self._verify_and_save)
        add_layout.addWidget(self.add_btn)

        layout.addWidget(add_frame)

        # Close
        close_btn = QPushButton("Done")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _load_profiles(self):
        self.profile_list.clear()
        profiles = get_profiles()
        for p in profiles:
            active_marker = " [ACTIVE]" if p.get("is_active") else ""
            user = p.get("username") or "Pending verification"
            text = f"{p.get('name')}{active_marker} - @{user}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, p)
            self.profile_list.addItem(item)
            if p.get("is_active"):
                self.profile_list.setCurrentItem(item)

    def _set_active(self):
        item = self.profile_list.currentItem()
        if not item:
            return
        p = item.data(Qt.UserRole)
        set_active_profile(p["id"])
        self._load_profiles()
        self.profile_changed.emit(p)
        QMessageBox.information(self, "Success", f"Active profile switched to {p['name']}.")

    def _delete_profile(self):
        item = self.profile_list.currentItem()
        if not item:
            return
        p = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to remove profile '{p['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_profile(p["id"])
            self._load_profiles()
            profiles = get_profiles()
            active = next((x for x in profiles if x.get("is_active")), None)
            if active:
                self.profile_changed.emit(active)

    def _verify_and_save(self):
        name = self.name_input.text().strip()
        token = self.token_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Missing Name", "Please provide a name for this profile.")
            return
        if not token:
            QMessageBox.warning(self, "Missing Token", "Please enter a valid GitHub token.")
            return

        self.add_btn.setEnabled(False)
        self.add_btn.setText("Verifying with GitHub...")
        try:
            client = GitHubClient(token)
            user_info = client.get_authenticated_user()

            pid = save_profile(
                name=name,
                token=token,
                username=user_info.get("login", ""),
                avatar_url=user_info.get("avatar_url", ""),
                bio=user_info.get("bio", "")
            )

            set_active_profile(pid)
            self.name_input.clear()
            self.token_input.clear()
            self._load_profiles()

            active_profile = {"id": pid, "name": name, "token": token, "username": user_info.get("login")}
            self.profile_changed.emit(active_profile)

            QMessageBox.information(
                self, "Connected!", 
                f"Successfully authenticated as @{user_info.get('login')}!\nRate limit remaining: {user_info.get('rate_limit_remaining')}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to authenticate with GitHub:\n{str(e)}")
        finally:
            self.add_btn.setEnabled(True)
            self.add_btn.setText("🔑 Connect & Save Profile")
