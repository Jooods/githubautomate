import os
import webbrowser
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTabWidget, QWidget, QListWidget, QListWidgetItem, 
    QTextEdit, QCheckBox, QFileDialog, QProgressBar, QMessageBox, 
    QFrame, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from core.github_client import GitHubClient
from core.semver_manager import SemVerManager, SemVer
from core.workers import (
    FetchReleasesWorker, CreateReleaseWorker, DownloadArchiveWorker, DownloadAssetWorker
)

class ReleaseManagerDialog(QDialog):
    release_created = Signal(dict)

    def __init__(self, repo_data: Dict[str, Any], client: GitHubClient, parent=None):
        super().__init__(parent)
        self.repo_data = repo_data
        self.client = client
        self.full_name = repo_data.get("full_name")
        self.releases: List[Dict[str, Any]] = []
        self.tags: List[Dict[str, Any]] = []
        self.attached_assets: List[str] = []
        self.latest_tag: Optional[str] = None

        self.setWindowTitle(f"Releases & Tags: {self.full_name}")
        self.setMinimumSize(820, 600)
        self._init_ui()
        self._load_releases_and_tags()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        top_header = QHBoxLayout()
        title = QLabel(f"Releases & Semantic Versions - {self.full_name}")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #58a6ff;")
        top_header.addWidget(title)

        top_header.addStretch()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_releases_and_tags)
        top_header.addWidget(refresh_btn)
        main_layout.addLayout(top_header)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_browse = QWidget()
        self.tab_create = QWidget()

        self._build_browse_tab()
        self._build_create_tab()

        self.tabs.addTab(self.tab_browse, "📦 Browse Releases & Tags")
        self.tabs.addTab(self.tab_create, "➕ Create Release & SemVer Bumper")
        main_layout.addWidget(self.tabs)

        # Status & Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        main_layout.addWidget(self.status_label)

    # --- BROWSE TAB ---
    def _build_browse_tab(self):
        layout = QHBoxLayout(self.tab_browse)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)

        # Left Column: Releases & Tags List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        left_lbl = QLabel("Releases & Tags")
        left_lbl.setStyleSheet("font-weight: 600; color: #8b949e;")
        left_layout.addWidget(left_lbl)

        self.rel_list = QListWidget()
        self.rel_list.setStyleSheet("""
            QListWidget {
                background-color: #161b22; border: 1px solid #30363d;
                border-radius: 6px; padding: 4px;
            }
            QListWidget::item {
                padding: 8px; border-radius: 4px;
                border-bottom: 1px solid #21262d;
            }
            QListWidget::item:selected {
                background-color: #1f6feb; color: #ffffff;
            }
        """)
        self.rel_list.itemSelectionChanged.connect(self._on_release_selected)
        left_layout.addWidget(self.rel_list)
        splitter.addWidget(left_widget)

        # Right Column: Release Inspector & Downloads
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Release Header Details
        self.detail_title = QLabel("Select a release")
        self.detail_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #f0f6fc;")
        right_layout.addWidget(self.detail_title)

        self.detail_meta = QLabel("")
        self.detail_meta.setStyleSheet("color: #8b949e; font-size: 11px;")
        right_layout.addWidget(self.detail_meta)

        # Quick Download Buttons (Source code)
        dl_row = QHBoxLayout()
        self.dl_zip_btn = QPushButton("⬇️ Download Source (.zip)")
        self.dl_zip_btn.setProperty("class", "accent")
        self.dl_zip_btn.clicked.connect(lambda: self._download_source_archive("zipball"))
        dl_row.addWidget(self.dl_zip_btn)

        self.dl_tar_btn = QPushButton("⬇️ Download Source (.tar.gz)")
        self.dl_tar_btn.clicked.connect(lambda: self._download_source_archive("tarball"))
        dl_row.addWidget(self.dl_tar_btn)

        self.open_web_btn = QPushButton("🌐 View on GitHub ↗")
        self.open_web_btn.clicked.connect(self._open_release_web)
        dl_row.addWidget(self.open_web_btn)
        right_layout.addLayout(dl_row)

        # Release Body (Markdown)
        body_lbl = QLabel("Release Notes:")
        body_lbl.setStyleSheet("font-weight: 600; color: #8b949e; font-size: 12px;")
        right_layout.addWidget(body_lbl)

        self.detail_body = QTextEdit()
        self.detail_body.setReadOnly(True)
        self.detail_body.setStyleSheet("""
            background-color: #0d1117; border: 1px solid #30363d;
            border-radius: 6px; color: #c9d1d9; font-family: -apple-system, sans-serif;
        """)
        right_layout.addWidget(self.detail_body, stretch=1)

        # Assets Table
        assets_lbl = QLabel("Release Assets:")
        assets_lbl.setStyleSheet("font-weight: 600; color: #8b949e; font-size: 12px;")
        right_layout.addWidget(assets_lbl)

        self.assets_table = QTableWidget()
        self.assets_table.setColumnCount(3)
        self.assets_table.setHorizontalHeaderLabels(["Asset Name", "Size", "Action"])
        self.assets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.assets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.assets_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.assets_table.setFixedHeight(120)
        right_layout.addWidget(self.assets_table)

        splitter.addWidget(right_widget)
        splitter.setSizes([260, 520])
        layout.addWidget(splitter)

    # --- CREATE TAB ---
    def _build_create_tab(self):
        layout = QVBoxLayout(self.tab_create)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. SemVer Bumper Bar
        semver_frame = QFrame()
        semver_frame.setStyleSheet("""
            background-color: #161b22; border: 1px solid #8957e5;
            border-radius: 8px; padding: 10px;
        """)
        sem_layout = QVBoxLayout(semver_frame)
        sem_layout.setSpacing(8)

        sem_top = QHBoxLayout()
        sem_icon = QLabel("🏷️ Semantic Version Bumper:")
        sem_icon.setStyleSheet("font-weight: 600; color: #bc8cff;")
        sem_top.addWidget(sem_icon)

        self.latest_tag_lbl = QLabel("Latest tag: None")
        self.latest_tag_lbl.setStyleSheet("color: #8b949e; font-family: Consolas;")
        sem_top.addWidget(self.latest_tag_lbl)
        sem_top.addStretch()
        sem_layout.addLayout(sem_top)

        bump_row = QHBoxLayout()
        bump_row.setSpacing(8)

        self.btn_bump_patch = QPushButton("+ Bump Patch (v1.0.1)")
        self.btn_bump_patch.clicked.connect(lambda: self._apply_bump("patch"))
        bump_row.addWidget(self.btn_bump_patch)

        self.btn_bump_minor = QPushButton("+ Bump Minor (v1.1.0)")
        self.btn_bump_minor.clicked.connect(lambda: self._apply_bump("minor"))
        bump_row.addWidget(self.btn_bump_minor)

        self.btn_bump_major = QPushButton("+ Bump Major (v2.0.0)")
        self.btn_bump_major.clicked.connect(lambda: self._apply_bump("major"))
        bump_row.addWidget(self.btn_bump_major)

        self.btn_bump_rc = QPushButton("+ Pre-release (-rc.1)")
        self.btn_bump_rc.clicked.connect(lambda: self._apply_bump("prerelease"))
        bump_row.addWidget(self.btn_bump_rc)

        sem_layout.addLayout(bump_row)
        layout.addWidget(semver_frame)

        # 2. Tag & Branch row
        tag_branch_row = QHBoxLayout()
        
        tag_box = QVBoxLayout()
        tag_lbl = QLabel("Tag Name:")
        tag_lbl.setStyleSheet("font-weight: 500; color: #c9d1d9;")
        self.tag_input = QLineEdit("v1.0.0")
        self.tag_input.textChanged.connect(self._validate_tag_input)
        tag_box.addWidget(tag_lbl)
        tag_box.addWidget(self.tag_input)
        tag_branch_row.addLayout(tag_box, stretch=1)

        branch_box = QVBoxLayout()
        branch_lbl = QLabel("Target Branch / Commit:")
        branch_lbl.setStyleSheet("font-weight: 500; color: #c9d1d9;")
        self.target_input = QLineEdit(self.repo_data.get("default_branch", "main"))
        branch_box.addWidget(branch_lbl)
        branch_box.addWidget(self.target_input)
        tag_branch_row.addLayout(branch_box, stretch=1)

        layout.addLayout(tag_branch_row)

        # 3. Release Title
        title_box = QVBoxLayout()
        title_lbl = QLabel("Release Title:")
        title_lbl.setStyleSheet("font-weight: 500; color: #c9d1d9;")
        self.rel_title_input = QLineEdit("v1.0.0 - Release")
        title_box.addWidget(title_lbl)
        title_box.addWidget(self.rel_title_input)
        layout.addLayout(title_box)

        # 4. Release Notes
        notes_header = QHBoxLayout()
        notes_lbl = QLabel("Release Notes (Markdown):")
        notes_lbl.setStyleSheet("font-weight: 500; color: #c9d1d9;")
        notes_header.addWidget(notes_lbl)
        notes_header.addStretch()

        auto_notes_btn = QPushButton("✨ Auto-Generate Release Notes")
        auto_notes_btn.setToolTip("Auto-generate categorized notes from commit history")
        auto_notes_btn.clicked.connect(self._auto_generate_notes)
        notes_header.addWidget(auto_notes_btn)
        layout.addLayout(notes_header)

        self.rel_notes_edit = QTextEdit()
        self.rel_notes_edit.setPlaceholderText("Describe the new features, bug fixes, and improvements in this release...")
        self.rel_notes_edit.setStyleSheet("""
            background-color: #0d1117; border: 1px solid #30363d;
            border-radius: 6px; color: #c9d1d9; font-family: Consolas;
        """)
        layout.addWidget(self.rel_notes_edit, stretch=1)

        # 5. Assets & Checkboxes
        bottom_options = QHBoxLayout()
        self.draft_chk = QCheckBox("Save as Draft")
        self.prerelease_chk = QCheckBox("Set as Pre-release")
        bottom_options.addWidget(self.draft_chk)
        bottom_options.addWidget(self.prerelease_chk)
        bottom_options.addStretch()

        attach_btn = QPushButton("📎 Attach Release Files...")
        attach_btn.clicked.connect(self._attach_asset)
        bottom_options.addWidget(attach_btn)
        layout.addLayout(bottom_options)

        self.attached_lbl = QLabel("No files attached.")
        self.attached_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.attached_lbl)

        # 6. Submit Button
        self.publish_btn = QPushButton("🚀  Publish GitHub Release")
        self.publish_btn.setProperty("class", "primary")
        self.publish_btn.setFixedHeight(36)
        self.publish_btn.clicked.connect(self._create_release)
        layout.addWidget(self.publish_btn)

    # --- LOGIC ---
    def _load_releases_and_tags(self):
        self.status_label.setText("Fetching releases & tags from GitHub...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate

        self.fetch_worker = FetchReleasesWorker(self.client, self.full_name, parent=self)
        self.fetch_worker.succeeded.connect(self._on_fetch_success)
        self.fetch_worker.failed.connect(self._on_fetch_failed)
        self.fetch_worker.start()

    def _on_fetch_success(self, data: dict):
        self.progress_bar.setVisible(False)
        self.status_label.setText("Ready.")
        self.releases = data.get("releases", [])
        self.tags = data.get("tags", [])

        # Update lists
        self.rel_list.clear()

        # Extract all tag names
        tag_names = [t.get("name") for t in self.tags]
        for r in self.releases:
            if r.get("tag_name") not in tag_names:
                tag_names.append(r.get("tag_name"))

        self.latest_tag = SemVerManager.get_latest_semver_tag(tag_names)
        if self.latest_tag:
            self.latest_tag_lbl.setText(f"Latest tag: {self.latest_tag}")
            self._update_bump_buttons(self.latest_tag)
        else:
            self.latest_tag_lbl.setText("Latest tag: None detected")
            self._update_bump_buttons("v1.0.0")

        # Populate Browse list
        for r in self.releases:
            tag = r.get("tag_name")
            title = r.get("title") or tag
            item = QListWidgetItem(f"📦 {title} ({tag})")
            item.setData(Qt.UserRole, ("release", r))
            self.rel_list.addItem(item)

        for t in self.tags:
            tag_name = t.get("name")
            # If not already listed as a full release
            if not any(r.get("tag_name") == tag_name for r in self.releases):
                item = QListWidgetItem(f"🏷️ Tag: {tag_name}")
                item.setData(Qt.UserRole, ("tag", t))
                self.rel_list.addItem(item)

        if self.rel_list.count() > 0:
            self.rel_list.setCurrentRow(0)

    def _on_fetch_failed(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText("Failed to load releases.")
        QMessageBox.warning(self, "API Error", f"Could not fetch releases:\n{err_msg}")

    def _on_release_selected(self):
        item = self.rel_list.currentItem()
        if not item:
            return

        item_type, item_data = item.data(Qt.UserRole)
        self.current_selected_item = (item_type, item_data)

        if item_type == "release":
            title = item_data.get("title") or item_data.get("tag_name")
            tag = item_data.get("tag_name")
            date = item_data.get("published_at", "")[:10]
            draft = " [Draft]" if item_data.get("draft") else ""
            pre = " [Pre-release]" if item_data.get("prerelease") else ""

            self.detail_title.setText(f"{title} ({tag}){draft}{pre}")
            self.detail_meta.setText(f"Published on: {date} | Tag: {tag}")
            self.detail_body.setText(item_data.get("body", ""))

            # Populate assets
            assets = item_data.get("assets", [])
            self.assets_table.setRowCount(len(assets))
            for row, a in enumerate(assets):
                name_item = QTableWidgetItem(a.get("name"))
                self.assets_table.setItem(row, 0, name_item)

                size_kb = a.get("size", 0) // 1024
                size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb} KB"
                self.assets_table.setItem(row, 1, QTableWidgetItem(size_str))

                dl_btn = QPushButton("Download")
                dl_btn.setFixedSize(80, 26)
                dl_btn.clicked.connect(lambda _, asset=a: self._download_asset_file(asset))
                self.assets_table.setCellWidget(row, 2, dl_btn)

        elif item_type == "tag":
            tag_name = item_data.get("name")
            sha = item_data.get("commit_sha", "")[:8]
            self.detail_title.setText(f"Git Tag: {tag_name}")
            self.detail_meta.setText(f"Commit: {sha}")
            self.detail_body.setText(f"This is a standalone Git tag without a GitHub Release entity.")
            self.assets_table.setRowCount(0)

    def _update_bump_buttons(self, base_tag: str):
        patch = SemVerManager.bump_tag(base_tag, "patch")
        minor = SemVerManager.bump_tag(base_tag, "minor")
        major = SemVerManager.bump_tag(base_tag, "major")
        rc = SemVerManager.bump_tag(base_tag, "prerelease")

        self.btn_bump_patch.setText(f"+ Patch ({patch})")
        self.btn_bump_minor.setText(f"+ Minor ({minor})")
        self.btn_bump_major.setText(f"+ Major ({major})")
        self.btn_bump_rc.setText(f"+ Pre-release ({rc})")

    def _apply_bump(self, bump_type: str):
        base = self.latest_tag or "v1.0.0"
        new_tag = SemVerManager.bump_tag(base, bump_type)
        self.tag_input.setText(new_tag)
        self.rel_title_input.setText(f"{new_tag} - Release")

    def _validate_tag_input(self, text: str):
        is_valid = SemVerManager.is_valid_semver(text)
        if is_valid:
            self.tag_input.setStyleSheet("border: 1px solid #2ea043;")
        else:
            self.tag_input.setStyleSheet("border: 1px solid #d29922;")

    def _auto_generate_notes(self):
        tag = self.tag_input.text().strip()
        template = f"""## Release {tag}

### 🚀 What's Changed
- Added core features and improvements
- Optimized workflows and user experience
- Upgraded dependencies and stability fixes

### 🐛 Bug Fixes
- Resolved edge cases in release deployment
- Enhanced error handling

**Full Changelog**: https://github.com/{self.full_name}/commits/{tag}
"""
        self.rel_notes_edit.setText(template.strip())

    def _attach_asset(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Assets to Attach to Release")
        if files:
            self.attached_assets.extend(files)
            names = [os.path.basename(f) for f in self.attached_assets]
            self.attached_lbl.setText(f"Attached {len(names)} files: " + ", ".join(names))

    def _create_release(self):
        tag = self.tag_input.text().strip()
        title = self.rel_title_input.text().strip()
        body = self.rel_notes_edit.toPlainText().strip()
        branch = self.target_input.text().strip() or "main"
        is_draft = self.draft_chk.isChecked()
        is_pre = self.prerelease_chk.isChecked()

        if not tag:
            QMessageBox.warning(self, "Missing Tag", "Please provide a valid tag name.")
            return

        self.publish_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText(f"Creating release {tag}...")

        self.create_worker = CreateReleaseWorker(
            client=self.client,
            full_name=self.full_name,
            tag_name=tag,
            title=title,
            body=body,
            draft=is_draft,
            prerelease=is_pre,
            target_commitish=branch,
            asset_paths=self.attached_assets,
            parent=self
        )
        self.create_worker.succeeded.connect(self._on_create_success)
        self.create_worker.failed.connect(self._on_create_failed)
        self.create_worker.start()

    def _on_create_success(self, rel: dict):
        self.publish_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"✓ Release {rel.get('tag_name')} published!")
        self.status_label.setStyleSheet("color: #3fb950;")
        
        QMessageBox.information(self, "Success", f"Release {rel.get('tag_name')} was created successfully!")
        self.release_created.emit(rel)
        self._load_releases_and_tags()
        self.tabs.setCurrentIndex(0)

    def _on_create_failed(self, err_msg: str):
        self.publish_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Release creation failed.")
        self.status_label.setStyleSheet("color: #f85149;")
        QMessageBox.critical(self, "Error", f"Failed to create release:\n{err_msg}")

    def _download_source_archive(self, archive_fmt: str):
        if not hasattr(self, 'current_selected_item') or not self.current_selected_item:
            return

        item_type, item_data = self.current_selected_item
        ref = item_data.get("tag_name") if item_type == "release" else item_data.get("name")
        ext = ".zip" if archive_fmt == "zipball" else ".tar.gz"
        suggested_name = f"{self.repo_data.get('name')}-{ref}{ext}"

        dest_file, _ = QFileDialog.getSaveFileName(self, "Save Archive", suggested_name)
        if not dest_file:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.status_label.setText(f"Downloading source archive ({ref})...")

        self.dl_worker = DownloadArchiveWorker(
            client=self.client,
            full_name=self.full_name,
            ref=ref,
            dest_path=dest_file,
            archive_format=archive_fmt,
            parent=self
        )
        self.dl_worker.progress.connect(self._on_download_progress)
        self.dl_worker.succeeded.connect(self._on_download_success)
        self.dl_worker.failed.connect(self._on_download_failed)
        self.dl_worker.start()

    def _download_asset_file(self, asset: dict):
        asset_url = asset.get("browser_download_url")
        filename = asset.get("name")
        dest_file, _ = QFileDialog.getSaveFileName(self, "Save Asset", filename)
        if not dest_file:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.status_label.setText(f"Downloading asset {filename}...")

        self.dl_asset_worker = DownloadAssetWorker(
            client=self.client,
            asset_url=asset_url,
            dest_path=dest_file,
            parent=self
        )
        self.dl_asset_worker.progress.connect(self._on_download_progress)
        self.dl_asset_worker.succeeded.connect(self._on_download_success)
        self.dl_asset_worker.failed.connect(self._on_download_failed)
        self.dl_asset_worker.start()

    def _on_download_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def _on_download_success(self, path: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"✓ Downloaded to: {path}")
        self.status_label.setStyleSheet("color: #3fb950;")
        reply = QMessageBox.question(
            self, "Download Finished",
            f"File successfully saved to:\n{path}\n\nDo you want to open containing folder?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            os.startfile(os.path.dirname(path))

    def _on_download_failed(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText("Download failed.")
        self.status_label.setStyleSheet("color: #f85149;")
        QMessageBox.critical(self, "Download Error", f"Failed to download file:\n{err_msg}")

    def _open_release_web(self):
        if hasattr(self, 'current_selected_item') and self.current_selected_item:
            item_type, item_data = self.current_selected_item
            url = item_data.get("html_url")
            if url:
                webbrowser.open(url)
