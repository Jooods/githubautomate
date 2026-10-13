import os
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTabWidget, QWidget, QTextEdit, QFileDialog, 
    QProgressBar, QMessageBox, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from core.ai_context_generator import AIContextGenerator
from core.workers import GenerateAIContextWorker

class AIContextDialog(QDialog):
    def __init__(self, initial_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.current_path = initial_path or ""
        self.generated_data: Dict[str, Any] = {}
        self.worker: Optional[GenerateAIContextWorker] = None

        self.setWindowTitle("AI-Powered Project Context Generator")
        self.setMinimumSize(880, 680)
        self._init_ui()

        if self.current_path:
            self.path_input.setText(self.current_path)
            self._start_generation()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Title & Subtitle
        header_box = QVBoxLayout()
        title = QLabel("🤖 AI Project Context Generator")
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #bc8cff;")
        header_box.addWidget(title)

        subtitle = QLabel("Deeply analyzes project codebase, architecture, and dependencies to auto-generate AI_CONTEXT.md, README.md, and CHANGELOG.md for IDE AI assistants.")
        subtitle.setStyleSheet("color: #8b949e; font-size: 12px;")
        header_box.addWidget(subtitle)
        main_layout.addLayout(header_box)

        # Path & Custom Description Input Frame
        top_frame = QFrame()
        top_frame.setStyleSheet("""
            background-color: #161b22; border: 1px solid #30363d;
            border-radius: 8px; padding: 10px;
        """)
        top_layout = QVBoxLayout(top_frame)
        top_layout.setSpacing(8)

        path_row = QHBoxLayout()
        path_lbl = QLabel("Target Project:")
        path_lbl.setStyleSheet("font-weight: 600; min-width: 100px; color: #c9d1d9;")
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a project or cloned repository directory...")
        path_row.addWidget(path_lbl)
        path_row.addWidget(self.path_input, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        path_row.addWidget(browse_btn)

        self.gen_btn = QPushButton("⚡ Analyze & Generate")
        self.gen_btn.setProperty("class", "accent")
        self.gen_btn.clicked.connect(self._start_generation)
        path_row.addWidget(self.gen_btn)
        top_layout.addLayout(path_row)

        desc_row = QHBoxLayout()
        desc_lbl = QLabel("Focus / Summary:")
        desc_lbl.setStyleSheet("color: #8b949e; min-width: 100px; font-size: 11px;")
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Optional: Add project goal or specific instructions to guide the AI output...")
        desc_row.addWidget(desc_lbl)
        desc_row.addWidget(self.desc_input)
        top_layout.addLayout(desc_row)

        main_layout.addWidget(top_frame)

        # Metrics & Detected Ecosystem Card
        self.info_card = QFrame()
        self.info_card.setStyleSheet("""
            background-color: #11161d; border: 1px dashed #30363d;
            border-radius: 6px; padding: 6px 12px;
        """)
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(8, 4, 8, 4)
        self.info_lbl = QLabel("Ready to analyze project directory.")
        self.info_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        info_layout.addWidget(self.info_lbl)
        main_layout.addWidget(self.info_card)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Tabbed Editor for the 3 generated files
        self.tabs = QTabWidget()
        
        # 1. AI_CONTEXT.md
        self.ai_edit = QTextEdit()
        self.ai_edit.setFont(QFont("Consolas", 10))
        self.tabs.addTab(self.ai_edit, "🤖 AI_CONTEXT.md (For AI Assistants)")

        # 2. README.md
        self.readme_edit = QTextEdit()
        self.readme_edit.setFont(QFont("Consolas", 10))
        self.tabs.addTab(self.readme_edit, "📘 README.md")

        # 3. CHANGELOG.md
        self.changelog_edit = QTextEdit()
        self.changelog_edit.setFont(QFont("Consolas", 10))
        self.tabs.addTab(self.changelog_edit, "📜 CHANGELOG.md")

        main_layout.addWidget(self.tabs, stretch=1)

        # Bottom Bar: Actions
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        copy_btn = QPushButton("📋 Copy Current Tab")
        copy_btn.clicked.connect(self._copy_current_tab)
        bottom_bar.addWidget(copy_btn)

        open_folder_btn = QPushButton("📁 Open Folder in Explorer")
        open_folder_btn.clicked.connect(self._open_project_folder)
        bottom_bar.addWidget(open_folder_btn)

        bottom_bar.addStretch()

        self.save_btn = QPushButton("💾  Save All 3 Files to Project")
        self.save_btn.setProperty("class", "primary")
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self._save_to_project)
        bottom_bar.addWidget(self.save_btn)

        main_layout.addLayout(bottom_bar)

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder:
            self.path_input.setText(folder)
            self._start_generation()

    def _start_generation(self):
        folder = self.path_input.text().strip()
        if not folder or not os.path.exists(folder):
            QMessageBox.warning(self, "Invalid Directory", "Please select an existing project folder.")
            return

        self.gen_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.info_lbl.setText("Scanning file tree, manifests, and git history...")

        custom_desc = self.desc_input.text().strip()

        self.worker = GenerateAIContextWorker(folder, custom_desc, parent=self)
        self.worker.succeeded.connect(self._on_generation_success)
        self.worker.failed.connect(self._on_generation_failed)
        self.worker.start()

    def _on_generation_success(self, result: dict):
        self.gen_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.generated_data = result

        info = result.get("info", {})
        name = info.get("name", "Project")
        primary_lang = info.get("primary_language", "Unknown")
        frameworks = ", ".join(info.get("frameworks", [])) or "Standard"
        files_count = info.get("total_files", 0)

        self.info_lbl.setText(
            f"✓ Analyzed '{name}' — {primary_lang} | Frameworks: {frameworks} | Total files scanned: {files_count}"
        )
        self.info_lbl.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: 500;")

        # Populate editors
        self.ai_edit.setPlainText(result.get("AI_CONTEXT.md", ""))
        self.readme_edit.setPlainText(result.get("README.md", ""))
        self.changelog_edit.setPlainText(result.get("CHANGELOG.md", ""))

    def _on_generation_failed(self, err_msg: str):
        self.gen_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.info_lbl.setText("Generation encountered an error.")
        self.info_lbl.setStyleSheet("color: #f85149; font-size: 11px;")
        QMessageBox.critical(self, "Generation Error", f"Failed to generate context:\n{err_msg}")

    def _copy_current_tab(self):
        curr_idx = self.tabs.currentIndex()
        text = ""
        if curr_idx == 0:
            text = self.ai_edit.toPlainText()
        elif curr_idx == 1:
            text = self.readme_edit.toPlainText()
        elif curr_idx == 2:
            text = self.changelog_edit.toPlainText()

        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Content copied to clipboard!")

    def _open_project_folder(self):
        folder = self.path_input.text().strip()
        if folder and os.path.exists(folder):
            os.startfile(folder)

    def _save_to_project(self):
        folder = self.path_input.text().strip()
        if not folder or not os.path.exists(folder):
            QMessageBox.warning(self, "Invalid Directory", "Target project directory does not exist.")
            return

        files_to_write = {
            "AI_CONTEXT.md": self.ai_edit.toPlainText(),
            "README.md": self.readme_edit.toPlainText(),
            "CHANGELOG.md": self.changelog_edit.toPlainText()
        }

        written = AIContextGenerator.write_context_files(folder, files_to_write, backup_existing=True)

        msg = f"Successfully saved to:\n{folder}\n\n"
        for k, v in written.items():
            if not k.endswith("_backup"):
                msg += f"• {k}\n"

        backups = [v for k, v in written.items() if k.endswith("_backup")]
        if backups:
            msg += f"\n(Backups of prior files were saved with timestamp)"

        QMessageBox.information(self, "Files Saved", msg)
