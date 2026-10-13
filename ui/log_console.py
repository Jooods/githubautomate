from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QComboBox, QApplication
)
from PySide6.QtGui import QTextCursor, QFont
from PySide6.QtCore import Qt

class LogConsoleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Header toolbar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        title = QLabel("Activity & Git Console")
        title.setStyleSheet("font-weight: 600; font-size: 12px; color: #8b949e;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Logs", "Info Only", "Success Only", "Warnings & Errors"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        self.filter_combo.setFixedWidth(130)
        top_bar.addWidget(self.filter_combo)

        copy_btn = QPushButton("Copy")
        copy_btn.setToolTip("Copy console logs to clipboard")
        copy_btn.clicked.connect(self._copy_logs)
        top_bar.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setToolTip("Clear console output")
        clear_btn.clicked.connect(self._clear_logs)
        top_bar.addWidget(clear_btn)

        layout.addLayout(top_bar)

        # Output text edit
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #c9d1d9;
                padding: 6px;
            }
        """)
        layout.addWidget(self.text_edit)

        self._all_logs = []

    def append_log(self, message: str, level: str = "INFO"):
        now = datetime.now().strftime("%H:%M:%S")
        entry = {
            "time": now,
            "level": level.upper(),
            "message": message
        }
        self._all_logs.append(entry)
        self._render_entry(entry)

    def _render_entry(self, entry: dict):
        level = entry["level"]
        time_str = entry["time"]
        msg = entry["message"]

        # Filter check
        curr_filter = self.filter_combo.currentText()
        if curr_filter == "Info Only" and level != "INFO":
            return
        if curr_filter == "Success Only" and level != "SUCCESS":
            return
        if curr_filter == "Warnings & Errors" and level not in ["WARNING", "ERROR"]:
            return

        # Color mapping
        if level == "SUCCESS":
            badge_html = f'<span style="color: #3fb950; font-weight: bold;">[SUCCESS]</span>'
        elif level == "WARNING":
            badge_html = f'<span style="color: #d29922; font-weight: bold;">[WARN]</span>'
        elif level == "ERROR":
            badge_html = f'<span style="color: #f85149; font-weight: bold;">[ERROR]</span>'
        else:
            badge_html = f'<span style="color: #58a6ff; font-weight: bold;">[INFO]</span>'

        time_html = f'<span style="color: #8b949e;">{time_str}</span>'
        msg_html = f'<span style="color: #e6edf3;">{self._escape_html(msg)}</span>'

        html = f'{time_html} {badge_html} {msg_html}'
        self.text_edit.append(html)
        
        # Scroll to bottom
        self.text_edit.moveCursor(QTextCursor.End)

    def _apply_filter(self):
        self.text_edit.clear()
        for entry in self._all_logs:
            self._render_entry(entry)

    def _copy_logs(self):
        text = self.text_edit.toPlainText()
        QApplication.clipboard().setText(text)

    def _clear_logs(self):
        self._all_logs.clear()
        self.text_edit.clear()

    @staticmethod
    def _escape_html(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
