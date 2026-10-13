from typing import List, Dict, Any, Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
    QLabel, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

class RepoViewWidget(QWidget):
    repo_selected = Signal(dict)
    upload_requested = Signal()
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_repos: List[Dict[str, Any]] = []
        self.filtered_repos: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Top Bar: Search, Filters, and Action Buttons
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search repositories by name, description, or language...")
        self.search_input.setFixedHeight(34)
        self.search_input.textChanged.connect(self._apply_filter)
        top_bar.addWidget(self.search_input, stretch=2)

        # Visibility Filter
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All Repos", "Public Only", "Private Only", "Forks Only", "Sources Only"])
        self.type_combo.setFixedHeight(34)
        self.type_combo.currentTextChanged.connect(self._apply_filter)
        top_bar.addWidget(self.type_combo)

        # Sort Filter
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Updated (Newest)", "Stars (High to Low)", "Name (A-Z)", "Forks (High to Low)"])
        self.sort_combo.setFixedHeight(34)
        self.sort_combo.currentTextChanged.connect(self._apply_filter)
        top_bar.addWidget(self.sort_combo)

        # Upload Project Button
        self.upload_btn = QPushButton("⬆️ Upload Project")
        self.upload_btn.setProperty("class", "primary")
        self.upload_btn.setToolTip("Upload an existing local project folder as a new GitHub repository")
        self.upload_btn.setFixedHeight(34)
        self.upload_btn.clicked.connect(self.upload_requested.emit)
        top_bar.addWidget(self.upload_btn)

        # Refresh Button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        top_bar.addWidget(self.refresh_btn)

        layout.addLayout(top_bar)

        # Status & Count Bar
        status_bar = QHBoxLayout()
        self.count_label = QLabel("0 repositories")
        self.count_label.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: 500;")
        status_bar.addWidget(self.count_label)
        status_bar.addStretch()
        layout.addLayout(status_bar)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Repository", "Visibility", "Language", "Stars", "Forks", "Last Updated"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)

        # Column resizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def set_repositories(self, repos: List[Dict[str, Any]]):
        self.all_repos = repos
        self._apply_filter()

    def _apply_filter(self):
        query = self.search_input.text().strip().lower()
        v_filter = self.type_combo.currentText()
        s_filter = self.sort_combo.currentText()

        results = []
        for r in self.all_repos:
            # Query match
            name = r.get("name", "").lower()
            full_name = r.get("full_name", "").lower()
            desc = (r.get("description") or "").lower()
            lang = (r.get("language") or "").lower()

            if query and not (query in name or query in full_name or query in desc or query in lang):
                continue

            # Visibility/Type match
            is_priv = r.get("is_private", False)
            is_fork = r.get("is_fork", False)

            if v_filter == "Public Only" and is_priv:
                continue
            if v_filter == "Private Only" and not is_priv:
                continue
            if v_filter == "Forks Only" and not is_fork:
                continue
            if v_filter == "Sources Only" and is_fork:
                continue

            results.append(r)

        # Sorting
        if s_filter == "Stars (High to Low)":
            results.sort(key=lambda x: x.get("stars", 0), reverse=True)
        elif s_filter == "Name (A-Z)":
            results.sort(key=lambda x: x.get("name", "").lower())
        elif s_filter == "Forks (High to Low)":
            results.sort(key=lambda x: x.get("forks", 0), reverse=True)
        else: # Updated (Newest)
            results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        self.filtered_repos = results
        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(len(self.filtered_repos))
        self.count_label.setText(f"Showing {len(self.filtered_repos)} of {len(self.all_repos)} repositories")

        for row, r in enumerate(self.filtered_repos):
            # 0: Repository Name & desc preview
            name_text = r.get("full_name") or r.get("name")
            desc = r.get("description") or ""
            item_name = QTableWidgetItem(f"{name_text}\n{desc[:55]}..." if desc else name_text)
            item_name.setFont(QFont("-apple-system", 10, QFont.Bold if not desc else QFont.Normal))
            self.table.setItem(row, 0, item_name)

            # 1: Visibility
            is_priv = r.get("is_private", False)
            item_vis = QTableWidgetItem("🔒 Private" if is_priv else "🌐 Public")
            item_vis.setTextAlignment(Qt.AlignCenter)
            item_vis.setForeground(QColor("#f85149" if is_priv else "#58a6ff"))
            self.table.setItem(row, 1, item_vis)

            # 2: Language
            lang = r.get("language") or "—"
            item_lang = QTableWidgetItem(lang)
            item_lang.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_lang)

            # 3: Stars
            stars = r.get("stars", 0)
            item_stars = QTableWidgetItem(f"⭐ {stars:,}")
            item_stars.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_stars)

            # 4: Forks
            forks = r.get("forks", 0)
            item_forks = QTableWidgetItem(f"🍴 {forks:,}")
            item_forks.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_forks)

            # 5: Last Updated
            updated = r.get("updated_at", "")
            display_date = updated[:10] if updated else "—"
            item_updated = QTableWidgetItem(display_date)
            item_updated.setTextAlignment(Qt.AlignCenter)
            item_updated.setForeground(QColor("#8b949e"))
            self.table.setItem(row, 5, item_updated)

        if self.filtered_repos:
            self.table.selectRow(0)

    def _on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row_idx = selected_rows[0].row()
            if 0 <= row_idx < len(self.filtered_repos):
                self.repo_selected.emit(self.filtered_repos[row_idx])
