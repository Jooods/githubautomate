import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QComboBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from core.db import get_setting, set_setting

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings & Preferences")
        self.setMinimumSize(520, 380)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Application Settings")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #f0f6fc;")
        layout.addWidget(title)

        # 1. Clone directory frame
        clone_frame = QFrame()
        clone_frame.setStyleSheet("""
            background-color: #161b22; border: 1px solid #30363d;
            border-radius: 8px; padding: 12px;
        """)
        cf_layout = QVBoxLayout(clone_frame)
        cf_layout.setSpacing(8)

        cf_lbl = QLabel("Default Clone Directory:")
        cf_lbl.setStyleSheet("font-weight: 500; color: #c9d1d9;")
        cf_layout.addWidget(cf_lbl)

        cf_row = QHBoxLayout()
        self.clone_path_input = QLineEdit()
        cf_row.addWidget(self.clone_path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_clone_dir)
        cf_row.addWidget(browse_btn)
        cf_layout.addLayout(cf_row)
        layout.addWidget(clone_frame)

        # 2. AI Context Generator Enhancer Frame (Optional)
        ai_frame = QFrame()
        ai_frame.setStyleSheet("""
            background-color: #161b22; border: 1px solid #30363d;
            border-radius: 8px; padding: 12px;
        """)
        ai_layout = QVBoxLayout(ai_frame)
        ai_layout.setSpacing(8)

        ai_lbl = QLabel("AI Enhancer Engine:")
        ai_lbl.setStyleSheet("font-weight: 500; color: #c9d1d9;")
        ai_layout.addWidget(ai_lbl)

        ai_prov_row = QHBoxLayout()
        prov_lbl = QLabel("Mode:")
        prov_lbl.setStyleSheet("min-width: 90px; color: #8b949e;")
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItems([
            "Local Offline Heuristics (Fast, Private, Built-in)",
            "Google Gemini API (Optional LLM Enhancement)",
            "OpenAI API Compatible"
        ])
        ai_prov_row.addWidget(prov_lbl)
        ai_prov_row.addWidget(self.ai_mode_combo)
        ai_layout.addLayout(ai_prov_row)

        ai_key_row = QHBoxLayout()
        key_lbl = QLabel("API Key:")
        key_lbl.setStyleSheet("min-width: 90px; color: #8b949e;")
        self.ai_key_input = QLineEdit()
        self.ai_key_input.setEchoMode(QLineEdit.Password)
        self.ai_key_input.setPlaceholderText("Optional API key (if using external LLM)")
        ai_key_row.addWidget(key_lbl)
        ai_key_row.addWidget(self.ai_key_input)
        ai_layout.addLayout(ai_key_row)

        layout.addWidget(ai_frame)

        # 3. Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _browse_clone_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Clone Directory")
        if folder:
            self.clone_path_input.setText(folder)

    def _load_settings(self):
        default_clone = get_setting("default_clone_path", os.path.join(os.path.expanduser("~"), "Projects"))
        self.clone_path_input.setText(default_clone)

        mode = get_setting("ai_mode", "Local Offline Heuristics (Fast, Private, Built-in)")
        idx = self.ai_mode_combo.findText(mode)
        if idx >= 0:
            self.ai_mode_combo.setCurrentIndex(idx)

        self.ai_key_input.setText(get_setting("ai_api_key", ""))

    def _save_settings(self):
        path = self.clone_path_input.text().strip()
        if path:
            os.makedirs(path, exist_ok=True)
            set_setting("default_clone_path", path)

        set_setting("ai_mode", self.ai_mode_combo.currentText())
        set_setting("ai_api_key", self.ai_key_input.text().strip())

        QMessageBox.information(self, "Saved", "Settings saved successfully.")
        self.accept()
